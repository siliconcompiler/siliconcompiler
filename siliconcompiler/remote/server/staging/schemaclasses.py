'''
The classes a job's manifest may name, loaded inside the manifest's read
(`manifestread`), never in the API process.

SiliconCompiler resolves a manifest's `__meta__` and `taskmodule` names by
importing them. So the allowlist is what this installation
provides, loaded once: SiliconCompiler, and every installed distribution that
depends on it. A missing class resolves to its base type; a missing task class
is refused (`unknown_class`), since a task's own methods run on the node.
'''

import importlib
import logging
import pkgutil
import threading

from importlib import metadata

__all__ = ["load"]


logger = logging.getLogger("sc-server")

_lock = threading.Lock()
_loaded = False

# Never imported by the walk: a `__main__` runs its program, and the server's
# own modules are loaded already.
_SKIP = ("__main__", "siliconcompiler.remote.server")


def load() -> None:
    '''Import what this installation provides, once per process.'''
    global _loaded
    with _lock:
        if _loaded:
            return
        packages = ["siliconcompiler", *_dependents()]
        walked = 0
        for top in packages:
            walked += _walk(top)
        _loaded = True
        logger.info(f"loaded the schema classes of {', '.join(packages)} "
                    f"({walked} modules)")


def _dependents():
    '''The top-level packages of every installed distribution requiring SiliconCompiler.'''
    from packaging.requirements import InvalidRequirement, Requirement

    def requires_us(line) -> bool:
        try:
            return Requirement(line).name.lower() == "siliconcompiler"
        except InvalidRequirement:
            return False

    tops = metadata.packages_distributions()
    wanted = set()
    for dist in metadata.distributions():
        if any(requires_us(line) for line in dist.requires or []):
            wanted.add((dist.metadata["Name"] or "").lower())
    found = set()
    for top, owners in tops.items():
        if top.isidentifier() and any((owner or "").lower() in wanted for owner in owners):
            found.add(top)
    return sorted(found)


def _walk(top: str) -> int:
    try:
        package = importlib.import_module(top)
    except Exception as e:                                      # noqa: BLE001
        logger.debug(f"could not import {top}: {e}")
        return 0
    if not hasattr(package, "__path__"):
        return 1

    count = 1
    for info in pkgutil.walk_packages(package.__path__, f"{top}.", onerror=lambda name: None):
        if info.name.endswith(_SKIP[0]) or info.name.startswith(_SKIP[1]):
            continue
        try:
            importlib.import_module(info.name)
            count += 1
        except Exception as e:                                  # noqa: BLE001
            # A missing optional dependency: those classes are not on offer.
            logger.debug(f"could not import {info.name}: {e}")
    return count
