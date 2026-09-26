'''
Reading a job's manifest as data: what it may name, and nothing imported for it.

🔴 **Contract §1: `__meta__` resolves through an allowlist, never through
`importlib.import_module()` on a name the manifest supplied.** SiliconCompiler
reads a manifest by importing the module each `__meta__` entry -- and each
flowgraph node's `taskmodule` -- names, and checks what it got afterwards, so
the import has already run by then. A manifest is written by whoever uploads
it, and the API process holds the signing key and the store.

So the allowlist is the classes this server's own installation provides,
loaded once at start-up: SiliconCompiler whole, its tool drivers, and every
installed distribution that depends on it -- the PDKs and libraries, a site's
own drivers. A manifest's name is looked up among them
(`known_classes_only`). A class that is not there resolves to its base type,
as it always has; a node's TASK class that is not there is refused at submit
(`software-unavailable`, `unknown_class`), because a task's own methods run on
the node.

⚠️ The data directory is also kept off `sys.path` (see `create_app`): an
extracted archive must never be importable in this process, whatever names it.
'''

import importlib
import logging
import pkgutil
import threading

from importlib import metadata

from siliconcompiler.schema.baseschema import known_classes_only

__all__ = ["load", "reading"]


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


def reading():
    '''The context every manifest a job uploaded is read in.'''
    load()
    return known_classes_only()


def _dependents():
    '''The top-level packages of every installed distribution that requires
    SiliconCompiler: where a PDK, a library or a tool driver comes from.'''
    tops = metadata.packages_distributions()
    wanted = set()
    for dist in metadata.distributions():
        requires = [(requirement or "").split(";")[0].strip().lower()
                    for requirement in dist.requires or []]
        if any(requirement.startswith("siliconcompiler") and
               requirement[len("siliconcompiler"):len("siliconcompiler") + 1] in
               ("", " ", "=", ">", "<", "!", "~", "[", "(")
               for requirement in requires):
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
