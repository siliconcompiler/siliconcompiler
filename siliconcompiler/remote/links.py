'''
Links in a job's build directory, and where each one's file really lives: the
one reading both ends use to keep a link inside the job as a link and follow
none out of it (contract.md, *An upload keeps links, and stores a linked file once*).

Link targets are read; a file is never opened through a link. :func:`resolve`
walks one component at a time, so a chain leaving the tree is caught first.

A pass-through is often one inode under three names (hard links):
:class:`Homes` finds its home in the producing node's ``outputs/``.
'''

import os
import stat

from typing import Dict, List, Optional, Set, Tuple

__all__ = ["resolve", "follow", "Homes", "relative", "HOP_LIMIT",
           "OUTSIDE", "DANGLING", "LOOP", "OTHER"]


# Links a chain may pass before it counts as a loop.
HOP_LIMIT = 40


# Why a chain did not end inside the tree.
OUTSIDE = "outside"      # it leaves the tree
DANGLING = "dangling"    # it names nothing
LOOP = "loop"            # it passes the hop limit
OTHER = "other"          # it ends at something neither a file nor a directory


def resolve(tree, path) -> Optional[str]:
    '''Where ``path`` (under ``tree``) ends with every link read: a file or
    directory under ``tree``'s real path, else None. ``tree`` itself may be a link.'''
    return follow(tree, path)[0]


def follow(tree, path) -> Tuple[Optional[str], Optional[str]]:
    '''As :func:`resolve`, as ``(end, None)`` or ``(None, why)``.'''
    base = os.path.abspath(str(tree))
    real_base = os.path.realpath(base)
    start = os.path.abspath(str(path))
    within = _under(start, base)
    if within is None:
        within = _under(start, real_base)
    if within is None:
        return None, OUTSIDE

    resolved = real_base
    pending = [part for part in within.split(os.sep) if part]
    hops = HOP_LIMIT
    while pending:
        part = pending.pop(0)
        if part == os.curdir:
            continue
        if part == os.pardir:
            if resolved == real_base:
                return None, OUTSIDE
            resolved = os.path.dirname(resolved)
            continue
        candidate = os.path.join(resolved, part)
        try:
            info = os.lstat(candidate)
        except OSError:
            return None, DANGLING
        if stat.S_ISLNK(info.st_mode):
            hops -= 1
            if hops < 0:
                return None, LOOP
            try:
                target = os.readlink(candidate)
            except OSError:
                return None, DANGLING
            if os.path.isabs(target):
                inner = _under(os.path.normpath(target), base)
                if inner is None:
                    inner = _under(os.path.normpath(target), real_base)
                if inner is None:
                    return None, OUTSIDE
                resolved = real_base
                pending = [piece for piece in inner.split(os.sep) if piece] + pending
            else:
                pending = [piece for piece in target.replace("\\", "/").split("/")
                           if piece] + pending
            continue
        if pending and not stat.S_ISDIR(info.st_mode):
            return None, DANGLING
        resolved = candidate

    if resolved == real_base:
        return None, OTHER
    try:
        info = os.lstat(resolved)
    except OSError:
        return None, DANGLING
    if stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode):
        return resolved, None
    return None, OTHER


def relative(target: str, link_dir: str) -> str:
    '''The link to write in ``link_dir`` so that it names ``target``.'''
    return os.path.relpath(target, link_dir).replace(os.sep, "/")


class Homes:
    '''Every hard-linked file in ``tree`` by inode, and its home: the name in the
    ``outputs/`` of the node whose ``inputs/`` lacks it. Never walked through a link.'''

    def __init__(self, tree):
        self.tree = os.path.realpath(str(tree))
        self._names: Dict[Tuple[int, int], List[str]] = {}
        self._rewalked: Set[Tuple[int, int]] = set()
        self._walk()

    def _walk(self) -> None:
        names: Dict[Tuple[int, int], List[str]] = {}
        for here, dirs, files in os.walk(self.tree, followlinks=False):
            dirs.sort()
            for name in sorted(files):
                full = os.path.join(here, name)
                try:
                    info = os.lstat(full)
                except OSError:
                    continue
                if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
                    names.setdefault((info.st_dev, info.st_ino), []).append(full)
        self._names = names

    def names(self, info) -> List[str]:
        '''Every name the tree holds for the file ``info`` describes.'''
        return list(self._names.get((info.st_dev, info.st_ino), ()))

    def leaves(self, info) -> bool:
        '''Whether the file has more links than names in the tree: hard-linked
        in from outside, a PDK's perhaps.

        Walked again, once per file, before saying yes: in a running job the
        next node's inputs gain hard links just as the finished node is archived.
        '''
        if info.st_nlink <= max(1, len(self.names(info))):
            return False
        key = (info.st_dev, info.st_ino)
        if key not in self._rewalked:
            self._rewalked.add(key)
            self._walk()
        return info.st_nlink > max(1, len(self.names(info)))

    def home(self, info) -> Optional[str]:
        '''The name in the producing node's ``outputs/``, or None.'''
        names = self.names(info)
        placed: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
        for name in names:
            parts = os.path.relpath(name, self.tree).split(os.sep)
            if len(parts) >= 4 and parts[2] in ("outputs", "inputs"):
                placed.setdefault((parts[0], parts[1]), {}).setdefault(
                    parts[2], []).append(name)
        homes = sorted(held["outputs"][0] for held in placed.values()
                       if held.get("outputs") and not held.get("inputs"))
        return homes[0] if homes else None


def _under(path: str, base: str) -> Optional[str]:
    '''``path`` relative to ``base`` where it is under it, else None.'''
    if path == base:
        return ""
    prefix = base.rstrip(os.sep) + os.sep
    if not path.startswith(prefix):
        return None
    return path[len(prefix):]
