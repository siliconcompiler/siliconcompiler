'''
What owns each file a job names, where it came from, and how it reaches a run.

Both ends ask this. The client asks it to decide what goes in the archive and
which dataroots it expects the server to supply; the server asks it to decide,
for every file the manifest names, whether it arrived or can be supplied -- and
never by looking at the path the job names.

🔴 **Every file is uploaded or supplied by identity (D112).** The server used to
look for a file the client left out at the same path on its own disk, expanding
variables from its own environment. A manifest could root a library at `/etc` or
`$HOME/.aws`, leave it out of the archive, and have the server supply it -- on an
unauthenticated server, anyone reading the host's files into a job. It no longer
reads any path a job names.

==============================  ===============  =================================
Dataroot source                 Outcome          How the server finds its copy
==============================  ===============  =================================
a local path, or no dataroot    uploaded         --
a ``$``-rooted path             uploaded         -- the CLIENT expands it
an editable Python package      uploaded         --
an installed Python package     supplied         by package name
git / https / any remote        supplied         by source and ref, allowlist only
marked private                  supplied, never  (object name, dataroot name) to a
                                uploaded         root the operator configured
==============================  ===============  =================================

⚠️ **The design is uploaded whatever its source**, and a PDK's, library's, FPGA
device's or tool's files are uploaded only when local or editable. **Private
wins over both**: a private file is never uploaded, and a private design --
which no server supplies -- is refused.

🔴 **"Local" is the dataroot's registered SOURCE, never where the file is
now.** Every resolved file is on local disk -- a lambdapdk PDK is fetched into
the cache on first use -- so judging by location would upload every PDK in every
job, the exact opposite of the rule, and silently.

🔴 **The table says whether a value MAY go up; the flow says whether it is
NEEDED (D129).** A value goes in the archive, is fetched, or is asked for only
when its key is in :func:`required` -- the union of every running node's
`require`. A local library with views for ten tools used to upload all ten for a
flow that runs three. Both ends read the set from the same manifest; the client
works it out by running each node's setup on a copy (:func:`work_out`)
and carries it there.

⚠️ **A parameter goes up whole.** What the table decides for each value,
`collect` carries out per parameter -- one ``(key, step, index)`` -- so a value
the server could have supplied travels with a local one beside it
(:func:`collection_keys`). A private value beside an uploaded one is refused
rather than sent: keep private files in a fileset of their own.
'''

import os
import re

from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Set, Tuple
from urllib.parse import urlsplit

__all__ = ["DESIGN", "PROJECT", "RESOURCE_KINDS", "LOCAL", "EDITABLE", "INSTALLED",
           "REMOTE", "PRIVATE", "UPLOADED", "SUPPLIED", "FETCH", "ASK", "UNAVAILABLE",
           "is_private", "skipped", "owner", "source", "uploads", "sources",
           "safe_source", "masked", "is_masked", "account", "Entry", "confined",
           "upload_report", "required",
           "needed", "work_out", "with_required", "WorkedOut", "installed_dataroots",
           "private_holders", "collection_keys", "collected_path", "PrivateBeside",
           "value_records", "account_records"]


# Who a file belongs to, when it is neither a resource nor a tool.
DESIGN = "design"
PROJECT = "project"

# The resource kinds whose files follow the local-or-editable rule -- the same
# words the contract's `resource_kinds` uses.
RESOURCE_KINDS = ("pdk", "library", "fpga")

# Where a dataroot's files come from.
LOCAL = "local"            # a path on this machine, `$`-rooted included
EDITABLE = "editable"      # a Python package installed editable
INSTALLED = "installed"    # a Python package installed normally
REMOTE = "remote"          # git, https, or anything fetched -- cached or not
PRIVATE = "private"        # never leaves the machine; supplied by name


def is_private(resolver) -> bool:
    '''Whether a dataroot is marked never to leave the machine: a ``+private``
    scheme, ``file+private://``, ``git+ssh+private://`` and the rest
    (:attr:`~siliconcompiler.package.Resolver.is_private`).

    🔴 **The one place the marker is tested**, so what a remote run makes of it
    is decided here and nowhere else.
    '''
    return bool(getattr(resolver, "is_private", False))


def skipped(key) -> bool:
    '''Parameters that are paths and are not the run's input: exactly what
    `collect` leaves out, by the one rule both use
    (`curation.never_collected`) -- the build and cache directories and the
    credentials file, which are this machine's, the run history, a task's own
    inputs, outputs and reports, and a schema template.'''
    from siliconcompiler.utils.curation import never_collected

    return never_collected(key)


def owner(project, key) -> Tuple[str, Optional[str]]:
    '''``(kind, name)`` for the object a parameter belongs to.

    ``kind`` is one of `RESOURCE_KINDS`, ``"tool"``, `DESIGN` or `PROJECT`.

    ⚠️ The resource classes are tested BEFORE `Design`, because `PDK` and
    `StdCellLibrary` subclass it -- tested the other way round, every PDK would
    be the user's design and always uploaded.
    '''
    if key[0] == "library" and len(key) > 1:
        from siliconcompiler import FPGADevice, PDK, StdCellLibrary

        obj = project.get("library", key[1], field="schema")
        if isinstance(obj, PDK):
            return "pdk", key[1]
        if isinstance(obj, FPGADevice):
            return "fpga", key[1]
        if isinstance(obj, StdCellLibrary):
            return "library", key[1]
        return DESIGN, key[1]

    if key[0] == "tool" and len(key) > 1:
        return "tool", key[1]

    return PROJECT, None


def source(resolvers, dataroot: Optional[str], _seen=None,
           path: Optional[str] = None) -> str:
    '''Where files under ``dataroot`` come from, judged by how it was
    REGISTERED. ``resolvers`` is the owning schema's
    ``_find_files_dataroot_resolvers(True)``.

    🔴 A ``$``-rooted path is LOCAL: the client expands it, with its own
    environment and its `option,env`, and uploads what it finds. The server
    never expands a variable.

    A dataroot that names another dataroot is judged by the one it names; a
    keypath dataroot, by nothing it can be traced to, is local -- the cautious
    answer, since it means sending the file rather than trusting the server
    has it.
    '''
    from siliconcompiler.package import (
        DatarootResolver, PythonPathResolver, RemoteResolver)

    if not dataroot:
        return LOCAL

    resolver = resolvers.get(dataroot)
    if resolver is None:
        return LOCAL

    if is_private(resolver):
        return PRIVATE
    if isinstance(resolver, RemoteResolver):
        return REMOTE
    if isinstance(resolver, PythonPathResolver):
        module = resolver.urlpath
        return EDITABLE if PythonPathResolver.is_python_module_editable(module) \
            else INSTALLED
    if isinstance(resolver, DatarootResolver):
        seen = set(_seen or ())
        if dataroot in seen:
            return LOCAL
        seen.add(dataroot)
        return source(resolvers, resolver.urlpath, seen)
    # A file path, a keypath, or something this client does not know. Sending
    # it is the answer that cannot leave a job short of a file.
    return LOCAL


def uploads(project, key, dataroot: Optional[str], resolvers,
            path: Optional[str] = None) -> bool:
    '''Whether one value of one parameter goes in the archive.'''
    if skipped(key):
        return False

    kind = source(resolvers, dataroot, path=path)
    if kind == PRIVATE:
        return False

    who, _ = owner(project, key)
    if who in (DESIGN, PROJECT):
        return True

    return kind in (LOCAL, EDITABLE)


def safe_source(resolver) -> Optional[str]:
    '''A dataroot's source as it may leave this machine: SiliconCompiler's
    own `Resolver.safe_source` -- no `user:secret@`, every query value masked
    as ``***`` -- the one definition, so what is sent and what is logged agree.
    None where there is no resolver, or its source cannot be read as a URL.'''
    if resolver is None:
        return None
    try:
        return resolver.safe_source
    except (AttributeError, ValueError):
        return None


def masked(url: Optional[str]) -> str:
    '''A source URL the way `safe_source` would send it, for a URL that
    arrived as text rather than from a resolver.'''
    from siliconcompiler.package import Resolver

    return Resolver._masked_uri(url or "", show_userinfo=False)


def is_masked(url: Optional[str]) -> bool:
    '''Whether a source carries a masked query value -- ``?token=***`` or a
    bare ``?***`` -- and so says what it is without saying enough to be
    fetched from.'''
    if not url:
        return False
    query = urlsplit(url).query
    return any(field.partition("=")[2] == "***" or field == "***"
               for field in re.split(r"[&;]", query) if field)


class _Value(NamedTuple):
    key: Tuple[str, ...]
    value: Any                  # the PathNodeValue
    resolvers: Dict[str, Any]
    kind: str                   # the owner's kind, as a source kind
    name: Optional[str]
    dataroot: Optional[str]
    origin: str                 # LOCAL, EDITABLE, INSTALLED, REMOTE or PRIVATE
    step: Optional[str] = None
    index: Optional[str] = None


def _values(project) -> Iterator[_Value]:
    '''Every value of every path parameter a run reads, with its owner and
    where it comes from.'''
    from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue

    for key in sorted(project.allkeys(include_default=False)):
        if skipped(key):
            continue
        param = project.get(*key, field=None)
        if not param.is_path:
            continue

        resolvers = None
        for held, step, index in param.getvalues(return_values=False):
            if not held.has_value:
                continue
            if resolvers is None:
                resolvers = project.get(*key[:-1], field="schema") \
                    ._find_files_dataroot_resolvers(True)
            ones = held.values if isinstance(held, (NodeSetValue, NodeListValue)) \
                else [held]
            for one in ones:
                if one.get() is None:
                    continue
                dataroot = one.get(field="dataroot")
                who, name = owner(project, key)
                yield _Value(tuple(key), one, resolvers,
                             DESIGN if who == PROJECT else who,
                             project.name if who == PROJECT else name,
                             dataroot, source(resolvers, dataroot, path=one.get()),
                             step, index)


class PrivateBeside(ValueError):
    '''A parameter that would go up holds a private value too.'''

    def __init__(self, mixed: List[Tuple[Tuple[str, ...], Optional[str], Optional[str]]]):
        self.mixed = mixed
        named = "; ".join(f"[{','.join(key)}]" + (f" ({step}/{index})" if step else "")
                          for key, step, index in mixed)
        super().__init__(
            f"{named} holds files marked private beside files this run sends. A "
            "parameter's files go up together, so the private ones would too: put "
            "them in a fileset of their own.")


def collection_keys(project, pick: Callable[[_Value], bool],
                    refuse_private: bool = True) \
        -> List[Tuple[Tuple[str, ...], Optional[str], Optional[str]]]:
    '''What `collect` is handed: every ``(key, step, index)`` one of whose
    values ``pick`` takes -- and then all of its values, since `collect` takes
    a parameter whole.

    🔴 **Both ends call this**, the client to collect and the server to know
    what a follow-up archive may carry, so they agree on what "whole" includes.

    A private value is never picked, and one beside a picked value is
    :class:`PrivateBeside` -- raised, unless ``refuse_private`` is off, where
    the parameter is left out.
    '''
    from siliconcompiler.utils.curation import filter_collection_keys

    picked: Dict[Tuple[Tuple[str, ...], Optional[str], Optional[str]], None] = {}
    private = set()
    for one in _values(project):
        where = (one.key, one.step, one.index)
        if one.origin == PRIVATE:
            private.add(where)
        elif pick(one):
            picked[where] = None
    mixed = [where for where in picked if where in private]
    if mixed and refuse_private:
        raise PrivateBeside(mixed)
    return filter_collection_keys([where for where in picked if where not in private])


def collected_path(one: _Value) -> Optional[str]:
    '''Where `collect` puts ``one``, under the collection directory.'''
    from siliconcompiler.schema.parametervalue import PathNodeValue

    return PathNodeValue.generate_hashed_collection_path(one.value.get(), one.dataroot)


def collected_paths(project, paths) -> Dict[str, str]:
    '''Where `collect` puts each of ``paths`` -- files on this machine that a
    path parameter names -- under the collection directory: ``{path: its
    collected path}``, for each a non-private value resolves to. What puts a
    test's helper modules in the test's own collected folder.'''
    wanted = {os.path.realpath(str(path)): str(path) for path in paths}
    found: Dict[str, str] = {}
    for one in _values(project):
        if one.origin == PRIVATE:
            continue
        resolver = one.resolvers.get(one.dataroot) if one.dataroot else None
        try:
            base = resolver.get_path() if resolver is not None else None
            here = one.value.resolve_path(search=[str(base)] if base else None)
        except Exception:                                       # noqa: BLE001
            continue
        path = wanted.get(os.path.realpath(str(here))) if here else None
        if path is not None and path not in found:
            where = collected_path(one)
            if where:
                found[path] = where
    return found


def sources(project, required=None) -> List[Dict[str, Any]]:
    '''The dataroots this client expects the server to supply: the descriptor's
    `sources`. One entry per (kind, name, dataroot) not uploaded -- and, given
    the flow's ``required`` keys, only one holding a value the flow reads.

    🔴 Every URL is its resolver's `safe_source`: no `user:secret@`, and every
    query value masked as ``***`` -- which says what the source is and not
    enough to fetch it from, so the server asks for it rather than fetch it.
    A private dataroot's source is ABSENT -- its path is never sent.

    Each names its dataroot by ``name``, the object that owns it, and
    ``dataroot``, its own name, and no kind: a resource's name is unique across
    kinds, so the server finds the kind from it (surface D282).
    '''
    found: Dict[Tuple[Optional[str], str], Dict[str, Any]] = {}
    for one in _values(project):
        if one.origin not in (INSTALLED, REMOTE, PRIVATE) or not one.dataroot:
            continue
        if not needed(one.key, required):
            continue
        entry = (one.name, one.dataroot)
        if entry in found:
            continue
        resolver = one.resolvers.get(one.dataroot)
        item = {"name": one.name, "dataroot": one.dataroot,
                "private": one.origin == PRIVATE}
        if one.origin != PRIVATE:
            item["source"] = safe_source(resolver)
            ref = getattr(resolver, "reference", None)
            if ref:
                item["ref"] = ref
        found[entry] = item
    return list(found.values())


def _distribution_of(module: Optional[str]) -> Optional[str]:
    '''The installed distribution that provides a top-level module.'''
    from importlib import metadata

    if not module:
        return None
    owners = metadata.packages_distributions().get(module.split(".", 1)[0]) or []
    return owners[0] if owners else None


def installed_dataroots(project, required=None) \
        -> List[Tuple[Tuple[Optional[str], str], str]]:
    '''Each ``(name, dataroot)`` the flow reads from a Python package
    installed normally, with the distribution that provides it -- what a
    server may supply by that distribution's version, where it holds it.'''
    found: Dict[Tuple[Optional[str], str], str] = {}
    for one in _values(project):
        if one.origin != INSTALLED or not one.dataroot or not needed(one.key, required):
            continue
        entry = (one.name, one.dataroot)
        if entry in found:
            continue
        resolver = one.resolvers.get(one.dataroot)
        distribution = _distribution_of(getattr(resolver, "urlpath", None))
        if distribution:
            found[entry] = distribution
    return sorted(found.items())


def private_holders(project, required=None) -> Set[str]:
    '''The distributions whose objects carry a private dataroot the flow
    reads: the job has to land where that distribution is, since the
    server's copy of the dataroot is mapped by that object.'''
    found: Set[str] = set()
    for one in _values(project):
        if one.origin != PRIVATE or not needed(one.key, required):
            continue
        try:
            holder = project.get(*one.key[:-1], field="schema")
        except Exception:                                        # noqa: BLE001
            continue
        distribution = _distribution_of(type(holder).__module__)
        if distribution:
            found.add(distribution)
    return found


# How the server accounts for a (kind, name, dataroot): worst first.
UNAVAILABLE = "unavailable"   # private and not supplied, or a path that escapes
ASK = "ask"                   # the client can send it, and has not
FETCH = "fetch"               # allowlisted, not held: fetched after submit
SUPPLIED = "supplied"         # held, private-mapped, or an installed package
UPLOADED = "uploaded"         # every file of it is in the archive

_WORST = (UNAVAILABLE, ASK, FETCH, SUPPLIED, UPLOADED)


class Entry(NamedTuple):
    '''One (kind, name, dataroot), and how its files reach the run.'''
    kind: str
    name: Optional[str]
    dataroot: Optional[str]
    status: str
    root: Optional[str] = None      # the server's own copy, for SUPPLIED
    source: Optional[str] = None    # what to fetch, for FETCH
    ref: Optional[str] = None
    why: Optional[str] = None       # for UNAVAILABLE
    origin: Optional[str] = None    # LOCAL, EDITABLE, INSTALLED, REMOTE or PRIVATE
    key: Optional[Tuple[str, ...]] = None   # the value that decided the status,
    path: Optional[str] = None              # for a refusal to name

    @property
    def wire(self) -> Dict[str, Any]:
        '''As `upload_sources` spells it: a dataroot, by its owner and its own
        name (surface D282).'''
        return {"kind": "dataroot", "name": self.name, "dataroot": self.dataroot}


def value_records(project, collection_dir, required=None) -> List[Dict[str, Any]]:
    '''Every value the flow reads, as plain data: the manifest's half of
    :func:`account`, which runs where the manifest is read.

    One record per value -- its ``(key, step, index)``, the owner's kind and
    name, the dataroot and where it comes from, the path, and where
    `collect` puts it under the collection directory (:func:`collected_path`,
    computed here because the layout is the reading SiliconCompiler's) --
    with what it was found as in ``collection_dir`` (``collected``, relative),
    and the identity the server would supply it by: a package's module, or a
    remote source and ref.

    🔴 **What the server acts on is this, never the manifest.** It checks
    each ``collected`` path it relies on itself (:func:`account_records`),
    since whatever wrote the manifest decides what this says.
    '''
    records = []
    for one in _values(project):
        if not needed(one.key, required):
            continue
        record = {"key": list(one.key), "step": one.step, "index": one.index,
                  "kind": one.kind, "name": one.name, "dataroot": one.dataroot,
                  "origin": one.origin, "path": one.value.get(),
                  "collected_path": collected_path(one),
                  "collected": None, "source": None, "ref": None, "package": None}
        found = _collected_at(one.value, collection_dir)
        if found is not None:
            record["collected"] = found
        resolver = one.resolvers.get(one.dataroot) if one.dataroot else None
        if one.origin == INSTALLED and resolver is not None:
            record["package"] = resolver.urlpath
        elif one.origin == REMOTE and resolver is not None:
            record["source"] = safe_source(resolver)
            record["ref"] = getattr(resolver, "reference", None)
        records.append(record)
    return records


def account(project, collection_dir, supply, required=None) -> List[Entry]:
    '''Every file the flow reads, as how it reaches the run:
    :func:`value_records`, then :func:`account_records`.'''
    return account_records(value_records(project, collection_dir, required),
                           collection_dir, supply, required)


def account_records(records, collection_dir, supply, required=None) -> List[Entry]:
    '''Every file the flow reads, as how it reaches the run: the server's
    half of :func:`account`, from :func:`value_records`.

    ``supply`` answers for this server: ``package(module)``,
    ``private_root(name, dataroot)``, ``held(source, ref)`` and
    ``allowlisted(source, ref)``. ``required`` is :func:`required`'s set; None
    accounts for every file the manifest names, as before the set existed.

    🔴 **No path the job names is read.** A file is in the archive, or it is
    supplied by identity -- a package by name, a private dataroot by (object,
    dataroot), a remote source by (source, ref) -- and a path under a supplied
    root is confined to it. Anything else is `ASK` (the client can send it) or
    `UNAVAILABLE` (it cannot).

    🔴 **Given the set, a supplied file must be THERE.** A required value
    missing from the server's own copy is `UNAVAILABLE` -- the server should
    have supplied it -- rather than a node failing on it later. Without the set
    that check would refuse a job over a file it never reads.

    🔴 **An uploaded file is the server's own finding.** A record says where
    the read found it in the collection; it counts only where that path, held
    inside ``collection_dir``, is really there.
    '''
    groups: Dict[Tuple[str, Optional[str], Optional[str]], Entry] = {}

    for record in records:
        key = tuple(record["key"])
        if not needed(key, required):
            continue
        entry = _one(record, collection_dir, supply, present=required is not None)
        group = (record["kind"], record["name"], record["dataroot"])
        held = groups.get(group)
        if held is None or _WORST.index(entry.status) < _WORST.index(held.status):
            groups[group] = entry

    return sorted(groups.values(),
                  key=lambda e: (_WORST.index(e.status), e.kind, str(e.name),
                                 str(e.dataroot)))


def _one(record, collection_dir, supply, present: bool = False) -> Entry:
    path = record["path"]
    base = dict(kind=record["kind"], name=record["name"], dataroot=record["dataroot"],
                origin=record["origin"], key=tuple(record["key"]), path=path)

    # Private wins over everything, the archive included: it must never have
    # been sent, and a copy that arrived anyway is not used.
    if record["origin"] == PRIVATE:
        if record["kind"] == DESIGN:
            return Entry(**base, status=UNAVAILABLE,
                         why="a private design cannot be supplied by a server")
        root = supply.private_root(record["name"], record["dataroot"])
        if not root:
            return Entry(**base, status=UNAVAILABLE,
                         why="a private dataroot this server has no copy of")
        return _supplied(base, root, path, present)

    found = record.get("collected")
    if found and collection_dir and confined(collection_dir, found) is not None \
            and os.path.exists(confined(collection_dir, found)):
        return Entry(**base, status=UPLOADED)

    if record["origin"] in (LOCAL, EDITABLE):
        return Entry(**base, status=ASK)

    if record["origin"] == INSTALLED:
        return Entry(**base, status=SUPPLIED) \
            if record.get("package") and supply.package(record["package"]) \
            else Entry(**base, status=ASK)

    # REMOTE: by source and ref, and only from the allowlist.
    remote, ref = record.get("source"), record.get("ref")
    if not _relative_and_inside(path):
        return Entry(**base, status=UNAVAILABLE, why="a path that escapes its dataroot")
    root = supply.held(remote, ref)
    if root:
        return _supplied(base, root, path, present)
    if supply.allowlisted(remote, ref):
        return Entry(**base, status=FETCH, source=remote, ref=ref)
    return Entry(**base, status=ASK)


def _supplied(base, root, path, present: bool) -> Entry:
    '''A file under one of this server's own roots: confined to it, and --
    where the flow reads it -- there.'''
    full = confined(root, path)
    if full is None:
        return Entry(**base, status=UNAVAILABLE, why="a path that escapes its dataroot")
    if present and not os.path.exists(full):
        return Entry(**base, status=UNAVAILABLE,
                     why=f"{path} is not in this server's copy")
    return Entry(**base, status=SUPPLIED, root=root)


def _collected_at(value, collection_dir) -> Optional[str]:
    '''Where ``value`` resolves in ``collection_dir``, relative to it, or
    None where it is not there.'''
    if not collection_dir or not os.path.isdir(collection_dir):
        return None
    try:
        found = value.resolve_path(search=[], collection_dir=str(collection_dir))
    except FileNotFoundError:
        return None
    if not found:
        return None
    base = os.path.abspath(str(collection_dir))
    found = os.path.abspath(str(found))
    if found == base or os.path.commonpath([base, found]) != base:
        return None
    return os.path.relpath(found, base).replace(os.sep, "/")


def _collected(value, collection_dir) -> bool:
    if not collection_dir or not os.path.isdir(collection_dir):
        return False
    try:
        found = value.resolve_path(search=[], collection_dir=str(collection_dir))
    except FileNotFoundError:
        return False
    return bool(found) and str(found).startswith(str(collection_dir))


def _relative_and_inside(path) -> bool:
    '''Lexically: relative, and not climbing out of wherever it is joined.'''
    text = str(path or "")
    if not text or os.path.isabs(text) or text.startswith("$") or "\x00" in text:
        return False
    return not os.path.normpath(text).startswith("..")


def confined(root, path) -> Optional[str]:
    '''``root/path`` if it stays under ``root`` once symlinks are resolved,
    else None.

    🔴 **Canonicalised and checked, never trusted.** A supplied root is this
    server's, and a job naming ``../../etc/passwd`` under it -- or a symlink
    inside it pointing out -- must not reach past it.
    '''
    if not _relative_and_inside(path):
        return None
    base = os.path.realpath(str(root))
    full = os.path.realpath(os.path.join(base, str(path)))
    if full != base and os.path.commonpath([base, full]) != base:
        return None
    return full


def upload_report(project, collection_dir) \
        -> List[Tuple[str, Optional[str], Optional[str], int, int]]:
    '''What is in an archive's collection, by (kind, name, dataroot): bytes and
    files. What a user is shown before anything moves.'''
    totals: Dict[Tuple[str, Optional[str], Optional[str]], Tuple[int, int]] = {}
    counted: List[str] = []
    for one in _values(project):
        if not _collected(one.value, collection_dir):
            continue
        path = str(one.value.resolve_path(search=[], collection_dir=str(collection_dir)))
        if any(path == seen or path.startswith(seen + os.sep) for seen in counted):
            continue
        counted.append(path)
        size, files = _weigh(path)
        group = (one.kind, one.name, one.dataroot)
        have = totals.get(group, (0, 0))
        totals[group] = (have[0] + size, have[1] + files)
    return [(kind, name, dataroot, size, files)
            for (kind, name, dataroot), (size, files)
            in sorted(totals.items(), key=lambda item: str(item[0]))]


def _weigh(path: str) -> Tuple[int, int]:
    if os.path.isfile(path):
        return os.path.getsize(path), 1
    size = files = 0
    for folder, _, names in os.walk(path):
        for name in names:
            try:
                size += os.path.getsize(os.path.join(folder, name))
                files += 1
            except OSError:
                pass
    return size, files


###########################
# What the flow reads (D129)
###########################

# The framework reads these of a node's task itself, whatever the task declares:
# the rest of `SchedulerNode.get_required_keys`. `exe` is the other entry there,
# and it is a name, never a path.
_TASK_READS = ("prescript", "postscript", "refdir", "script")


def required(project) -> Optional[Set[Tuple[str, ...]]]:
    '''The keys the flow reads: every running node's `require`, and its
    task's own scripts. None where no node declares any.

    🔴 **The one definition, read by both ends from the same manifest.** The
    client filters its archive and its `sources` by it; the server limits what
    it fetches and asks for, and refuses at submit what should have arrived and
    did not.

    ⚠️ **None means the set was not worked out** -- the client could not run
    setup, or a manifest written before it did -- and nothing is filtered. It is
    never the empty set: a flow whose every node reads nothing has no files to
    filter either.
    '''
    from siliconcompiler.remote.runflow import runtime_flow

    flow = project.get_flow()
    keys: Set[Tuple[str, ...]] = set()
    declared = False
    for step, index in runtime_flow(project).get_nodes():
        prefix = ("tool", flow.get(step, index, "tool"), "task", flow.get(step, index, "task"))
        for item in project.get(*prefix, "require", step=step, index=index) or []:
            keys.add(tuple(item.split(",")))
            declared = True
        for name in _TASK_READS:
            if project.get(*prefix, name, step=step, index=index):
                keys.add((*prefix, name))
    return keys if declared else None


def needed(key, required) -> bool:
    '''Whether the flow reads ``key``: always, where the set is unknown.'''
    return required is None or tuple(key) in required


class WorkedOut(NamedTuple):
    '''What one setup pass on a copy learns: every node's `require`; the
    Python environment of each executed node whose task reports one; each
    executed node's task, set up, with the tool versions it declared; and each
    node whose setup could not run here, with why.'''
    required: Dict[Tuple[str, str], List[str]]
    environments: Dict[Tuple[str, str], Any]
    tasks: Dict[Tuple[str, str], Any] = {}
    failed: Dict[Tuple[str, str], str] = {}


def work_out(project) -> WorkedOut:
    '''Every node's `require`, by running its setup on a throwaway copy --
    and, from the same pass, each node's own Python environment
    (`Task.get_python_environment`).

    🔴 **`require` is empty until setup runs**, and a remote run's setup runs
    in the job's image. So the client runs it here first, on a copy -- the
    caller's project is never touched -- and in the order a run does:

    - ``_init_run()`` first. It is what fills `asic,asiclib` from the main
      library, and without it no library's LEF, liberty or GDS is required.
    - Every node in execution order, since a node's setup reads its
      upstream's outputs to decide what it loads.

    Keyed by ``(step, index)``, for every node that set up and was not
    skipped. 🔴 **Each node on its own**: a setup that cannot run here -- a
    task needing what only its image has -- is recorded in ``failed`` and
    drops nothing of any other node. Environments and tasks are kept only for
    the nodes the run executes, the same `runtime_flow` the server derives.
    '''
    import copy
    import logging

    from siliconcompiler.remote.runflow import runtime_flow
    from siliconcompiler.scheduler.schedulernode import SchedulerNode

    work = copy.deepcopy(project)
    logger = work.logger
    level = logger.level
    # A run prints each node's setup, and prints it again on the server; here
    # it is noise, and a failure is reported once by the caller.
    logger.setLevel(logging.CRITICAL)
    try:
        work._init_run()
        flow = work.get_flow()
        executed = set(runtime_flow(work).get_nodes())
        declared: Dict[Tuple[str, str], List[str]] = {}
        environments: Dict[Tuple[str, str], Any] = {}
        tasks: Dict[Tuple[str, str], Any] = {}
        failed: Dict[Tuple[str, str], str] = {}
        for layer in flow.get_execution_order():
            for step, index in layer:
                node = SchedulerNode(work, step, index)
                try:
                    with node.runtime():
                        if not node.setup():
                            continue
                        environment = node.task.get_python_environment()
                        versions = list(node.task.get("version") or [])
                except Exception as e:                           # noqa: BLE001
                    failed[(step, index)] = str(e) or type(e).__name__
                    continue
                if (step, index) in executed:
                    tasks[(step, index)] = (node.task, versions)
                    if environment is not None:
                        environments[(step, index)] = environment
                values = work.get("tool", flow.get(step, index, "tool"),
                                  "task", flow.get(step, index, "task"), "require",
                                  step=step, index=index) or []
                declared[(step, index)] = list(dict.fromkeys(values))
        return WorkedOut(declared, environments, tasks, failed)
    finally:
        logger.setLevel(level)


def with_required(project, declared: Dict[Tuple[str, str], List[str]]):
    '''A copy of ``project`` carrying ``declared`` as each node's `require`:
    the manifest the client uploads, so the server reads the set from it.

    ⚠️ Only `require` is carried. Setup's other effects are the run's to make
    -- a second setup over them doubles every command-line option -- and
    `add_required_key` lists a key once, so the run's own setup adds nothing
    twice.
    '''
    import copy

    carried = copy.deepcopy(project)
    flow = carried.get_flow()
    for (step, index), values in declared.items():
        carried.set("tool", flow.get(step, index, "tool"), "task", flow.get(step, index, "task"),
                    "require", values, step=step, index=index)
    return carried
