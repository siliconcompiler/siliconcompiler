'''
Reading a job's build directory without following it out.

A job writes its own build directory, so any path in it can be a symlink into
another job's data or `/etc`. Every read this server makes of a job's tree goes
through here: each component is opened relative to the one before and refused
when it is a link, so a link swapped in after a check is refused too. A FIFO
is refused, since opening one blocks forever. Only the root may be a link.

An archive keeps a link that ends inside the job as one relative link and
drops any other; nothing is copied in place of a link.
'''

import logging
import os
import stat
import tarfile

from pathlib import Path

from siliconcompiler.remote import links

__all__ = ["open_inside", "add_file", "add_tree"]


logger = logging.getLogger("sc-server")

_NONBLOCK = getattr(os, "O_NONBLOCK", 0)


def _parts(root, path):
    '''``path`` as components under ``root``, lexically; PermissionError if not under it.'''
    root = os.path.abspath(str(root))
    rel = os.path.relpath(os.path.abspath(str(path)), root)
    parts = rel.split(os.sep)
    if rel == os.curdir or os.path.isabs(rel) or os.pardir in parts:
        raise PermissionError(f"{path} is not under {root}")
    return root, parts


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


def _open_regular(name: str, dir_fd: int) -> int:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | _NONBLOCK, dir_fd=dir_fd)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise PermissionError(f"{name} is not a regular file")
    return fd


def _open_file(root, path) -> int:
    root, parts = _parts(root, path)
    parent = _walk_to(root, parts[:-1])
    try:
        return _open_regular(parts[-1], parent)
    finally:
        os.close(parent)


def open_inside(root, path):
    '''Open a regular file under ``root`` for reading, reached through no link; else OSError.'''
    return os.fdopen(_open_file(root, path), "rb")


def add_file(tar: tarfile.TarFile, root, path, arcname: str) -> None:
    '''Add one regular file to ``tar``; OSError where it is not one.'''
    with open_inside(root, path) as handle:
        _add_open(tar, handle, os.fstat(handle.fileno()), arcname)


def add_tree(tar: tarfile.TarFile, root, top, skip=()) -> None:
    '''Add everything under ``top`` to ``tar``, named relative to it.'''
    fd = _walk_to(*_parts(root, top))
    try:
        _walk(tar, fd, Path(top), "", frozenset(skip), root)
    finally:
        os.close(fd)


def _walk(tar, dir_fd, dir_path: Path, arcdir: str, skip, root) -> None:
    with os.scandir(dir_fd) as entries:
        names = sorted(entry.name for entry in entries)
    for name in names:
        if name in skip:
            continue
        arcname = f"{arcdir}/{name}" if arcdir else name
        info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)

        if stat.S_ISLNK(info.st_mode):
            _add_symlink(tar, root, dir_path, name, arcname, info.st_mtime)
        elif stat.S_ISDIR(info.st_mode):
            try:
                sub = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=dir_fd)
            except OSError:
                continue            # swapped for a link or removed underneath
            try:
                member = tar.tarinfo(arcname)
                member.type, member.mtime = tarfile.DIRTYPE, info.st_mtime
                member.mode = stat.S_IMODE(info.st_mode)
                tar.addfile(member)
                _walk(tar, sub, dir_path / name, arcname, skip, root)
            finally:
                os.close(sub)
        elif stat.S_ISREG(info.st_mode):
            try:
                fd = _open_regular(name, dir_fd)
            except OSError:
                continue
            with os.fdopen(fd, "rb") as handle:
                _add_open(tar, handle, os.fstat(handle.fileno()), arcname)
        # Devices, FIFOs and sockets are nobody's results.


def _add_symlink(tar, root, dir_path: Path, name: str, arcname: str, mtime) -> None:
    end = links.resolve(root, dir_path / name)
    if end is None:
        logger.info(f"left out of an archive: {arcname}, a link that does not end "
                    "inside the job")
        return
    member = tar.tarinfo(arcname)
    member.type, member.mtime = tarfile.SYMTYPE, mtime
    member.linkname = links.relative(end, os.path.realpath(str(dir_path)))
    tar.addfile(member)


def _add_open(tar, handle, info, arcname: str) -> None:
    member = tar.tarinfo(arcname)
    member.size, member.mtime = info.st_size, info.st_mtime
    member.mode = stat.S_IMODE(info.st_mode)
    tar.addfile(member, handle)
