'''
Reading a manifest somebody else wrote, importing nothing it names.

SiliconCompiler reads a manifest by importing the module each ``__meta__``
entry names and checking what it got afterwards, so that module's import-time
code has already run for whoever wrote the manifest. Here every class a
manifest names is looked up among the classes this process has already loaded
first: one that is not there has its name dropped, and the reader takes the
base type its ``sctype`` names, which is a lookup and never an import.

A node's task class is not imported by reading at all: it is the node's
``taskmodule`` string until something asks for the task. Check it against
:func:`known_classes` before anything does.

Used wherever a manifest crosses between the client and the server: the
server's read of an upload, and the client's of what a job sent back.
'''

from typing import Any, Dict, Optional, Type

__all__ = ["known_classes", "read"]


def known_classes() -> Dict[str, Type]:
    '''Every loaded subclass of `BaseSchema`, keyed ``module/Class`` as a
    manifest names one.'''
    from siliconcompiler.schema import BaseSchema

    found = {BaseSchema}
    pending = [BaseSchema]
    while pending:
        for sub in pending.pop().__subclasses__():
            if sub not in found:
                found.add(sub)
                pending.append(sub)
    return {f"{cls.__module__}/{cls.__name__}": cls for cls in found}


def read(path: Optional[str] = None, cfg: Optional[Dict[str, Any]] = None,
         lazyload: bool = True):
    '''The manifest at ``path``, or the dictionary ``cfg``, loaded as a project
    with nothing imported on its behalf.'''
    from siliconcompiler import Project
    from siliconcompiler.schema import BaseSchema

    if path is not None:
        # SiliconCompiler's own reader, a gzipped manifest included.
        cfg = BaseSchema._read_manifest(path)
    _forget_unknown(cfg, known_classes())
    return Project.from_manifest(cfg=cfg, lazyload=lazyload)


def _forget_unknown(node, known) -> None:
    '''Drop every ``__meta__`` class name not in ``known``, in place.'''
    if not isinstance(node, dict):
        return
    meta = node.get("__meta__")
    if isinstance(meta, dict) and meta.get("class") is not None \
            and meta["class"] not in known:
        del meta["class"]
    for key, value in node.items():
        if key != "__meta__":
            _forget_unknown(value, known)
