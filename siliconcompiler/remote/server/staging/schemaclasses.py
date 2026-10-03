'''
What a job's manifest may name, and nothing imported for it -- used inside the
manifest's read (`manifestread`), never in the API process.

🔴 **Contract §1, *No server process holding credentials parses a manifest*.**
The read runs in a process of its own while the job stages, and this is how it
resolves names there: SiliconCompiler reads a manifest by importing the module
each `__meta__` entry -- and each flowgraph node's `taskmodule` -- names, and
checks what it got afterwards, so the import has already run by then.

So the allowlist is the classes the reading process's installation provides,
loaded once as it starts: SiliconCompiler whole, its tool drivers, and every
installed distribution that depends on it -- the PDKs and libraries, a site's
own drivers. A manifest's name is looked up among them
(`remote.manifests`). A class that is not there resolves to its base type,
as it always has; a node's TASK class that is not there is refused
(`software-unavailable`, `unknown_class`), because a task's own methods run on
the node.

⚠️ The extracted tree is never on the reading process's `sys.path`: its working
directory is an empty one of its own, and nothing on `PYTHONPATH` is the job's.
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
    '''The top-level packages of every installed distribution that requires
    SiliconCompiler: where a PDK, a library or a tool driver comes from.'''
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
            # An optional dependency this server does not have: that module's
            # classes are not on offer here, which is the truthful answer.
            logger.debug(f"could not import {info.name}: {e}")
    return count
