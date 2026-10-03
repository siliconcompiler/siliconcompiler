'''
Reading what a job left behind without following it out.

🔴 A job writes its own build directory, so any path in it can be a symlink into
another job's data, the operator's private roots, or `/etc`. Every read this
server makes of a job's tree goes through here.

Race-free where the platform allows: each component is opened relative to the
one before and refused when it is a link, so a link swapped in after a check is
refused. A FIFO is refused too, since opening one blocks forever. Without
``dir_fd`` (Windows) the resolved path is checked instead, which narrows the
window without closing it. Only the root may be reached through a link: it is
the server's own directory.

🔴 An archive keeps a link inside the job as a link and follows none out of it
(database D142); nothing is copied in place of a link, since some tools keep
links to terabytes. See `add_tree`.
'''

import logging
import os
import stat
import tarfile

from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from siliconcompiler.remote import links

__all__ = ["open_inside", "size_inside", "inside", "add_tree", "add_file"]


logger = logging.getLogger("sc-server")


_SAFE = (hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")
         and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd
         and os.readlink in os.supports_dir_fd and os.scandir in os.supports_fd)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)


def inside(root, path) -> bool:
    '''Lexically under ``root``, and -- with links resolved -- still under it.'''
    try:
        _parts(root, path)
    except PermissionError:
        return False
    real_root = os.path.realpath(str(root))
    real = os.path.realpath(str(path))
    return real == real_root or real.startswith(real_root + os.sep)


def open_inside(root, path, mode: str = "rb", **kwargs):
    '''Open a regular file under ``root``, reached through no link; OSError otherwise.'''
    if "r" not in mode or any(flag in mode for flag in "wax+"):
        raise ValueError("only reading is confined")
    fd = _open_file(root, path)
    try:
        return os.fdopen(fd, mode, **kwargs)
    except BaseException:
        os.close(fd)
        raise


def size_inside(root, path) -> int:
    '''The size of a regular file under ``root``, or 0 where there is none.'''
    try:
        fd = _open_file(root, path)
    except OSError:
        return 0
    try:
        return os.fstat(fd).st_size
    finally:
        os.close(fd)


def add_file(tar: tarfile.TarFile, root, path, arcname: str) -> bool:
    '''Add one regular file to ``tar``, read through no link; False where it is not one.'''
    try:
        fd = _open_file(root, path)
    except OSError:
        return False
    with os.fdopen(fd, "rb") as handle:
        _add_open(tar, handle, os.fstat(handle.fileno()), arcname)
    return True


def add_tree(tar: tarfile.TarFile, root, top, base, skip: Iterable[str] = (),
             job_tree=None, homes: Optional["links.Homes"] = None) -> None:
    '''Add ``top`` and everything under it to ``tar``, named relative to ``base``.

    A link is never read through: a chain ending at a file or directory
    inside ``job_tree`` becomes one relative link to its end, and is dropped
    otherwise. With ``homes``, a hard-linked file becomes a link to its home
    outside ``top``, a tar hard link to its first name here, or is dropped
    when it has a name outside the job.
    '''
    skip = frozenset(skip)
    top, base = Path(top), Path(base)
    arcname = os.path.relpath(str(top), str(base))
    packing = _Packing(job_tree if job_tree is not None else top, top, homes)
    if not _SAFE:
        return _add_tree_by_path(tar, root, top, arcname, skip, packing)

    fd = _walk_to(*_parts(root, top))
    try:
        if arcname != os.curdir:
            tar.addfile(_dir_info(tar, arcname, os.fstat(fd)))
        _walk(tar, fd, top, arcname, skip, packing)
    finally:
        os.close(fd)


class _Packing:
    '''What one archive is being built from, and what it holds so far.'''

    def __init__(self, job_tree, top, homes):
        self.job_tree = Path(job_tree)
        self.real_top = os.path.realpath(str(top))
        self.homes = homes
        # Hard-linked files already stored: inode -> name.
        self.first: Dict[Tuple[int, int], str] = {}

    def holds(self, path: str) -> bool:
        return path == self.real_top or path.startswith(self.real_top + os.sep)


def _add_symlink(tar, packing: "_Packing", dir_path: Path, name: str, arcname: str,
                 mtime=None) -> None:
    '''Store a link as one relative link to where its chain ends in the job, or drop it.'''
    end = links.resolve(packing.job_tree, dir_path / name)
    if end is not None and packing.homes is not None and os.path.isfile(end):
        info = os.lstat(end)
        if info.st_nlink > 1:
            if packing.homes.leaves(info):
                end = None
            else:
                end = packing.homes.home(info) or end
    if end is None:
        logger.info(f"left out of an archive: {arcname}, a link that does not end "
                    "inside the job")
        return
    _write_link(tar, arcname, links.relative(end, os.path.realpath(str(dir_path))), mtime)


def _write_link(tar, arcname: str, target: str, mtime=None) -> None:
    link = tar.tarinfo(arcname)
    link.type, link.linkname = tarfile.SYMTYPE, target
    if mtime is not None:
        link.mtime = mtime
    tar.addfile(link)


def _add_regular(tar, packing: "_Packing", handle, info, dir_path: Path, arcname: str) -> None:
    '''Store a regular file's bytes, or a hard-linked one as a link to its home or first name.'''
    if info.st_nlink > 1 and packing.homes is not None:
        if packing.homes.leaves(info):
            # 🔴 A name outside the job: this could be PDK data hard-linked in.
            logger.info(f"left out of an archive: {arcname}, a file with a name "
                        "outside the job")
            return
        key = (info.st_dev, info.st_ino)
        if key in packing.first:
            member = tar.tarinfo(arcname)
            member.type, member.linkname = tarfile.LNKTYPE, packing.first[key]
            member.mtime = info.st_mtime
            tar.addfile(member)
            return
        home = packing.homes.home(info)
        if home is not None and not packing.holds(home):
            _write_link(tar, arcname,
                        links.relative(home, os.path.realpath(str(dir_path))),
                        info.st_mtime)
            return
        packing.first[key] = arcname
    _add_open(tar, handle, info, arcname)


######################################################################

def _parts(root, path):
    '''``path`` as components under ``root``, lexically; PermissionError if not under it.'''
    root = os.path.abspath(str(root))
    rel = os.path.relpath(os.path.abspath(str(path)), root)
    parts = rel.split(os.sep)
    if rel == os.curdir or os.path.isabs(rel) or os.pardir in parts:
        raise PermissionError(f"{path} is not under {root}")
    return root, parts


def _open_file(root, path) -> int:
    if not _SAFE:
        return _open_file_by_path(root, path)
    root, parts = _parts(root, path)
    parent = _walk_to(root, parts[:-1])
    try:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | _NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    return _regular(fd, path)


def _walk_to(root: str, parts) -> int:
    '''A directory fd for ``root/parts``, refusing a link at every step.'''
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
    except BaseException:
        os.close(fd)
        raise
    return fd


def _regular(fd: int, path) -> int:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise PermissionError(f"{path} is not a regular file")
    return fd


def _walk(tar, dir_fd, dir_path: Path, arcdir: str, skip, packing) -> None:
    with os.scandir(dir_fd) as entries:
        names = sorted(entry.name for entry in entries)
    for name in names:
        if name in skip:
            continue
        arcname = f"{arcdir}/{name}" if arcdir != os.curdir else name
        info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)

        if stat.S_ISLNK(info.st_mode):
            _add_symlink(tar, packing, dir_path, name, arcname, info.st_mtime)
        elif stat.S_ISDIR(info.st_mode):
            try:
                sub = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=dir_fd)
            except OSError:
                continue            # swapped for a link or removed underneath
            try:
                tar.addfile(_dir_info(tar, arcname, os.fstat(sub)))
                _walk(tar, sub, dir_path / name, arcname, skip, packing)
            finally:
                os.close(sub)
        elif stat.S_ISREG(info.st_mode):
            try:
                fd = _regular(os.open(name, os.O_RDONLY | os.O_NOFOLLOW | _NONBLOCK,
                                      dir_fd=dir_fd), name)
            except OSError:
                continue
            with os.fdopen(fd, "rb") as handle:
                _add_regular(tar, packing, handle, os.fstat(handle.fileno()), dir_path,
                             arcname)
        # Devices, FIFOs and sockets are nobody's results.


def _add_open(tar, handle, info, arcname: str) -> None:
    member = tar.tarinfo(arcname)
    member.size, member.mtime = info.st_size, info.st_mtime
    member.mode = stat.S_IMODE(info.st_mode)
    tar.addfile(member, handle)


def _dir_info(tar, arcname: str, info) -> tarfile.TarInfo:
    member = tar.tarinfo(arcname)
    member.type, member.mtime = tarfile.DIRTYPE, info.st_mtime
    member.mode = stat.S_IMODE(info.st_mode)
    return member


######################################################################
# Where there is no dir_fd
######################################################################

def _open_file_by_path(root, path) -> int:
    if not inside(root, path):
        raise PermissionError(f"{path} is not under {root}")
    real = os.path.realpath(str(path))
    # Checked before opening too: with no O_NONBLOCK, opening a FIFO blocks.
    if not stat.S_ISREG(os.stat(real).st_mode):
        raise PermissionError(f"{path} is not a regular file")
    return _regular(os.open(real, os.O_RDONLY | _NONBLOCK | getattr(os, "O_BINARY", 0)),
                    path)


def _add_tree_by_path(tar, root, top: Path, arcname: str, skip, packing) -> None:
    if not inside(root, top) or top.is_symlink():
        raise PermissionError(f"{top} is not under {root}")
    if arcname != os.curdir:
        tar.addfile(_dir_info(tar, arcname, top.stat()))
    for child in sorted(top.iterdir()):
        if child.name in skip:
            continue
        name = f"{arcname}/{child.name}" if arcname != os.curdir else child.name
        if child.is_symlink():
            _add_symlink(tar, packing, top, child.name, name)
        elif child.is_dir():
            _add_tree_by_path(tar, root, child, name, skip, packing)
        elif child.is_file():
            try:
                fd = _open_file(root, child)
            except OSError:
                continue
            with os.fdopen(fd, "rb") as handle:
                _add_regular(tar, packing, handle, os.fstat(handle.fileno()), top, name)
