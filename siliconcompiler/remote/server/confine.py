'''
Reading what a job left behind without following it out.

🔴 **A job's build directory is written by the job.** A node's own code -- an
`execute` task, a user's script -- can leave a symlink anywhere in it, and an
upstream output can be one. A server that opens a path there follows the link:
into another job's data, the private roots the operator configured, or `/etc`.
Every read this server makes of a job's tree goes through here: the logs and
manifests it indexes, the archives it builds, the live tail and the progress
file.

**Race-free where the platform allows it.** Each component is opened relative
to the one before it and refused when it is a link, so a link swapped in after
a check is refused rather than followed. A FIFO is refused too: opening one
blocks the reader forever. Where there is no ``dir_fd`` (Windows), the path is
resolved and checked to stay under the root instead, which narrows the window
without closing it.

Only the ROOT may be reached through a link: it is the server's own directory,
and a datadir mounted through one is ordinary.

🔴 **An archive keeps a link inside the job as a link, pointed at the file's
real home, and follows none out of it** (contract.md, *A produced archive keeps
a link inside the job as a link*; database D142). Nothing is copied in place of
a link: some tools keep links in their own databases, and copying their
targets could store terabytes. A chain is read hop by hop (`links.resolve`);
one that ends at a regular file or a directory inside the job's build
directory becomes one relative link to where it ends, so SiliconCompiler's
``outputs/x`` -> ``inputs/x`` -> upstream ``outputs/x`` is one link to the
upstream node's ``outputs/x``. A hard-linked file is found its home by inode
(`links.Homes`): stored as a link to it where that is another node, as a tar
hard link where its other name is already in the archive. A chain that leaves
the job, dangles or loops, and a file with a name outside the job, are dropped
and logged, never stored.
'''

import logging
import os
import stat
import tarfile

from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from siliconcompiler.remote import links

__all__ = ["open_inside", "size_inside", "inside", "add_tree", "add_file",
           "link_stays_inside"]


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
    '''``path`` opened for reading, where it is a regular file under ``root``
    reached through no link. Raises OSError otherwise.'''
    if "r" not in mode or any(flag in mode for flag in "wax+"):
        raise ValueError("only reading is confined")
    fd = _open_file(root, path)
    try:
        return os.fdopen(fd, mode, **kwargs)
    except BaseException:
        os.close(fd)
        raise


def size_inside(root, path) -> int:
    '''The size of a regular file under ``root``, or 0 where there is none --
    not yet written, a link, or anything else.'''
    try:
        fd = _open_file(root, path)
    except OSError:
        return 0
    try:
        return os.fstat(fd).st_size
    finally:
        os.close(fd)


def add_file(tar: tarfile.TarFile, root, path, arcname: str) -> bool:
    '''One regular file into ``tar``, read through no link. False where it is
    not one.'''
    try:
        fd = _open_file(root, path)
    except OSError:
        return False
    with os.fdopen(fd, "rb") as handle:
        _add_open(tar, handle, os.fstat(handle.fileno()), arcname)
    return True


def add_tree(tar: tarfile.TarFile, root, top, base, skip: Iterable[str] = (),
             job_tree=None, homes: Optional["links.Homes"] = None) -> None:
    '''``top`` and everything under it into ``tar``, named relative to
    ``base``, never reading through a link out of ``root``.

    A link is stored as a link, never read through: where its chain ends at a
    regular file or directory inside ``job_tree`` -- the job's build directory
    -- as one relative link to where it ends, and dropped otherwise. With
    ``homes``, a hard-linked file becomes a link to its home where that is
    outside ``top``, a tar hard link where its first name is already in this
    archive, and is dropped where it has a name outside the job. A name in
    ``skip`` is left out wherever it appears.
    '''
    skip = frozenset(skip)
    top, base = Path(top), Path(base)
    arcname = os.path.relpath(str(top), str(base))
    packing = _Packing(job_tree if job_tree is not None else top, top, homes)
    if not _SAFE:
        return _add_tree_by_path(tar, root, top, arcname, skip, packing)

    fd = _open_dir(root, top)
    try:
        if arcname != os.curdir:
            tar.addfile(_dir_info(tar, arcname, os.fstat(fd)))
        _walk(tar, root, fd, top, arcname, skip, packing)
    finally:
        os.close(fd)


class _Packing:
    '''What one archive is being built from, and what it holds so far.'''

    def __init__(self, job_tree, top, homes):
        self.job_tree = Path(job_tree)
        self.real_top = os.path.realpath(str(top))
        self.homes = homes
        # Each hard-linked file already stored, by inode, and the name it is
        # stored under.
        self.first: Dict[Tuple[int, int], str] = {}

    def holds(self, path: str) -> bool:
        return path == self.real_top or path.startswith(self.real_top + os.sep)


def link_stays_inside(tree, link_dir, target: str) -> bool:
    '''Whether a link in ``link_dir`` naming ``target`` resolves inside
    ``tree``, lexically -- as an extractor would see it. An absolute target
    never does: it names this server's paths whatever it points at.'''
    if not target or os.path.isabs(target) or target.startswith(("/", "\\")):
        return False
    here = os.path.relpath(str(link_dir), str(tree))
    resolved = os.path.normpath(os.path.join(here, target))
    return resolved != os.pardir and not resolved.startswith(os.pardir + os.sep) \
        and not os.path.isabs(resolved)


def _add_symlink(tar, packing: "_Packing", dir_path: Path, name: str, arcname: str,
                 mtime=None) -> None:
    '''A link, as one relative link to where its chain ends inside the job
    -- a hard-linked end at its home -- or nothing.'''
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
    '''A regular file: its bytes, or -- hard-linked -- a link to its home or
    to its first name in this archive.'''
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
    '''``path`` as components under ``root``, lexically. Raises
    PermissionError for one that is not under it at all.'''
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


def _open_dir(root, path) -> int:
    root, parts = _parts(root, path)
    return _walk_to(root, parts)


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


def _walk(tar, root, dir_fd, dir_path: Path, arcdir: str, skip, packing) -> None:
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
                _walk(tar, root, sub, dir_path / name, arcname, skip, packing)
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
    # Checked BEFORE opening as well as after: opening a FIFO blocks, and with
    # no O_NONBLOCK there is nothing else to stop it.
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
