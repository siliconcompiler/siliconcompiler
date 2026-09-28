'''
What a node's own Python needs, read off the machine a job is submitted from.

A testbench imports whatever its author had installed, and the submitting
machine is the one place that environment is known to exist. So it is read
here, from the static imports of the node's test modules and, through them, of
the user's own helper modules (surface *A node's own Python packages, built
while staging*):

- **a distribution installed from an index** -- pinned at the version
  installed here, with what it depends on, for the server to install;
- **the user's own code** -- each helper module a test reaches that no
  installed distribution owns, and each package installed editable, from a
  local path or from git, which no index can reproduce -- sent as files, once
  per job, under their import names. Never installed, so none of it runs at
  build time.

🔴 **The image's set is left out, not just SiliconCompiler's.** What the job's
`requires.python` names -- SiliconCompiler and what its own process needs for
the node, cocotb for a cocotb task -- comes with the image the job resolves
to, and so does everything those depend on. Pinning any of it again would put
a second copy on the tool's path.

⚠️ **An import made dynamically -- through `importlib`, or a plugin entry
point -- is not followed.** The fix is a plain import in a test module.
'''

import ast
import functools
import importlib.util
import json
import os
import sys

from importlib import metadata
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

__all__ = ["Captured", "CannotForward", "imported_modules", "reached", "capture",
           "COMPILED"]


# A compiled extension: built for the submitting machine, so it will not
# import on the node.
COMPILED = (".so", ".pyd", ".dylib")


class CannotForward(ValueError):
    '''What the client cannot send as the user's own code, or cannot read.'''


class Captured(NamedTuple):
    '''What one node needs: pins from an index, and the user's own code as
    files, each ``{path under sc_python/packages/: the file here}``.'''
    pins: List[Tuple[str, str]]                  # (name, version)
    files: Dict[str, str]
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


def reached(sources: Iterable[str]) -> Tuple[Set[str], Dict[str, str], List[str]]:
    '''What the static imports of ``sources`` reach, followed through the
    user's own helper modules.

    Returns ``(modules an installed distribution owns, {helper import name: its
    file or package directory}, warnings)``. A helper is a module no installed
    distribution owns that is found beside a source that imports it, as a
    test runner puts a test's own directory on its path. Raises CannotForward
    for a source that cannot be read or parsed.
    '''
    owned = _module_distributions()
    stdlib = set(sys.stdlib_module_names)

    distributions: Set[str] = set()
    helpers: Dict[str, str] = {}
    warnings: List[str] = []
    todo = [os.path.abspath(path) for path in sources]
    seen: Set[str] = set()

    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in sorted(_imports(path)):
            if name in stdlib or name in helpers:
                continue
            if name in owned:
                distributions.add(name)
                continue
            found = _helper(name, os.path.dirname(path))
            if found is None:
                warnings.append(f"{os.path.basename(path)} imports {name}, which no "
                                "installed distribution provides and is not beside it; "
                                "it is not sent")
                continue
            helpers[name] = found
            todo.extend(_python_files(found))

    return distributions, helpers, warnings


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


def capture(sources: Iterable[str], requirements: Iterable[str],
            provided: Iterable[str], excluded: Iterable[str] = ()) -> Captured:
    '''What a node needs from this machine's Python.

    Args:
        sources: the node's test modules, whose static imports are followed.
        requirements: distributions, or PEP 508 requirements, it loads by name.
        provided: what the node's image holds -- SiliconCompiler and what the
            job's `requires.python` names -- and everything that pulls in.
        excluded: directories whose contents reach the node through their own
            dataroot -- a private or supplied one -- and so are never sent.

    Raises CannotForward for a source that cannot be read, a compiled
    extension among the user's own code, or two sources for one path.
    '''
    modules, helpers, warnings = reached(sources)
    excluded = [os.path.abspath(path) for path in excluded]

    roots = set(requirements)
    for module in modules:
        roots.update(_module_distributions().get(module, []))

    needed = _closure(sorted(roots))
    image = _closure(sorted(set(provided) | {"siliconcompiler"}))

    pins = []
    files: Dict[str, str] = {}
    for key, dist in sorted(needed.items()):
        if key in image:
            continue
        name, version = dist.metadata["Name"], dist.version
        if _direct_url(dist) is None:
            pins.append((name, version))
            continue
        # The user's own code, installed editable, from a local path or from
        # git: sent as files under its import names.
        for module, location in _package_paths(dist):
            _add(files, module, location, excluded, f"{name} {version}", warnings)

    for module, location in sorted(helpers.items()):
        _add(files, module, location, excluded, f"the helper module {module}", warnings)

    return Captured(pins, files, warnings)


def _add(files: Dict[str, str], module: str, location: str, excluded, what: str,
         warnings: List[str]) -> None:
    '''``location`` -- a module file or a package directory -- into
    ``files`` under ``module``, file by file.'''
    if any(location == root or location.startswith(root + os.sep) for root in excluded):
        return
    if os.path.isfile(location):
        place(files, f"{module}{os.path.splitext(location)[1]}", location, what)
        return
    for root, dirs, names in os.walk(location):
        for name in list(dirs):
            if name == "__pycache__":
                dirs.remove(name)
            elif os.path.islink(os.path.join(root, name)):
                dirs.remove(name)
                warnings.append(f"{what}: {os.path.join(root, name)} is a link, and is "
                                "not sent")
        dirs.sort()
        for name in sorted(names):
            full = os.path.join(root, name)
            if name.endswith((".pyc", ".pyo")):
                continue
            if os.path.islink(full):
                warnings.append(f"{what}: {full} is a link, and is not sent")
                continue
            relative = os.path.relpath(full, location).replace(os.sep, "/")
            place(files, f"{module}/{relative}", full, what)


def place(files: Dict[str, str], path: str, source: str, what: str) -> None:
    '''One file into the tree, refusing what would not import on the node or
    would overwrite another source's file.'''
    if source.endswith(COMPILED):
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
    from packaging.utils import canonicalize_name
    return canonicalize_name(name)


def _closure(requirements: Iterable[str]) -> Dict[str, metadata.Distribution]:
    '''Every installed distribution a set of requirements pulls in, by
    canonical name. Extras named here are followed, extras of dependencies
    are not, and what is not installed is left out.'''
    from packaging.requirements import InvalidRequirement, Requirement

    found: Dict[str, metadata.Distribution] = {}
    todo: List[Tuple[str, Set[str]]] = []
    for requirement in requirements:
        try:
            parsed = Requirement(requirement)
        except InvalidRequirement:
            continue
        todo.append((parsed.name, set(parsed.extras)))

    while todo:
        name, extras = todo.pop()
        key = _canonical(name)
        if key in found:
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


def _direct_url(dist: metadata.Distribution) -> Optional[dict]:
    '''PEP 610's record of where a distribution came from, if not an index.'''
    text = dist.read_text("direct_url.json")
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _package_paths(dist: metadata.Distribution) -> List[Tuple[str, str]]:
    '''Where a distribution's top-level modules are, found through the import
    system -- an editable install records only the hook pointing at its source
    -- as ``[(import name, module file or package directory)]``. A namespace
    package is every directory it spans, so packages sharing one merge.'''
    key = _canonical(dist.metadata["Name"])
    paths: List[Tuple[str, str]] = []
    for module, owners in sorted(_module_distributions().items()):
        if key not in [_canonical(owner) for owner in owners]:
            continue
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError):
            spec = None
        if spec is None:
            continue
        if spec.submodule_search_locations:
            for location in spec.submodule_search_locations:
                entry = (module, os.path.abspath(location))
                if entry not in paths:
                    paths.append(entry)
        elif spec.origin and os.path.isfile(spec.origin):
            paths.append((module, os.path.abspath(spec.origin)))
    return paths
