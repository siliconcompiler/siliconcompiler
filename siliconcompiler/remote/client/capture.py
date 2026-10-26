'''
What a job's own Python needs, read from the static imports of each node's test
modules on the submitting machine: indexable distributions are listed at their
installed versions, others built as wheels (`wheels`), and the user's helper
modules sent as files.

What `requested_versions.python` names is never listed: the image holds it,
and a second copy would land on the tool's path.

Dynamic imports and imports under a platform check are not followed.
'''

import ast
import functools
import json
import os
import sys

from importlib import metadata
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

from siliconcompiler.remote import environment

__all__ = ["Reach", "Lists", "CannotForward", "reach", "lists", "place", "direct_url"]


class CannotForward(ValueError):
    '''What the client cannot send or read; ``compiled`` names a compiled file that stops it.'''

    def __init__(self, message: str, compiled: Optional[str] = None):
        super().__init__(message)
        self.compiled = compiled


class Reach(NamedTuple):
    '''What one node's Python reaches: ``{distribution: extras}``, ``{test:
    {path under its folder: helper file}}``, and what was not followed.'''
    distributions: Dict[str, Set[str]]
    helpers: Dict[str, Dict[str, str]]
    warnings: List[str]


class Lists(NamedTuple):
    '''The job's `python_packages` as ``(name, version)`` pairs, and the wheels to build.'''
    requirements: List[Tuple[str, str]]
    constraints: List[Tuple[str, str]]
    wheels: List[metadata.Distribution]
    warnings: List[str]


_PLATFORM = {("sys", "platform"), ("os", "name"), ("os", "uname"),
             ("platform", "system"), ("platform", "machine"), ("platform", "platform"),
             ("platform", "uname")}


def _imports(path: str) -> Tuple[Set[str], Set[str]]:
    '''``(top-level absolute imports, those only under a platform check)``,
    either branch, since the server's platform is unknown here.'''
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(path))
    except (OSError, SyntaxError, ValueError) as e:
        raise CannotForward(f"{path} cannot be read as Python ({e}), so what it "
                            "imports cannot be worked out") from None
    names, guarded = set(), set()
    todo = [(tree, False)]
    while todo:
        node, under = todo.pop()
        if isinstance(node, ast.If) and any(
                isinstance(test, ast.Attribute) and isinstance(test.value, ast.Name)
                and (test.value.id, test.attr) in _PLATFORM for test in ast.walk(node.test)):
            todo.extend((child, True) for child in node.body + node.orelse)
            continue
        found = guarded if under else names
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module.split(".")[0])
        todo.extend((child, under) for child in ast.iter_child_nodes(node))
    return names, guarded - names


def reach(sources: Iterable[str], requirements: Iterable[str] = ()) -> Reach:
    '''What the static imports of ``sources`` reach through the user's helper
    modules, plus the distributions ``requirements`` load by name.

    A helper is a module or package in a test's folder, found before any
    installed distribution of that name, as Python finds it on the node.
    '''
    from packaging.requirements import InvalidRequirement, Requirement

    owned = _module_distributions()
    stdlib = set(sys.stdlib_module_names)

    distributions: Dict[str, Set[str]] = {}
    helpers: Dict[str, Dict[str, str]] = {}
    warnings: List[str] = []

    for requirement in requirements:
        try:
            parsed = Requirement(requirement)
        except InvalidRequirement:
            warnings.append(f"{requirement} is not a PEP 508 requirement; it is not "
                            "listed")
            continue
        distributions.setdefault(environment.canonical(parsed.name), set()).update(parsed.extras)

    for test in sorted({os.path.abspath(path) for path in sources}):
        folder = os.path.dirname(test)
        found: Dict[str, str] = {}
        todo, seen, named = [test], set(), set()
        platform_only: Dict[str, str] = {}
        while todo:
            path = todo.pop()
            if path in seen:
                continue
            seen.add(path)
            imported, guarded = _imports(path)
            for name in sorted(guarded - stdlib):
                platform_only.setdefault(name, path)
            for name in sorted(imported):
                if name in stdlib or name in named:
                    continue
                named.add(name)
                helper = _helper(name, folder)
                if helper is not None:
                    for relative, file in _helper_files(name, helper, warnings):
                        found[relative] = file
                    todo.extend(_python_files(helper))
                    continue
                if name in owned:
                    for owner in owned[name]:
                        distributions.setdefault(environment.canonical(owner), set())
                    continue
                warnings.append(f"{os.path.basename(path)} imports {name}, which no "
                                "installed distribution provides and is not beside "
                                f"{os.path.basename(test)}; it is not sent")
        for name, path in sorted(platform_only.items()):
            # Only for what would otherwise have gone.
            if name not in named and (name in owned or _helper(name, folder)):
                warnings.append(f"{os.path.basename(path)} imports {name} only under a "
                                "platform check, so it is not sent; import it outside "
                                "the check if the server needs it")
        if found:
            helpers[test] = found

    return Reach(distributions, helpers, warnings)


def _helper(name: str, directory: str) -> Optional[str]:
    '''A module or package ``name`` in ``directory``, or None.'''
    module = os.path.join(directory, f"{name}.py")
    if os.path.isfile(module) and not os.path.islink(module):
        return module
    package = os.path.join(directory, name)
    if os.path.isdir(package) and not os.path.islink(package) \
            and any(True for _ in _python_files(package)):
        return package
    return None


def _helper_files(name: str, location: str, warnings: List[str]):
    '''``(path under the test's folder, file)`` per helper file: no bytecode, no link.'''
    if os.path.isfile(location):
        yield f"{name}{os.path.splitext(location)[1]}", location
        return
    for root, dirs, files in os.walk(location):
        for entry in list(dirs):
            if entry == "__pycache__":
                dirs.remove(entry)
            elif os.path.islink(os.path.join(root, entry)):
                dirs.remove(entry)
                warnings.append(f"the helper module {name}: {os.path.join(root, entry)} "
                                "is a link, and is not sent")
        dirs.sort()
        for entry in sorted(files):
            full = os.path.join(root, entry)
            if entry.endswith((".pyc", ".pyo")):
                continue
            if os.path.islink(full):
                warnings.append(f"the helper module {name}: {full} is a link, and is "
                                "not sent")
                continue
            relative = os.path.relpath(full, location).replace(os.sep, "/")
            yield f"{name}/{relative}", full


def _python_files(path: str):
    if os.path.isfile(path):
        if path.endswith(".py"):
            yield path
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__"
                         and not os.path.islink(os.path.join(root, d)))
        for name in sorted(files):
            if name.endswith(".py") and not os.path.islink(os.path.join(root, name)):
                yield os.path.join(root, name)


def lists(roots: Dict[str, Set[str]], provided: Iterable[str]) -> Lists:
    '''The job's `python_packages` and wheels from ``roots`` (:func:`reach`),
    less ``provided``, the `requested_versions.python` names the image holds.

    Requirements are the indexable roots; wheels, any reached distribution with
    a ``direct_url.json``; constraints, every other reached dependency.
    Only what the install needs, never everything installed: a stray
    constraint can only stop an install for no reason of the job's.
    '''
    from packaging.version import InvalidVersion, Version

    image = {environment.canonical(name) for name in provided} | {"siliconcompiler"}
    installed = _installed()
    warnings: List[str] = []

    reached = _closure(roots, image)
    wheels = [dist for key, dist in sorted(reached.items())
              if key not in image and direct_url(dist) is not None]
    carried = {key for key, dist in reached.items() if direct_url(dist) is not None}

    def version_of(dist) -> Optional[str]:
        try:
            return str(Version(dist.version))
        except InvalidVersion:
            return None

    requirements = []
    for key in sorted(roots):
        if key in image or key in carried:
            continue
        dist = installed.get(key)
        if dist is None:
            warnings.append(f"{key} is loaded by name and is not installed here; it "
                            "is not listed")
            continue
        version = version_of(dist)
        if version is None:
            raise CannotForward(
                f"{key} is installed here at {dist.version}, which is not a PEP 440 "
                "version, so the server cannot be told which to install")
        requirements.append((key, version))

    listed = {name for name, _ in requirements}
    constraints = []
    for key in sorted(reached):
        dist = installed.get(key)
        if key in image or key in listed or key in carried or dist is None:
            continue
        version = version_of(dist)
        if version is not None:
            constraints.append((key, version))

    entries = [f"{name}=={version}" for name, version in requirements + constraints]
    member = {"requirements": entries[:len(requirements)],
              "constraints": entries[len(requirements):]}
    if len(entries) > environment.MAX_ENTRIES or \
            len(json.dumps(member, separators=(",", ":")).encode()) > environment.MAX_BYTES:
        raise CannotForward(
            f"this run's Python reaches {len(entries)} installed distributions, and a "
            f"job lists at most {environment.MAX_ENTRIES}")

    for name, _ in requirements + constraints:
        for file in sorted(str(entry) for entry in installed[name].files or ()
                           if len(entry.parts) == 1 and entry.suffix == ".pth"):
            warnings.append(
                f"{name} installs {file}, a .pth file, which runs in every Python that "
                "starts with it on its path -- the node's among them")

    return Lists(requirements, constraints, wheels, warnings)


def place(files: Dict[str, str], path: str, source: str, what: str) -> None:
    '''Add one of the user's files at ``path``, refusing one that would not
    import on the node or would overwrite another source's.'''
    if source.lower().endswith(environment.COMPILED):
        # Refused, not warned about.
        raise CannotForward(
            f"{what} is your own code and holds a compiled extension, {source}, "
            "built for this machine; it will not import on the server. Publish it "
            "to an index, as a wheel for the server's platform")
    held = files.get(path)
    if held is not None and os.path.realpath(held) != os.path.realpath(source):
        raise CannotForward(
            f"two sources would both be sent as {path}: {held} and {source}. Rename "
            "one, or install one from an index")
    files[path] = source


@functools.lru_cache(maxsize=1)
def _module_distributions() -> Dict[str, List[str]]:
    return metadata.packages_distributions()


def _installed() -> Dict[str, metadata.Distribution]:
    '''Every installed distribution by canonical name; the first on ``sys.path`` wins.'''
    found: Dict[str, metadata.Distribution] = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name and environment.canonical(name) not in found:
            found[environment.canonical(name)] = dist
    return found


def _closure(roots: Dict[str, Set[str]], stop: Set[str] = frozenset()) \
        -> Dict[str, metadata.Distribution]:
    '''Every installed distribution ``roots`` pull in, never following ``stop``;
    only the roots' own extras are followed.'''
    from packaging.requirements import InvalidRequirement, Requirement

    found: Dict[str, metadata.Distribution] = {}
    todo: List[Tuple[str, Set[str]]] = [(name, set(extras)) for name, extras in roots.items()]

    while todo:
        name, extras = todo.pop()
        key = environment.canonical(name)
        if key in found or key in stop:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        found[key] = dist

        for dependency in dist.requires or []:
            try:
                parsed = Requirement(dependency)
            except InvalidRequirement:
                continue
            if parsed.marker and not any(parsed.marker.evaluate({"extra": extra})
                                         for extra in extras | {""}):
                continue
            todo.append((parsed.name, set(parsed.extras)))

    return found


def direct_url(dist: metadata.Distribution) -> Optional[dict]:
    '''PEP 610's record of where a distribution came from, if not an index.'''
    text = dist.read_text("direct_url.json")
    if not text:
        return None
    try:
        found = json.loads(text)
    except ValueError:
        return None
    return found if isinstance(found, dict) else None
