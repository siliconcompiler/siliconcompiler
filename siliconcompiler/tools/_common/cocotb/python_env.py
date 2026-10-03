"""
Carry a cocotb testbench's Python environment from the machine it was submitted
from to the node that runs it.

A testbench imports whatever its author had installed. The submitting machine
is the only place that environment is known to exist, so it is captured there:
packages that came from an index are pinned, to be installed on the node, and
packages that cannot be installed from an index -- editable, local and VCS
installs -- are copied forward. The node installs only the pins its own Python
does not already satisfy.
"""

import ast
import functools
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import uuid

from importlib import metadata
from typing import Dict, Iterable, List, Optional, Set, Tuple


# Distributions the node always provides: it runs siliconcompiler to execute
# the node at all, so siliconcompiler and everything it depends on are there.
_NODE_PROVIDED_ROOT = "siliconcompiler"

# Reported by the Python that will run the simulation. Run as a standalone
# script so it imports nothing but cocotb, whatever else is on the path.
_COCOTB_CONFIG_SCRIPT = """
import json, sys
import cocotb_tools.config as config
import find_libpython
sim = sys.argv[1]
print(json.dumps({
    "libs_dir": str(config.libs_dir),
    "share_dir": str(config.share_dir),
    "vpi_lib": str(config.lib_name_path("vpi", sim)),
    "lib_entry": config.lib_entry("vpi", sim),
    "pygpi_entry": config.pygpi_entry_point(),
    "libpython": find_libpython.find_libpython(),
}))
"""


def imported_modules(paths: Iterable[str]) -> Set[str]:
    """
    Returns the top-level modules imported by Python source files.

    Only absolute imports are returned, and the standard library is left out.
    A file that cannot be read or parsed contributes nothing.

    Args:
        paths (list of str): Python source files.

    Returns:
        set of str: Top-level module names.
    """
    names = set()
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
    return names - set(sys.stdlib_module_names)


@functools.lru_cache(maxsize=1)
def _module_distributions() -> Dict[str, List[str]]:
    return metadata.packages_distributions()


def _canonical(name: str) -> str:
    from packaging.utils import canonicalize_name
    return canonicalize_name(name)


def _closure(requirements: Iterable[str]) -> Dict[str, metadata.Distribution]:
    """
    Returns the installed distributions a set of requirements pulls in.

    Args:
        requirements (list of str): Distribution names or PEP 508 requirements.
            Extras named here are followed; extras of dependencies are not.

    Returns:
        dict: Canonical distribution name to its installed distribution.
            Requirements that are not installed are left out.
    """
    from packaging.requirements import Requirement, InvalidRequirement

    found = {}
    todo: List[Tuple[str, Set[str]]] = []
    for requirement in requirements:
        try:
            req = Requirement(requirement)
        except InvalidRequirement:
            continue
        todo.append((req.name, set(req.extras)))

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
                req = Requirement(dependency)
            except InvalidRequirement:
                continue
            if req.marker and not any(req.marker.evaluate({"extra": extra})
                                      for extra in extras | {""}):
                continue
            todo.append((req.name, set(req.extras)))

    return found


def _direct_url(dist: metadata.Distribution) -> Optional[dict]:
    """PEP 610 record of where a distribution was installed from, if not an index."""
    text = dist.read_text("direct_url.json")
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _package_paths(dist: metadata.Distribution) -> Tuple[List[str], List[str]]:
    """
    Locates what has to be copied for a distribution to be importable elsewhere.

    Follows the import system rather than the distribution's file list: an
    editable install records only the hook that points at its source.

    Returns:
        tuple: (paths, skipped) where paths are the distribution's package
            directories and its metadata directory, and skipped names the
            top-level modules that could not be copied as a directory.
    """
    key = _canonical(dist.metadata["Name"])
    paths = []
    skipped = []
    for module, owners in sorted(_module_distributions().items()):
        if key not in [_canonical(owner) for owner in owners]:
            continue
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError):
            spec = None
        if spec is None or not spec.submodule_search_locations:
            # A single-file module, or one that is not importable here
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
        if any(f.endswith((".so", ".pyd", ".dylib")) for f in files):
            return True
    return False


def capture(modules: Iterable[str], requirements: Iterable[str]) \
        -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Captures what a node needs from this machine's Python environment.

    Args:
        modules (list of str): Top-level modules the node's Python code imports.
            Modules no installed distribution provides are ignored.
        requirements (list of str): Further distribution names or PEP 508
            requirements the node needs.

    Returns:
        tuple: (install, forward_packages, forward_paths, warnings) where
            install is a list of ``name==version`` pins for distributions that
            came from an index, forward_packages is the same for distributions
            that have to be copied, forward_paths are the directories to copy
            for them, and warnings are messages for the user.
    """
    roots = set(requirements)
    for module in modules:
        roots.update(_module_distributions().get(module, []))

    needed = _closure(sorted(roots))
    provided = _closure([_NODE_PROVIDED_ROOT])

    install = []
    forward_packages = []
    forward_paths = []
    warnings = []
    for key, dist in sorted(needed.items()):
        if key in provided:
            continue

        pin = f"{dist.metadata['Name']}=={dist.version}"
        if _direct_url(dist) is None:
            install.append(pin)
            continue

        paths, skipped = _package_paths(dist)
        for module in skipped:
            warnings.append(f"{dist.metadata['Name']}: module {module} is not a package "
                            "directory and will not be copied to the node")
        for path in paths:
            if not path.endswith(".dist-info") and _has_compiled_files(path):
                warnings.append(f"{dist.metadata['Name']}: {path} contains compiled "
                                "extensions, so the node must match this platform and Python")
        forward_packages.append(pin)
        forward_paths.extend(paths)

    return install, forward_packages, forward_paths, warnings


def is_installed(pin: str) -> bool:
    """
    Checks whether this Python has exactly the version a ``name==version`` pin names.

    Args:
        pin (str): A ``name==version`` pin, as :func:`capture` produces.

    Returns:
        bool: True if the distribution is installed at that version.
    """
    name, _, version = pin.partition("==")
    try:
        return metadata.version(name) == version
    except metadata.PackageNotFoundError:
        return False


def install(pins: List[str], root: str, logger) -> str:
    """
    Installs pinned distributions into a directory for use on ``PYTHONPATH``.

    The directory is keyed by this Python and platform and by the pins, so it is
    built once and shared by every node that asks for the same set. It is built
    under a lock beside it and moved into place only once complete, so a
    directory that exists is a directory that is finished.

    Args:
        pins (list of str): ``name==version`` pins. Their dependencies are not
            resolved, since a pin set from :func:`capture` already contains them.
        root (str): Directory holding the installed sets.
        logger (logging.Logger): Where to report the installation.

    Returns:
        str: The directory the distributions are installed in.

    Raises:
        RuntimeError: If the installation fails.
    """
    from fasteners import InterProcessLock

    tag = sys.implementation.cache_tag
    key = hashlib.sha256(json.dumps({
        "python": tag,
        "platform": sysconfig.get_platform(),
        "pins": sorted(pins)
    }).encode()).hexdigest()[:16]
    target = os.path.join(root, f"{tag}-{key}")

    if os.path.isdir(target):
        return target

    os.makedirs(root, exist_ok=True)
    with InterProcessLock(f"{target}.lock"):
        if os.path.isdir(target):
            return target

        logger.info(f"Installing Python packages for this node into {target}: "
                    f"{', '.join(sorted(pins))}")
        staging = f"{target}.{uuid.uuid4().hex}"
        cmd = [sys.executable, "-m", "pip", "install",
               "--no-deps", "--no-input", "--disable-pip-version-check",
               "--target", staging, *sorted(pins)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, text=True)
        if proc.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError(f"Unable to install Python packages for this node "
                               f"({' '.join(cmd)}):\n{proc.stdout}")
        os.rename(staging, target)

    return target


def cocotb_config(sim: str, python_path: List[str]) -> dict:
    """
    Reports where cocotb keeps what a simulator loads, as the simulator will
    see it: this Python, with ``python_path`` ahead of its own packages.

    Args:
        sim (str): The simulator, as cocotb names it.
        python_path (list of str): Directories ahead of this Python's own.

    Returns:
        dict: ``libs_dir``, ``share_dir``, ``vpi_lib``, ``lib_entry``,
            ``pygpi_entry`` and ``libpython``.

    Raises:
        RuntimeError: If cocotb cannot be found.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        python_path + [p for p in os.getenv("PYTHONPATH", "").split(os.pathsep) if p])

    # Run from a directory with no Python modules in it: -c puts the working
    # directory first on the path.
    proc = subprocess.run([sys.executable, "-c", _COCOTB_CONFIG_SCRIPT, sim],
                          env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, text=True,
                          cwd=os.path.dirname(sys.executable))
    if proc.returncode != 0:
        raise RuntimeError(f"Unable to locate cocotb for {sim}:\n{proc.stderr}")
    return json.loads(proc.stdout)
