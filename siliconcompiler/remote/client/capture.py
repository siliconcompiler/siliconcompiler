'''
What a job's own Python needs, read off the machine it is submitted from.

A testbench imports whatever its author had installed, and the submitting
machine is the one place that environment is known to exist. So it is read
here, from the static imports of each node's test modules and, through them, of
the user's own helper modules (surface *A node's own Python packages, built
while staging*):

- **a distribution an index can supply** -- listed in the create body's
  `python_packages` at the version installed here: in ``requirements`` where
  the run's code imports it or a task loads it by name, and in
  ``constraints`` for every other distribution installed here;
- **a distribution no index can supply** -- installed editable, from a local
  path or file, or from git, which pip records in a ``direct_url.json`` (PEP
  610) -- built into a wheel (`siliconcompiler.remote.client.wheels`), and in
  neither list;
- **the user's own modules** -- each helper module a test imports that sits
  beside it -- sent as collected files in the test's collected folder, keeping
  their names. Never installed, so none of it runs at build time.

🔴 **What the job's `requires.python` names is left out of both lists.**
SiliconCompiler and what its own process needs for the node, cocotb for a
cocotb task, come with the image the job resolves to, and listing any of them
would put a second copy on the tool's path.

⚠️ **An import made dynamically -- through `importlib`, or a plugin entry
point -- is not followed.** The fix is a plain import in a test module.
'''

import ast
import functools
import json
import os
import sys

from importlib import metadata
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

from siliconcompiler.remote import environment

__all__ = ["Reach", "Lists", "CannotForward", "imported_modules", "reach", "lists",
           "place", "direct_url", "COMPILED"]


COMPILED = environment.COMPILED


class CannotForward(ValueError):
    '''What the client cannot send, or cannot read.'''


class Reach(NamedTuple):
    '''What one node's Python reaches: the distributions it imports or loads
    by name, as ``{canonical name: extras}``; the helper modules beside each
    test, as ``{test: {path under the test's folder: the file here}}``; and
    what was not followed.'''
    distributions: Dict[str, Set[str]]
    helpers: Dict[str, Dict[str, str]]
    warnings: List[str]


class Lists(NamedTuple):
    '''The job's `python_packages`, as ``(name, version)`` pairs, and each
    distribution to build a wheel of.'''
    requirements: List[Tuple[str, str]]
    constraints: List[Tuple[str, str]]
    wheels: List[metadata.Distribution]
    warnings: List[str]


def imported_modules(paths: Iterable[str]) -> Set[str]:
    '''The top-level modules Python sources import: absolute imports only,
    and the standard library left out. A file that cannot be read or parsed
    contributes nothing.'''
    names = set()
    for path in paths:
        try:
            names.update(_imports(path))
        except CannotForward:
            continue
    return names - set(sys.stdlib_module_names)


def _imports(path: str) -> Set[str]:
    '''The top-level names one source imports absolutely. Raises
    CannotForward where it cannot be read or parsed.'''
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(path))
    except (OSError, SyntaxError, ValueError) as e:
        raise CannotForward(f"{path} cannot be read as Python ({e}), so what it "
                            "imports cannot be worked out") from None
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def reach(sources: Iterable[str], requirements: Iterable[str] = ()) -> Reach:
    '''What the static imports of ``sources`` reach, followed through the
    user's own helper modules, and the distributions ``requirements`` load by
    name.

    A helper is a module or package in a test's own folder -- which the tool
    puts on its path, as a test runner does -- and is found there before any
    installed distribution of the same name, as Python finds it. Its own
    imports are looked up in the same folder. Raises CannotForward for a
    source that cannot be read or parsed.
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
        distributions.setdefault(_canonical(parsed.name), set()).update(parsed.extras)

    for test in sorted({os.path.abspath(path) for path in sources}):
        folder = os.path.dirname(test)
        found: Dict[str, str] = {}
        todo, seen, named = [test], set(), set()
        while todo:
            path = todo.pop()
            if path in seen:
                continue
            seen.add(path)
            for name in sorted(_imports(path)):
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
                        distributions.setdefault(_canonical(owner), set())
                    continue
                warnings.append(f"{os.path.basename(path)} imports {name}, which no "
                                "installed distribution provides and is not beside "
                                f"{os.path.basename(test)}; it is not sent")
        if found:
            helpers[test] = found

    return Reach(distributions, helpers, warnings)


def _helper(name: str, directory: str) -> Optional[str]:
    '''A module or package ``name`` in ``directory``, as a test's own
    directory would supply it on the node.'''
    module = os.path.join(directory, f"{name}.py")
    if os.path.isfile(module) and not os.path.islink(module):
        return module
    package = os.path.join(directory, name)
    if os.path.isdir(package) and not os.path.islink(package) \
            and any(True for _ in _python_files(package)):
        return package
    return None


def _helper_files(name: str, location: str, warnings: List[str]):
    '''``(path under the test's folder, the file here)`` for a helper module
    or package, file by file: no bytecode, and no link.'''
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
    '''The job's `python_packages` and the distributions to build wheels of,
    from what the run's Python reaches (``roots``, as :func:`reach` gives
    them) and this machine's installed distributions.

    - **requirements**: each of ``roots`` installed here, no index can
      supply, and ``provided`` does not name;
    - **wheels**: each distribution with a ``direct_url.json`` among
      ``roots`` and what they depend on, ``provided`` left out and not
      followed;
    - **constraints**: every other distribution installed here, at its
      version.

    ``provided`` is the job's `requires.python` names -- SiliconCompiler among
    them -- which the image holds. Every version is in its canonical form, so
    each entry is one the server's grammar takes; a constraint whose version
    is not PEP 440 is left out, and a requirement whose version is not stops
    the run. Where the lists would pass the server's bounds, the constraints
    shrink to what the requirements and wheels depend on.
    '''
    from packaging.version import InvalidVersion, Version

    image = {_canonical(name) for name in provided} | {"siliconcompiler"}
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
    for key, dist in sorted(installed.items()):
        if key in image or key in listed or direct_url(dist) is not None:
            continue
        version = version_of(dist)
        if version is not None:
            constraints.append((key, version))

    def fits(constraints) -> bool:
        entries = [f"{name}=={version}" for name, version in requirements + constraints]
        member = {"requirements": entries[:len(requirements)],
                  "constraints": entries[len(requirements):]}
        return len(entries) <= environment.MAX_ENTRIES and \
            len(json.dumps(member, separators=(",", ":")).encode()) <= environment.MAX_BYTES

    if not fits(constraints):
        # A constraint applies only to a package the install needs, so the
        # ones nothing here depends on can go without changing it.
        needed = set(_closure({**roots, **{_canonical(dist.metadata["Name"]): set()
                                           for dist in wheels}}, image))
        constraints = [(name, version) for name, version in constraints if name in needed]
        if not fits(constraints):
            raise CannotForward(
                f"this run's Python reaches {len(requirements) + len(constraints)} "
                f"installed distributions, and a job lists at most "
                f"{environment.MAX_ENTRIES}")

    return Lists(requirements, constraints, wheels, warnings)


def place(files: Dict[str, str], path: str, source: str, what: str) -> None:
    '''One of the user's files into the tree, refusing what would not import
    on the node or would overwrite another source's file.'''
    if source.lower().endswith(COMPILED):
        # 🔴 Refused, not warned about: one built for this machine will not
        # import on the node.
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


def _canonical(name: str) -> str:
    return environment.canonical(name)


def _installed() -> Dict[str, metadata.Distribution]:
    '''Every distribution installed here, by canonical name: the first of a
    name on ``sys.path`` wins, as it does for an import.'''
    found: Dict[str, metadata.Distribution] = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if name and _canonical(name) not in found:
            found[_canonical(name)] = dist
    return found


def _closure(roots: Dict[str, Set[str]], stop: Set[str] = frozenset()) \
        -> Dict[str, metadata.Distribution]:
    '''Every installed distribution ``roots`` pull in, by canonical name,
    never following one in ``stop``. Extras named in ``roots`` are followed,
    extras of dependencies are not, and what is not installed is left out.'''
    from packaging.requirements import InvalidRequirement, Requirement

    found: Dict[str, metadata.Distribution] = {}
    todo: List[Tuple[str, Set[str]]] = [(name, set(extras)) for name, extras in roots.items()]

    while todo:
        name, extras = todo.pop()
        key = _canonical(name)
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
