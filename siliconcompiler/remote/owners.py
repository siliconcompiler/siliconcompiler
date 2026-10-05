'''
What owns each file a job names, where it came from, and how it reaches a run.

The client asks this what to archive and what the server should supply; the
server asks it whether each file the manifest names arrived or can be supplied.

Every file is uploaded or supplied by identity: the server never reads
a path a job names, or a manifest could root a library at `/etc` and have the
server supply the host's files.

==============================  ===============  =================================
Dataroot source                 Outcome          How the server finds its copy
==============================  ===============  =================================
a local path, or no dataroot    uploaded         --
a ``$``-rooted path             uploaded         -- the CLIENT expands it
an editable Python package      uploaded         --
an installed Python package     supplied         by package name
git / https / any remote        supplied         by source and ref, allowlist only
marked private                  supplied, never  the operator's copy, by its
                                uploaded, never  keypath; else a copy held, or a
                                asked for        fetch, of its remote source
==============================  ===============  =================================

`+private` governs the bytes leaving the submitter, not where the server gets
them.

A dataroot is named by its keypath (:func:`dataroot_keypath`):
its own name is unique only within its owner.

The design always uploads; a PDK's, library's, device's or tool's files only
when local or editable. Private wins over both.

"Local" is the dataroot's registered SOURCE, never where the file is now: a
fetched PDK is on local disk too, and would upload with every job.

The table says whether a value MAY go up; the flow says whether it is NEEDED
(:func:`required`). Each value goes up on its own (:func:`collection`).
'''

import os
import re

from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Set, Tuple
from urllib.parse import urlsplit

__all__ = ["DESIGN", "PROJECT", "RESOURCE_KINDS", "LOCAL", "EDITABLE", "INSTALLED",
           "REMOTE", "PRIVATE", "UPLOADED", "SUPPLIED", "FETCH", "ASK", "UNAVAILABLE",
           "is_private", "skipped", "owner", "source", "uploads", "sources",
           "dataroot_keypath", "is_dataroot_keypath", "keypath_owner", "shown",
           "Unnamed",
           "safe_source", "masked", "is_masked", "has_userinfo", "Entry", "confined",
           "upload_report", "required",
           "needed", "work_out", "with_required", "WorkedOut", "installed_dataroots",
           "private_holders", "collection", "Collection", "collected_path",
           "value_records", "account_records", "uploaded_private"]


# Who a file belongs to, when it is neither a resource nor a tool.
DESIGN = "design"
PROJECT = "project"

# Kinds following the local-or-editable rule, as the API's `resource_kinds`.
RESOURCE_KINDS = ("pdk", "library", "fpga")

# Where a dataroot's files come from.
LOCAL = "local"            # a path on this machine, `$`-rooted included
EDITABLE = "editable"      # a Python package installed editable
INSTALLED = "installed"    # a Python package installed normally
REMOTE = "remote"          # git, https, or anything fetched -- cached or not
PRIVATE = "private"        # never leaves the machine


def is_private(resolver) -> bool:
    '''Whether a dataroot is marked ``+private`` (``file+private://`` and the rest).

    The one place the marker is tested.
    '''
    return bool(getattr(resolver, "is_private", False))


def skipped(key) -> bool:
    '''Path parameters that are not the run's input: what `collect` leaves out
    (`curation.never_collected`).'''
    from siliconcompiler.utils.curation import never_collected

    return never_collected(key)


def is_dataroot_keypath(keypath) -> bool:
    '''Whether ``keypath`` is ``library,<name>,dataroot,<root>`` or
    ``tool,<tool>,task,<task>,dataroot,<root>``; the server refuses any other.'''
    if not isinstance(keypath, (list, tuple)) or \
            not all(isinstance(part, str) and part for part in keypath):
        return False
    return (len(keypath) == 4 and keypath[0] == "library" and keypath[2] == "dataroot") \
        or (len(keypath) == 6 and keypath[0] == "tool" and keypath[2] == "task"
            and keypath[4] == "dataroot")


def keypath_owner(keypath) -> str:
    '''The name a dataroot's grant is checked against: the library's, or the task's tool.'''
    return keypath[1]


def shown(keypath) -> str:
    '''A keypath as SiliconCompiler prints one, ``tool,x,task,y,dataroot,z``.'''
    return ",".join(keypath)


class Unnamed(ValueError):
    '''A value whose dataroot neither keypath shape can name, so the server refuses it.'''

    def __init__(self, key, keypath):
        self.key, self.keypath = tuple(key), tuple(keypath)
        super().__init__(
            f"[{shown(key)}] reads the dataroot {shown(keypath)}, which is neither a "
            "library's nor a task's: a server names every dataroot by one of those, "
            "so this one cannot be supplied")


def _dataroot_section(schema):
    '''The nearest ancestor, itself included, defining a ``dataroot``, as
    `_find_files_dataroot_resolvers` finds it; None if none does.'''
    root = schema._parent(root=True)
    while not schema.valid("dataroot"):
        if schema is root:
            return None
        schema = schema._parent()
    return schema


def dataroot_keypath(project, key, dataroot: Optional[str]) -> Optional[Tuple[str, ...]]:
    '''The keypath of the dataroot one value of ``key`` resolves in: the
    defining schema's keypath plus ``dataroot,<dataroot>``, never a slice of
    ``key``. None for a value in no dataroot its section defines: it is local.'''
    if not dataroot:
        return None
    section = _dataroot_section(project.get(*key[:-1], field="schema"))
    if section is None or dataroot not in section.getkeys("dataroot"):
        return None
    return (*section._keypath, "dataroot", dataroot)


def owner(project, key) -> Tuple[str, Optional[str]]:
    '''``(kind, name)`` of the object a parameter belongs to; ``kind`` is never on the wire.

    Resource classes are tested BEFORE `Design`, which `PDK` and
    `StdCellLibrary` subclass: else every PDK would always upload.
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


def source(resolvers, dataroot: Optional[str], _seen=None) -> str:
    '''Where files under ``dataroot`` come from, judged by how it was REGISTERED.

    A ``$``-rooted path is LOCAL: the client expands and uploads it; the
    server never expands a variable. Anything untraceable is LOCAL too: sending
    the file cannot leave a job short.
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
    return LOCAL


def uploads(project, key, dataroot: Optional[str], resolvers) -> bool:
    '''Whether one value of one parameter goes in the archive.'''
    if skipped(key):
        return False

    kind = source(resolvers, dataroot)
    if kind == PRIVATE:
        return False

    who, _ = owner(project, key)
    if who in (DESIGN, PROJECT):
        return True

    return kind in (LOCAL, EDITABLE)


def safe_source(resolver) -> Optional[str]:
    '''A dataroot's source as it may leave this machine: `Resolver.safe_source`,
    the one definition, so what is sent and logged agree. None if unreadable.'''
    if resolver is None:
        return None
    try:
        return resolver.safe_source
    except (AttributeError, ValueError):
        return None


def masked(url: Optional[str]) -> str:
    '''A URL masked as `safe_source` would send it, for one that arrived as text.'''
    from siliconcompiler.package import Resolver

    return Resolver._masked_uri(url or "", show_userinfo=False)


def is_masked(url: Optional[str]) -> bool:
    '''Whether a source carries a masked query value (``?token=***`` or ``?***``).'''
    if not url:
        return False
    query = urlsplit(url).query
    return any(field.partition("=")[2] == "***" or field == "***"
               for field in re.split(r"[&;]", query) if field)


def has_userinfo(url: Optional[str]) -> bool:
    '''Whether a URL carries userinfo, read as `Resolver._masked_uri` does, so
    what a client strips and a server refuses agree.'''
    if not url or not isinstance(url, str):
        return False
    return "@" in urlsplit(url).netloc


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
    keypath: Optional[Tuple[str, ...]] = None   # the dataroot's: `dataroot_keypath`


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
        keypaths: Dict[Optional[str], Optional[Tuple[str, ...]]] = {}
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
                if dataroot not in keypaths:
                    keypaths[dataroot] = dataroot_keypath(project, key, dataroot)
                who, name = owner(project, key)
                yield _Value(tuple(key), one, resolvers,
                             DESIGN if who == PROJECT else who,
                             project.name if who == PROJECT else name,
                             dataroot, source(resolvers, dataroot),
                             step, index, keypaths[dataroot])


class Collection(NamedTuple):
    '''What `collect` is handed: each ``(key, step, index)`` holding a value
    to send, and ``select``, which takes exactly those values.'''
    keys: List[Tuple[Tuple[str, ...], Optional[str], Optional[str]]]
    select: Callable[[Tuple[str, ...], Optional[str], Optional[str], Any], bool]


def collection(project, pick: Callable[[_Value], bool]) -> Collection:
    '''Every value ``pick`` takes and no other: per value, never per parameter;
    the rest is never resolved.

    A private value is never picked, whatever ``pick`` says. ``select``
    knows values by object: call it on the project this was built from.
    '''
    from siliconcompiler.utils.curation import filter_collection_keys

    keys: Dict[Tuple[Tuple[str, ...], Optional[str], Optional[str]], None] = {}
    picked = set()
    for one in _values(project):
        if one.origin != PRIVATE and pick(one):
            keys[(one.key, one.step, one.index)] = None
            picked.add(id(one.value))

    def select(key, step, index, value) -> bool:
        return id(value) in picked

    return Collection(filter_collection_keys(list(keys)), select)


def _dataroot_id(one: _Value) -> Optional[str]:
    '''``one``'s dataroot as `collect` files it: its `collection_id`.'''
    return one.resolvers[one.dataroot].collection_id if one.dataroot else None


def collected_path(one: _Value) -> Optional[str]:
    '''Where `collect` puts ``one``, under the collection directory.'''
    from siliconcompiler.schema.parametervalue import PathNodeValue

    return PathNodeValue.generate_hashed_collection_path(one.value.get(), _dataroot_id(one))


def collected_paths(project, paths) -> Dict[str, str]:
    '''``{path: collected path}`` for each of ``paths`` a non-private value
    resolves to: where a test's helper modules go.'''
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
    '''The descriptor's `sources`: each dataroot the flow reads that the server
    should supply, by ``keypath``. Raises :class:`Unnamed`.

    Every URL is `safe_source`: enough to say what it is, not to fetch it. A
    private one carries its remote source and ref; a local
    private path is never sent.
    '''
    found: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for one in _values(project):
        if one.origin not in (INSTALLED, REMOTE, PRIVATE) or not one.dataroot:
            continue
        if not needed(one.key, required):
            continue
        if one.keypath is None or not is_dataroot_keypath(one.keypath):
            raise Unnamed(one.key, one.keypath or (*one.key[:-1], "dataroot", one.dataroot))
        if one.keypath in found:
            continue
        resolver = one.resolvers.get(one.dataroot)
        item = {"keypath": list(one.keypath), "private": one.origin == PRIVATE}
        if one.origin != PRIVATE or _remote(resolver):
            item["source"] = safe_source(resolver)
            ref = getattr(resolver, "reference", None)
            if ref:
                item["ref"] = ref
        found[one.keypath] = item
    return list(found.values())


def _distribution_of(module: Optional[str]) -> Optional[str]:
    '''The installed distribution that provides a top-level module.'''
    from importlib import metadata

    if not module:
        return None
    owners = metadata.packages_distributions().get(module.split(".", 1)[0]) or []
    return owners[0] if owners else None


def installed_dataroots(project, required=None) \
        -> List[Tuple[Tuple[str, ...], str]]:
    '''``(keypath, distribution)`` for each dataroot the flow reads from a
    normally installed package, which a server may supply by version.'''
    found: Dict[Tuple[str, ...], str] = {}
    for one in _values(project):
        if one.origin != INSTALLED or one.keypath is None or \
                not needed(one.key, required):
            continue
        if one.keypath in found:
            continue
        resolver = one.resolvers.get(one.dataroot)
        distribution = _distribution_of(getattr(resolver, "urlpath", None))
        if distribution:
            found[one.keypath] = distribution
    return sorted(found.items())


def private_holders(project, required=None) -> Set[str]:
    '''Distributions whose objects carry a private dataroot the flow reads: the
    server maps its copy by that object, so the job must land where it is.'''
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


# How the server accounts for a dataroot: worst first.
UNAVAILABLE = "unavailable"   # private and not supplied, or a path that escapes
ASK = "ask"                   # the client can send it, and has not
FETCH = "fetch"               # allowlisted, not held: fetched after submit
SUPPLIED = "supplied"         # held, private-mapped, or an installed package
UPLOADED = "uploaded"         # every file of it is in the archive

_WORST = (UNAVAILABLE, ASK, FETCH, SUPPLIED, UPLOADED)


class Entry(NamedTuple):
    '''How one dataroot's files, or one owner's outside any, reach the run.'''
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
    keypath: Optional[Tuple[str, ...]] = None   # the dataroot's; None for files in none

    @property
    def wire(self) -> Dict[str, Any]:
        '''As `upload_sources` spells it; only a dataroot is ever asked for.'''
        return {"kind": "dataroot", "keypath": list(self.keypath)}


def value_records(project, collection_dir, required=None) -> List[Dict[str, Any]]:
    '''Every value the flow reads, as plain data: the manifest's half of the
    accounting, :func:`account_records` the server's. ``collected_path`` is
    computed here, since the layout is the reading SiliconCompiler's.

    The server checks each ``collected`` path itself: whatever wrote the
    manifest decides what this says.
    '''
    records = []
    for one in _values(project):
        if not needed(one.key, required):
            continue
        record = {"key": list(one.key), "step": one.step, "index": one.index,
                  "kind": one.kind, "name": one.name, "dataroot": one.dataroot,
                  "keypath": list(one.keypath) if one.keypath else None,
                  "origin": one.origin, "path": one.value.get(),
                  "collected_path": collected_path(one),
                  "collected": None, "source": None, "ref": None, "package": None}
        found = _collected_at(one, collection_dir)
        if found is not None:
            record["collected"] = found
        resolver = one.resolvers.get(one.dataroot) if one.dataroot else None
        if one.origin == INSTALLED and resolver is not None:
            record["package"] = resolver.urlpath
        elif one.origin in (REMOTE, PRIVATE) and _remote(resolver):
            # A private source too: a held copy or a fetch supplies it.
            record["source"] = safe_source(resolver)
            record["ref"] = getattr(resolver, "reference", None)
        records.append(record)
    return records


def _remote(resolver) -> bool:
    '''Whether the resolver fetches remotely, private or not (`source` says PRIVATE first).'''
    from siliconcompiler.package import RemoteResolver

    return isinstance(resolver, RemoteResolver)


def uploaded_private(records, collection_dir) -> List[Tuple[Tuple[str, ...], str]]:
    '''Each private value the archive carries anyway, as ``(keypath, member)``,
    found by the server itself: the archive is refused.'''
    found = []
    for record in records:
        where = record.get("collected")
        if record.get("origin") != PRIVATE or not where or not collection_dir:
            continue
        full = confined(collection_dir, where)
        if full is not None and os.path.exists(full):
            found.append((tuple(record.get("keypath") or record["key"]),
                          f"sc_collected_files/{where}"))
    return found


def account_records(records, collection_dir, supply, required=None) -> List[Entry]:
    '''Every file the flow reads, as how it reaches the run: the server's half
    of the accounting, from :func:`value_records`. ``supply`` answers for this
    server; ``required`` None accounts for every file.

    No path the job names is read: a file is uploaded, or supplied by
    identity and confined to that root; else `ASK` or `UNAVAILABLE`.
    Given ``required``, a supplied file must be THERE, else `UNAVAILABLE`.
    An upload counts only where it really is inside ``collection_dir``.
    '''
    groups: Dict[Tuple[Optional[str], ...], Entry] = {}

    for record in records:
        key = tuple(record["key"])
        if not needed(key, required):
            continue
        entry = _one(record, collection_dir, supply, present=required is not None)
        # By keypath; files in no dataroot, by owner.
        keypath = record.get("keypath")
        group = tuple(keypath) if keypath else \
            (record["kind"], record["name"], record["dataroot"])
        held = groups.get(group)
        if held is None or _WORST.index(entry.status) < _WORST.index(held.status):
            groups[group] = entry

    return sorted(groups.values(),
                  key=lambda e: (_WORST.index(e.status), e.kind, str(e.name),
                                 str(e.dataroot), e.keypath or ()))


def _one(record, collection_dir, supply, present: bool = False) -> Entry:
    path = record["path"]
    keypath = tuple(record["keypath"]) if record.get("keypath") else None
    base = dict(kind=record["kind"], name=record["name"], dataroot=record["dataroot"],
                origin=record["origin"], key=tuple(record["key"]), path=path,
                keypath=keypath)

    # Private wins over everything, the archive included, and is NEVER asked for.
    if record["origin"] == PRIVATE:
        root = supply.private_root(keypath) if keypath else None
        if root:
            return _supplied(base, root, path, present)
        remote, ref = record.get("source"), record.get("ref")
        if remote:
            if not _relative_and_inside(path):
                return Entry(**base, status=UNAVAILABLE,
                             why="a path that escapes its dataroot")
            held = supply.held(remote, ref)
            if held:
                return _supplied(base, held, path, present)
            if supply.allowlisted(remote, ref):
                return Entry(**base, status=FETCH, source=remote, ref=ref)
        return Entry(**base, status=UNAVAILABLE,
                     why="a private dataroot this server has no copy of, and cannot "
                         "fetch either" + ("" if remote else
                                           ": its source is on the submitter's machine"))

    found = record.get("collected")
    held = confined(collection_dir, found) if found and collection_dir else None
    if held is not None and os.path.exists(held):
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
    '''A file under a server root: confined to it and, where the flow reads it, there.'''
    full = confined(root, path)
    if full is None:
        return Entry(**base, status=UNAVAILABLE, why="a path that escapes its dataroot")
    if present and not os.path.exists(full):
        return Entry(**base, status=UNAVAILABLE,
                     why=f"{path} is not in this server's copy")
    return Entry(**base, status=SUPPLIED, root=root)


def _in_collection(one: _Value, collection_dir) -> Optional[str]:
    '''Where ``one`` resolves in ``collection_dir``, absolute; None if absent.'''
    if not collection_dir or not os.path.isdir(collection_dir):
        return None
    try:
        found = one.value.resolve_path(search=[], collection_dir=str(collection_dir),
                                       dataroot_id=_dataroot_id(one))
    except FileNotFoundError:
        return None
    return str(found) if found else None


def _collected_at(one: _Value, collection_dir) -> Optional[str]:
    '''`_in_collection`, relative to ``collection_dir``.'''
    found = _in_collection(one, collection_dir)
    if not found:
        return None
    base = os.path.abspath(str(collection_dir))
    found = os.path.abspath(str(found))
    if found == base or os.path.commonpath([base, found]) != base:
        return None
    return os.path.relpath(found, base).replace(os.sep, "/")


def _relative_and_inside(path) -> bool:
    '''Lexically: relative, and not climbing out of wherever it is joined.'''
    text = str(path or "")
    if not text or os.path.isabs(text) or text.startswith("$") or "\x00" in text:
        return False
    return not os.path.normpath(text).startswith("..")


def confined(root, path) -> Optional[str]:
    '''``root/path`` if it stays under ``root`` once symlinks resolve, else None.

    Never trusted: ``../../etc/passwd`` or a symlink out must not escape.
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
    '''Bytes and files in an archive's collection by (kind, name, dataroot),
    shown before anything moves. Each stored file counts once.'''
    totals: Dict[Tuple[str, Optional[str], Optional[str]], Tuple[int, int]] = {}
    counted: Set[Tuple[int, int]] = set()
    for one in _values(project):
        path = _in_collection(one, collection_dir)
        if not path or not path.startswith(str(collection_dir)):
            continue
        size, files = _weigh(path, counted)
        if not files:
            continue
        group = (one.kind, one.name, one.dataroot)
        have = totals.get(group, (0, 0))
        totals[group] = (have[0] + size, have[1] + files)
    return [(kind, name, dataroot, size, files)
            for (kind, name, dataroot), (size, files)
            in sorted(totals.items(), key=lambda item: str(item[0]))]


def _weigh(path: str, counted: Set[Tuple[int, int]]) -> Tuple[int, int]:
    '''Bytes and files under ``path`` not yet in ``counted`` (by inode), adding
    them: links name a file already counted.'''
    if os.path.isdir(path):
        found = (os.path.join(folder, name)
                 for folder, _, names in os.walk(path) for name in names)
    else:
        found = iter([path])
    size = files = 0
    for full in found:
        try:
            info = os.stat(full)
        except OSError:
            continue
        if (info.st_dev, info.st_ino) in counted:
            continue
        counted.add((info.st_dev, info.st_ino))
        size += info.st_size
        files += 1
    return size, files


# Read by the framework whatever the task declares (`SchedulerNode.get_required_keys`,
# less `exe`, a name).
_TASK_READS = ("prescript", "postscript", "refdir", "script")


def required(project) -> Optional[Set[Tuple[str, ...]]]:
    '''The keys the flow reads: every running node's `require` and its task's scripts.

    The one definition, read by both ends from the same manifest.
    None means not worked out, so nothing is filtered; never the empty set.
    '''
    from siliconcompiler.flowgraph import RuntimeFlowgraph

    flow = project.get_flow()
    keys: Set[Tuple[str, ...]] = set()
    declared = False
    for step, index in RuntimeFlowgraph.from_project(project).get_nodes():
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
    '''One setup pass, per node: `require`, Python environment, the set-up task
    with its declared versions, and why a setup failed.'''
    required: Dict[Tuple[str, str], List[str]]
    environments: Dict[Tuple[str, str], Any]
    tasks: Dict[Tuple[str, str], Any]
    failed: Dict[Tuple[str, str], str]


def work_out(project) -> WorkedOut:
    '''Every node's `require` and Python environment, by running setup on a copy.

    `require` is empty until setup runs, which remotely is in the image, so
    it runs here first, in a run's order: ``_init_run()`` (it fills
    `asic,asiclib`), then nodes in execution order. Each node on its own: a
    failing setup goes in ``failed`` and drops nothing else.
    '''
    import copy
    import logging

    from siliconcompiler.flowgraph import RuntimeFlowgraph
    from siliconcompiler.scheduler.schedulernode import SchedulerNode

    work = copy.deepcopy(project)
    logger = work.logger
    level = logger.level
    # Noise here: the caller reports a failure once.
    logger.setLevel(logging.CRITICAL)
    try:
        work._init_run()
        flow = work.get_flow()
        executed = set(RuntimeFlowgraph.from_project(work).get_nodes())
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
    '''A copy carrying ``declared`` as each node's `require`: the manifest uploaded.

    Only `require`: a second setup over setup's other effects doubles options.
    '''
    import copy

    carried = copy.deepcopy(project)
    flow = carried.get_flow()
    for (step, index), values in declared.items():
        carried.set("tool", flow.get(step, index, "tool"), "task", flow.get(step, index, "task"),
                    "require", values, step=step, index=index)
    return carried
