'''
Links in a job's build directory, and where each one's file really lives.

Both ends pack a job's tree -- the client an upload, the server the archives a
run produces -- and both keep a link inside the job as a link, pointed at the
file's real home, and follow none out of it (contract.md, *An upload keeps
links, and stores a linked file once*; *A produced archive keeps a link inside
the job as a link, and follows none out of it*). This is the one reading of a
link both use.

🔴 **Link targets are read; a file is never opened through a link.**
:func:`resolve` walks a path one component at a time, reading each link it
meets and splicing its target in, so a link planted anywhere on the way is
read rather than followed, and a chain that leaves the tree is found before
anything outside it is touched.

SiliconCompiler's pass-through chain is two hops: a node's ``outputs/x`` links
to its ``inputs/x``, which links to the upstream node's ``outputs/x``. Its
``link_symlink_copy`` tries a hard link first, so the chain is usually one inode
under three names instead: :class:`Homes` finds a hard-linked file's home by
inode, as the name in the ``outputs/`` of the node that produced it.
'''

import os
import stat

from typing import Dict, List, Optional, Set, Tuple

__all__ = ["resolve", "follow", "Homes", "relative", "HOP_LIMIT",
           "OUTSIDE", "DANGLING", "LOOP", "OTHER"]


# How many links a chain may pass through before it is given up on as a loop.
HOP_LIMIT = 40


# Why a chain did not end inside the tree.
OUTSIDE = "outside"      # it leaves the tree
DANGLING = "dangling"    # it names nothing
LOOP = "loop"            # it passes the hop limit
OTHER = "other"          # it ends at something neither a file nor a directory


def resolve(tree, path) -> Optional[str]:
    '''Where ``path`` ends, every link on the way read: a regular file or a
    directory inside ``tree``, as a path under ``tree``'s real path -- or None
    for a chain that leaves ``tree``, dangles, loops, passes :data:`HOP_LIMIT`
    or ends at anything else.

    ``path`` is under ``tree``, lexically. ``tree`` itself may be reached
    through a link: it is where the job is kept, not something the job wrote.
    '''
    return follow(tree, path)[0]


def follow(tree, path) -> Tuple[Optional[str], Optional[str]]:
    '''As :func:`resolve`, and why not: ``(end, None)``, or ``(None, why)``
    with ``why`` one of :data:`OUTSIDE`, :data:`DANGLING`, :data:`LOOP` and
    :data:`OTHER`.'''
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
    '''Every hard-linked regular file in ``tree``, by inode, and each one's
    home: the name in the ``outputs/`` of the node that produced it -- the node
    whose ``outputs/`` holds the inode while its ``inputs/`` does not.

    Walked once, never through a link. Names are under ``tree``'s real path,
    as :func:`resolve` returns them.
    '''

    def __init__(self, tree):
        self.tree = os.path.realpath(str(tree))
        self._names: Dict[Tuple[int, int], List[str]] = {}
        # Each file the tree was walked again for, so none costs more than one.
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
        '''Whether the file has a name outside the tree -- more links than the
        tree holds names for it -- which could be data hard-linked in from
        anywhere, a PDK's included.

        🔴 **The tree is walked again before this says yes.** It is a running
        job's, and a name can appear in it after the walk: the scheduler
        hard-links a node's outputs into the next node's inputs as that node
        starts, which is the moment the node that finished is archived.
        Counted against the first walk alone, a file whose every name is in the
        job has one more link than names, and is left out of its node's
        results as if it had one outside. Once per file, since one that still
        has more links than names after a second walk does have a name outside.
        '''
        if info.st_nlink <= max(1, len(self.names(info))):
            return False
        key = (info.st_dev, info.st_ino)
        if key not in self._rewalked:
            self._rewalked.add(key)
            self._walk()
        return info.st_nlink > max(1, len(self.names(info)))

    def home(self, info) -> Optional[str]:
        '''The name in the producing node's ``outputs/``, or None where no
        node's ``outputs/`` holds the file.'''
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
