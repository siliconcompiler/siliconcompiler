'''
What a node's own Python needs, read off the machine a job is submitted from.

A testbench imports whatever its author had installed, and the submitting
machine is the one place that environment is known to exist. So it is read
here: each distribution the node's sources import, and everything those pull
in, less what the node's image already holds (surface D131):

- **from an index** -- pinned, for the server to install;
- **editable, local or VCS** -- which no index can reproduce -- forwarded as
  the user's own code, their package directories uploaded and put on the
  tool's `PYTHONPATH`. Never installed, so none of their code runs at build
  time.

🔴 **The image's set is left out, not just SiliconCompiler's.** What the job's
`requires.python` pins -- SiliconCompiler and what its own process needs for
the node, cocotb for a cocotb task -- comes with the image the job resolves
to. Pinning it again here would put a second copy on the tool's path, and the
simulator and SiliconCompiler would disagree about which one they loaded.

Carried over from the preliminary cocotb design; what changed is where the
result goes -- a file, and nothing installed here.
'''

import ast
import functools
import importlib.util
import json
import os
import sys

from importlib import metadata
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

__all__ = ["Captured", "imported_modules", "capture"]


class Captured(NamedTuple):
    '''What one node needs: pins from an index, and what is forwarded.'''
    pins: List[Tuple[str, str]]                  # (name, version)
    forwarded: List[Tuple[str, List[str]]]       # (name==version, directories)
    warnings: List[str]


def imported_modules(paths: Iterable[str]) -> Set[str]:
    '''The top-level modules Python sources import: absolute imports only,
    and the standard library left out. A file that cannot be read or parsed
    contributes nothing.'''
    names = set()
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
    return names - set(sys.stdlib_module_names)


def capture(modules: Iterable[str], requirements: Iterable[str],
            provided: Iterable[str]) -> Captured:
    '''What a node needs from this machine's Python.

    Args:
        modules: top-level modules the node's Python imports. A module no
            installed distribution provides is left out.
        requirements: distributions, or PEP 508 requirements, it loads by name.
        provided: what the node's image holds -- SiliconCompiler and what the
            job's `requires.python` pins -- and everything that pulls in.
    '''
    roots = set(requirements)
    for module in modules:
        roots.update(_module_distributions().get(module, []))

    needed = _closure(sorted(roots))
    image = _closure(sorted(set(provided) | {"siliconcompiler"}))

    pins, forwarded, warnings = [], [], []
    for key, dist in sorted(needed.items()):
        if key in image:
            continue
        name, version = dist.metadata["Name"], dist.version
        if _direct_url(dist) is None:
            pins.append((name, version))
            continue

        paths, skipped = _package_paths(dist)
        for module in skipped:
            warnings.append(f"{name}: module {module} is not a package directory, "
                            "so it is not sent")
        for path in paths:
            if not path.endswith(".dist-info") and _has_compiled_files(path):
                warnings.append(f"{name}: {path} holds compiled extensions, so the node "
                                "must match this machine's platform and Python")
        forwarded.append((f"{name}=={version}", paths))

    return Captured(pins, forwarded, warnings)


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


def _package_paths(dist: metadata.Distribution) -> Tuple[List[str], List[str]]:
    '''What to send for a distribution to import elsewhere: its package
    directories, found through the import system -- an editable install
    records only the hook pointing at its source -- and its metadata.
    Returns (paths, top-level modules that are not a directory).'''
    key = _canonical(dist.metadata["Name"])
    paths: List[str] = []
    skipped: List[str] = []
    for module, owners in sorted(_module_distributions().items()):
        if key not in [_canonical(owner) for owner in owners]:
            continue
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError):
            spec = None
        if spec is None or not spec.submodule_search_locations:
            skipped.append(module)
            continue
        location = os.path.abspath(list(spec.submodule_search_locations)[0])
        if location not in paths:
            paths.append(location)

    dist_info = getattr(dist, "_path", None)
    if dist_info and os.path.isdir(dist_info):
        paths.append(os.path.abspath(str(dist_info)))
    return paths, skipped


def _has_compiled_files(path: str) -> bool:
    for _, _, files in os.walk(path):
        if any(name.endswith((".so", ".pyd", ".dylib")) for name in files):
            return True
    return False
