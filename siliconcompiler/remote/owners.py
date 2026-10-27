'''
What owns each file a job names, where it came from, and how it reaches a run.

The client asks this what to archive and what the server should supply.

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
them. An installed package uploads unless the server lists it at the installed
version (:func:`walk`).

A dataroot is named by its keypath (:func:`dataroot_keypath`):
its own name is unique only within its owner.

The design always uploads; a PDK's, library's, device's or tool's files only
when local or editable. Private wins over both.

"Local" is the dataroot's registered SOURCE, never where the file is now: a
fetched PDK is on local disk too, and would upload with every job.

The table says whether a value MAY go up; the flow says whether it is NEEDED
(:func:`required`). Each value goes up on its own (:func:`collection`).
'''

import functools
import os
import re

from typing import Any, Callable, Dict, List, NamedTuple, Optional, Set, Tuple
from urllib.parse import urlsplit

from siliconcompiler.remote.environment import canonical

__all__ = ["DESIGN", "PROJECT", "LOCAL", "EDITABLE", "INSTALLED",
           "REMOTE", "PRIVATE", "is_private", "owner", "source", "walk", "sources",
           "dataroot_keypath", "is_dataroot_keypath", "shown",
           "Unnamed",
           "safe_source", "masked", "is_masked", "has_userinfo",
           "upload_report", "required",
           "needed", "work_out", "with_required", "WorkedOut", "distributions_of",
           "module_distributions", "supplied_distributions", "not_sent_roots",
           "private_holders", "collection", "Collection", "collected_path"]


# Who a file belongs to, when it is neither a resource nor a tool.
DESIGN = "design"
PROJECT = "project"

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


def is_dataroot_keypath(keypath) -> bool:
    '''Whether ``keypath`` is ``library,<name>,dataroot,<root>`` or
    ``tool,<tool>,task,<task>,dataroot,<root>``; the server refuses any other.'''
    if not isinstance(keypath, (list, tuple)) or \
            not all(isinstance(part, str) and part for part in keypath):
        return False
    return (len(keypath) == 4 and keypath[0] == "library" and keypath[2] == "dataroot") \
        or (len(keypath) == 6 and keypath[0] == "tool" and keypath[2] == "task"
            and keypath[4] == "dataroot")


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
    # The package providing an INSTALLED dataroot, or holding a PRIVATE one.
    distribution: Optional[str] = None
    # Whether the server lists that package at the installed version (`walk`).
    listed: bool = False

    @property
    def upload(self) -> bool:
        '''Whether this value goes in the archive: the design always; a resource's
        or tool's only where local or editable, or from an installed package the
        server does not list at this version; never a private one.'''
        if self.origin == PRIVATE:
            return False
        if self.kind == DESIGN:
            return True
        if self.origin == INSTALLED:
            return not self.listed
        return self.origin in (LOCAL, EDITABLE)


def _lists(software: Dict[str, List[str]], distribution: Optional[str]) -> bool:
    '''Whether ``software`` (`GET /v1`'s `software.python`) lists ``distribution``
    at the version installed here. None, or a package not installed, never is.'''
    from importlib import metadata
    from packaging.version import InvalidVersion, Version

    if not distribution:
        return False
    try:
        mine = Version(metadata.version(distribution))
        return any(Version(version) == mine
                   for version in software.get(canonical(distribution)) or [])
    except (InvalidVersion, metadata.PackageNotFoundError):
        return False


def walk(project, software: Optional[Dict[str, List[str]]] = None) -> List[_Value]:
    '''Every value of every path parameter a run reads, with its owner, where it
    comes from and whether it uploads: walked once, for every question below.

    ``software`` is what the server lists under `software.python`; None lists none.
    '''
    from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue
    from siliconcompiler.utils.curation import never_collected

    software = software or {}
    found: List[_Value] = []
    for key in sorted(project.allkeys(include_default=False)):
        if never_collected(key):
            continue
        param = project.get(*key, field=None)
        if not param.is_path:
            continue

        schema = None
        places: Dict[Optional[str], Tuple] = {}
        for held, step, index in param.getvalues(return_values=False):
            if not held.has_value:
                continue
            if schema is None:
                schema = project.get(*key[:-1], field="schema")
                resolvers = schema._find_files_dataroot_resolvers(True)
                who, name = owner(project, key)
                kind, name = (DESIGN, project.name) if who == PROJECT else (who, name)
            ones = held.values if isinstance(held, (NodeSetValue, NodeListValue)) \
                else [held]
            for one in ones:
                if one.get() is None:
                    continue
                dataroot = one.get(field="dataroot")
                if dataroot not in places:
                    origin = source(resolvers, dataroot)
                    resolver = resolvers.get(dataroot)
                    distribution = None
                    if origin == INSTALLED:
                        distribution = _distribution_of(resolver.urlpath)
                    elif origin == PRIVATE:
                        distribution = _distribution_of(type(schema).__module__)
                    places[dataroot] = (dataroot_keypath(project, key, dataroot), origin,
                                        distribution, origin == INSTALLED
                                        and _lists(software, distribution))
                keypath, origin, distribution, listed = places[dataroot]
                found.append(_Value(tuple(key), one, resolvers, kind, name, dataroot,
                                    origin, step, index, keypath, distribution, listed))
    return found


class Collection(NamedTuple):
    '''What `collect` is handed: each ``(key, step, index)`` holding a value
    to send, and ``select``, which takes exactly those values.'''
    keys: List[Tuple[Tuple[str, ...], Optional[str], Optional[str]]]
    select: Callable[[Tuple[str, ...], Optional[str], Optional[str], Any], bool]


def collection(values: List[_Value], pick: Callable[[_Value], bool]) -> Collection:
    '''Every value ``pick`` takes and no other: per value, never per parameter;
    the rest is never resolved.

    A private value is never picked, whatever ``pick`` says. ``select``
    knows values by object: call it on the project ``values`` were walked from.
    '''
    from siliconcompiler.utils.curation import filter_collection_keys

    keys: Dict[Tuple[Tuple[str, ...], Optional[str], Optional[str]], None] = {}
    picked = set()
    for one in values:
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


def collected_paths(values: List[_Value], paths) -> Dict[str, str]:
    '''``{path: collected path}`` for each of ``paths`` a non-private value
    resolves to: where a test's helper modules go.'''
    wanted = {os.path.realpath(str(path)): str(path) for path in paths}
    found: Dict[str, str] = {}
    for one in values:
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


def sources(values: List[_Value], required=None) -> List[Dict[str, Any]]:
    '''The descriptor's `sources`: each dataroot the flow reads that the server
    should supply, by ``keypath``, so none whose values go up. Raises :class:`Unnamed`.

    Every URL is `safe_source`: enough to say what it is, not to fetch it. A
    private one carries its remote source and ref; a local
    private path is never sent.
    '''
    found: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for one in values:
        if one.origin not in (INSTALLED, REMOTE, PRIVATE) or not one.dataroot:
            continue
        if not needed(one.key, required) or one.upload:
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


@functools.lru_cache(maxsize=1)
def module_distributions() -> Dict[str, List[str]]:
    '''Every installed top-level module and the distributions providing it.
    Read once: it walks every installed distribution's file list.'''
    from importlib import metadata

    return metadata.packages_distributions()


def distributions_of(module: Optional[str]) -> List[str]:
    '''The installed distributions providing a module's top-level package. A
    task's ``module/Class`` name is read as its module; `__main__` has none.'''
    top = (module or "").split("/", 1)[0].split(".", 1)[0]
    return [] if top in ("", "__main__") else module_distributions().get(top, [])


def _distribution_of(module: Optional[str]) -> Optional[str]:
    found = distributions_of(module)
    return found[0] if found else None


def supplied_distributions(values: List[_Value], required=None) -> Set[str]:
    '''The packages the flow reads a dataroot from that the server lists at the
    installed version, so it supplies them by name.'''
    return {one.distribution for one in values if one.listed and needed(one.key, required)}


def not_sent_roots(values: List[_Value], required=None) -> List[str]:
    '''Where each private dataroot, and each one the server supplies, is on this
    machine: files there reach a node through their own dataroot, never as code
    the user sent.'''
    supplied = {one.keypath for one in values
                if one.listed and one.keypath and needed(one.key, required)}
    roots = set()
    for one in values:
        if one.origin == PRIVATE or one.keypath in supplied:
            resolver = one.resolvers.get(one.dataroot)
            try:
                path = resolver.get_path() if resolver is not None else None
            except Exception:                                    # noqa: BLE001
                path = None
            if path:
                roots.add(str(path))
    return sorted(roots)


def private_holders(values: List[_Value], required=None) -> Set[str]:
    '''Distributions whose objects carry a private dataroot the flow reads: the
    server maps its copy by that object, so the job must land where it is.'''
    return {one.distribution for one in values
            if one.origin == PRIVATE and one.distribution and needed(one.key, required)}


def _remote(resolver) -> bool:
    '''Whether the resolver fetches remotely, private or not (`source` says PRIVATE first).'''
    from siliconcompiler.package import RemoteResolver

    return isinstance(resolver, RemoteResolver)


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


def upload_report(values: List[_Value], collection_dir) \
        -> List[Tuple[str, Optional[str], Optional[str], int, int]]:
    '''Bytes and files in an archive's collection as (kind, name, dataroot),
    shown before anything moves; the dataroot by its keypath, since two owners
    may each have a `root`. Each stored file counts once.'''
    totals: Dict[Tuple[str, Optional[str], Optional[str]], Tuple[int, int]] = {}
    counted: Set[Tuple[int, int]] = set()
    for one in values:
        path = _in_collection(one, collection_dir)
        if not path or not path.startswith(str(collection_dir)):
            continue
        size, files = _weigh(path, counted)
        if not files:
            continue
        group = (one.kind, one.name, shown(one.keypath) if one.keypath else one.dataroot)
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
    A node whose `require` is absent, not empty, was not worked out, so
    neither is the set.
    '''
    from siliconcompiler.flowgraph import RuntimeFlowgraph

    flow = project.get_flow()
    keys: Set[Tuple[str, ...]] = set()
    declared = False
    for step, index in RuntimeFlowgraph.from_project(project).get_nodes():
        prefix = ("tool", flow.get(step, index, "tool"), "task", flow.get(step, index, "task"))
        if not project.get(*prefix, "require", field=None).is_set(step, index):
            return None
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
    with its declared versions, why a setup failed, and whether its inputs arrive.'''
    required: Dict[Tuple[str, str], List[str]]
    environments: Dict[Tuple[str, str], Any]
    tasks: Dict[Tuple[str, str], Any]
    failed: Dict[Tuple[str, str], str]
    unfed: Set[Tuple[str, str]]


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
        unfed: Set[Tuple[str, str]] = set()
        for layer in flow.get_execution_order():
            for step, index in layer:
                node = SchedulerNode(work, step, index)
                try:
                    with node.runtime():
                        if not node.setup():
                            # Skipped: it reads nothing, which is known.
                            declared[(step, index)] = []
                            continue
                        environment = node.task.get_python_environment()
                        versions = list(node.task.get("version") or [])
                        fed = node.task._validate_io()
                except Exception as e:                           # noqa: BLE001
                    failed[(step, index)] = str(e) or type(e).__name__
                    continue
                if (step, index) in executed:
                    tasks[(step, index)] = (node.task, versions)
                    if not fed:
                        unfed.add((step, index))
                    if environment is not None:
                        environments[(step, index)] = environment
                values = work.get("tool", flow.get(step, index, "tool"),
                                  "task", flow.get(step, index, "task"), "require",
                                  step=step, index=index) or []
                declared[(step, index)] = list(dict.fromkeys(values))
        return WorkedOut(declared, environments, tasks, failed, unfed)
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
