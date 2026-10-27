'''
Opening somebody else's archive, held to the limits.

Every refusal is ``archive-rejected`` with a ``reason`` naming the rule. An
upload may carry links that resolve inside it; one resolving outside is
``link_member`` and never followed.
'''

import os
import shutil
import tarfile

from pathlib import Path
from typing import Dict, Optional

from siliconcompiler.remote.server.errors import ARCHIVE_VIOLATIONS

__all__ = ["ArchiveRejected", "extract"]


# Expanded bytes per compressed byte, deliberately generous: it catches only the
# pathological bomb; `max_archive_expanded_bytes` binds normally.
MAX_EXPANSION_RATIO = 1000

# Below this the ratio is meaningless: a tiny archive clears 1000:1 on its header.
_RATIO_FLOOR = 65536


class ArchiveRejected(Exception):
    '''One archive rule was broken, and this says which.'''

    def __init__(self, reason: str, detail: str):
        if reason not in ARCHIVE_VIOLATIONS:
            raise KeyError(f"{reason} is not an archive-rejected reason")
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


def extract(archive: Path, dest: Path, limits: Dict[str, int]) -> int:
    '''Unpack ``archive`` into ``dest``, or refuse; returns the expanded size.

    Streamed and checked before each write, so limits bind on bytes, not header
    claims. A refused archive may leave members behind: the caller removes ``dest``.
    '''
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    try:
        # Resolved: an unresolved root is defeated by a symlink anywhere above it.
        return _extract(Path(archive), dest, dest.resolve(), limits)
    except (FileExistsError, IsADirectoryError, NotADirectoryError):
        raise ArchiveRejected(
            "invalid_manifest",
            "the archive holds a member that lands on another member's file or "
            "directory") from None
    except (tarfile.TarError, EOFError):
        raise ArchiveRejected("invalid_manifest", "the archive cannot be read as a tar") \
            from None


def _extract(archive: Path, dest: Path, root: Path, limits) -> int:
    compressed = archive.stat().st_size
    max_members = limits["max_archive_members"]
    max_expanded = limits["max_archive_expanded_bytes"]

    members = 0
    expanded = 0
    # A name is written once, and a hard link names an earlier regular file.
    written = set()
    regular = set()
    symlinks = []

    with tarfile.open(archive, "r:*") as tar:
        for member in tar:
            members += 1
            if members > max_members:
                raise ArchiveRejected(
                    "member_count", f"the archive holds more than {max_members} members")

            name = _normalized(member.name)
            if name in ("", "."):
                # The archive's own root, as `tar.add(dir, arcname="")` writes.
                if member.isdir():
                    continue
                raise ArchiveRejected("traversal", "the archive holds an unnamed member")

            _check_name(name)
            _check_path(name, root, dest)
            _check_not_through_a_link(name, dest, directory=member.isdir(),
                                      written=written)

            if member.issym():
                if _link_target(name, member.linkname) is None:
                    raise ArchiveRejected(
                        "link_member",
                        f"the archive holds a link that resolves outside it: {name}")
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(member.linkname, dest / name)
                symlinks.append(name)
                written.add(name)
                continue

            if member.islnk():
                target = _normalized(member.linkname)
                if target not in regular:
                    raise ArchiveRejected(
                        "link_member",
                        f"{name} is a hard link to something that is not an earlier "
                        "file in the archive")
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                os.link(dest / target, dest / name)
                written.add(name)
                continue

            if member.isdir():
                (dest / name).mkdir(parents=True, exist_ok=True)
                continue

            if not member.isfile():
                raise ArchiveRejected(
                    "device_member", f"the archive holds a device or special file: {name}")

            expanded += member.size
            if expanded > max_expanded:
                raise ArchiveRejected(
                    "expanded_bytes", f"the archive expands past {max_expanded} bytes")
            if compressed >= _RATIO_FLOOR and expanded > compressed * MAX_EXPANSION_RATIO:
                raise ArchiveRejected(
                    "ratio", f"the archive expands more than {MAX_EXPANSION_RATIO}:1")

            _write(tar, member, dest / name)
            written.add(name)
            regular.add(name)

    # Once every member is in place: a link written early can be made to
    # leave the root by one written after it, so each is resolved again.
    for name in symlinks:
        real = Path(os.path.realpath(dest / name))
        if real != root and root not in real.parents:
            raise ArchiveRejected(
                "link_member", f"the archive holds a link that resolves outside it: {name}")

    return expanded


def _normalized(name: str) -> str:
    name = name.strip()
    while name.startswith("./"):
        name = name[2:]
    return name


def _check_name(name: str) -> None:
    '''No member name holds ``..``: a link's target may climb, a name may not.'''
    if os.pardir in name.split("/"):
        raise ArchiveRejected("traversal", f"the archive holds a member named with ..: {name}")


def _check_not_through_a_link(name: str, dest: Path, directory: bool, written) -> None:
    '''Nothing is written through a link: a member whose path, or any parent of
    it, is already a link, and a second non-directory member with a name
    already extracted.'''
    parts = name.split("/")
    for depth in range(1, len(parts) + 1):
        if os.path.islink(dest.joinpath(*parts[:depth])):
            raise ArchiveRejected("traversal",
                                  f"the archive would write through a link: {name}")
    if not directory and name in written:
        raise ArchiveRejected("traversal", f"the archive holds {name} twice")


def _link_target(name: str, target: str) -> Optional[str]:
    '''Where symlink ``name`` points as an archive name, or None if outside, lexically.'''
    if not target or os.path.isabs(target):
        return None
    joined = os.path.normpath(os.path.join(os.path.dirname(name), target))
    if joined in (os.curdir, os.pardir) or joined.startswith(os.pardir + os.sep):
        return None
    return joined


def _check_path(name: str, root: Path, dest: Path) -> None:
    '''Refuse a member whose joined, resolved path lands outside the destination.'''
    if os.path.isabs(name):
        raise ArchiveRejected("traversal", f"the archive holds an absolute path: {name}")

    resolved = (dest / name).resolve()
    if resolved != root and root not in resolved.parents:
        raise ArchiveRejected(
            "traversal", f"the archive would write outside the job directory: {name}")


def _write(tar: tarfile.TarFile, member: tarfile.TarInfo, target: Path) -> None:
    '''Write one regular file, discarding the archive's mode but the executable bit.

    A 000 member would otherwise stop the run rather than the upload.
    '''
    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "wb") as f:
        shutil.copyfileobj(tar.extractfile(member), f)

    target.chmod(0o755 if member.mode & 0o100 else 0o644)
