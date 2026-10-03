'''
Read a manifest somebody else wrote, importing nothing it names.

SiliconCompiler's reader imports each ``__meta__`` class, running its
import-time code for the manifest's writer. Here a class not already loaded has
its name dropped, and the base type is used. A node's ``taskmodule`` stays a
string: check it against :func:`known_classes` before anything loads it.
'''

from typing import Any, Dict, Optional, Type

__all__ = ["known_classes", "read"]


def known_classes() -> Dict[str, Type]:
    '''Every loaded subclass of `BaseSchema`, keyed ``module/Class``.'''
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
    '''The manifest at ``path``, or ``cfg``, as a project, importing nothing.'''
    from siliconcompiler import Project
    from siliconcompiler.schema import BaseSchema

    if path is not None:
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
