'''
Opening somebody else's archive, held to the limits.

Nothing here runs until the digest has been checked: the contract's one
ordering that is a security property, since examining undeclared bytes is how
an archive bomb gets opened.

Every refusal is ``archive-rejected`` with a ``reason`` naming the rule: a
member value can be added after the v1 freeze, a slug cannot. An upload may
carry links that resolve inside it (D65); one resolving outside is
``link_member`` and never followed.
'''

import os
import shutil
import tarfile

from pathlib import Path
from typing import Dict, Optional

__all__ = ["ArchiveRejected", "check_inside", "extract", "VIOLATIONS",
           "MAX_EXPANSION_RATIO"]


# The closed vocabulary: the registry's own list, not a copy that could drift.
from siliconcompiler.remote.server.errors import ARCHIVE_VIOLATIONS as VIOLATIONS  # noqa: E402

# Expanded bytes per compressed byte, deliberately generous: it catches only the
# pathological bomb; `max_archive_expanded_bytes` binds normally.
MAX_EXPANSION_RATIO = 1000

# Below this the ratio is meaningless: a tiny archive clears 1000:1 on its header.
_RATIO_FLOOR = 65536


class ArchiveRejected(Exception):
    '''One archive rule was broken, and this says which.'''

    def __init__(self, reason: str, detail: str):
        if reason not in VIOLATIONS:
            raise KeyError(f"{reason} is not an archive-rejected reason")
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


def extract(archive: Path, dest: Path, limits: Dict[str, int],
            allowed=None, prefix: str = "", select=None, tally=None) -> int:
    '''Unpack ``archive`` into ``dest``, or refuse; returns the expanded size.

    ``allowed`` vets each member name first (``unrequested_member``): a
    follow-up may carry only what was asked for. ``prefix`` goes before every
    name and hard-link target, placing one node's archive at ``<step>/<index>/``.
    ``select`` skips members by their unprefixed name. ``tally`` collects what
    the limits were spent on, wheels included, for `check_inside`. Streamed and
    checked before each write, so limits bind on bytes, not header claims.
    '''
    archive = Path(archive)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Resolved: an unresolved root is defeated by a symlink anywhere above it.
    root = dest.resolve()

    symlinks = []
    try:
        return _extract(archive, dest, root, limits, allowed, prefix, select, symlinks,
                        tally)
    except ArchiveRejected:
        # No link this archive planted outlives its refusal.
        for planted in symlinks:
            try:
                if (dest / planted).is_symlink():
                    (dest / planted).unlink()
            except OSError:
                pass
        raise


def _extract(archive: Path, dest: Path, root: Path, limits, allowed, prefix, select,
             symlinks, tally=None) -> int:
    compressed = archive.stat().st_size
    max_members = limits["max_archive_members"]
    max_expanded = limits["max_archive_expanded_bytes"]

    members = 0
    expanded = 0
    # A name is written once, and a hard link names an earlier regular file.
    written = set()
    regular = set()

    with tarfile.open(archive, "r:*") as tar:
        for member in tar:
            members += 1
            if members > max_members:
                raise ArchiveRejected(
                    "member_count",
                    f"the archive holds more than {max_members} members")

            name = _normalized(member.name)
            if select is not None and not select(name):
                continue
            if prefix:
                name = f"{prefix.rstrip('/')}/{name}" if name not in ("", ".") \
                    else prefix.rstrip("/")

            if name in ("", "."):
                # The archive's own root, as `tar.add(dir, arcname="")` writes.
                if member.isdir():
                    continue
                raise ArchiveRejected(
                    "traversal", "the archive holds an unnamed member")

            _check_name(name)
            _check_path(name, root, dest)
            _check_not_through_a_link(name, dest, directory=member.isdir(),
                                      written=written)

            if allowed is not None and not allowed(name):
                raise ArchiveRejected(
                    "unrequested_member",
                    "the archive holds a member that was not asked for")

            if member.issym():
                target = _link_target(name, member.linkname)
                if target is None:
                    raise ArchiveRejected(
                        "link_member",
                        f"the archive holds a link that resolves outside it: {name}")
                if allowed is not None and not allowed(target):
                    raise ArchiveRejected(
                        "unrequested_member",
                        f"{name} links to something that was not asked for")
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                os.symlink(member.linkname, dest / name)
                symlinks.append(name)
                if not _stays_inside(dest / name, root):
                    raise ArchiveRejected(
                        "link_member",
                        f"the archive holds a link that resolves outside it: {name}")
                written.add(name)
                continue

            if member.islnk():
                target = _normalized(member.linkname)
                if prefix:
                    target = f"{prefix.rstrip('/')}/{target}"
                if target not in regular:
                    raise ArchiveRejected(
                        "link_member",
                        f"{name} is a hard link to something that is not an earlier "
                        "file in the archive")
                if allowed is not None and not allowed(target):
                    raise ArchiveRejected(
                        "unrequested_member",
                        f"{name} links to something that was not asked for")
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                os.link(dest / target, dest / name)
                written.add(name)
                continue

            if member.ischr() or member.isblk() or member.isfifo() or member.isdev():
                raise ArchiveRejected(
                    "device_member",
                    f"the archive holds a device node: {name}")

            if member.isdir():
                (dest / name).mkdir(parents=True, exist_ok=True)
                continue

            if not member.isfile():
                raise ArchiveRejected(
                    "device_member",
                    f"the archive holds an unsupported member: {name}")

            expanded += member.size
            if expanded > max_expanded:
                raise ArchiveRejected(
                    "expanded_bytes",
                    f"the archive expands past {max_expanded} bytes")
            if compressed >= _RATIO_FLOOR and expanded > compressed * MAX_EXPANSION_RATIO:
                raise ArchiveRejected(
                    "ratio",
                    f"the archive expands more than {MAX_EXPANSION_RATIO}:1")

            _write(tar, member, dest / name)
            written.add(name)
            regular.add(name)
            if tally is not None and name.endswith(".whl"):
                tally.setdefault("wheels", []).append(name)

    # Once every member is in place: a link written early can be made to
    # leave the root by one written after it, so each is resolved again.
    for name in symlinks:
        if not _stays_inside(dest / name, root):
            raise ArchiveRejected(
                "link_member", f"the archive holds a link that resolves outside it: {name}")

    if tally is not None:
        tally.update(members=members, expanded=expanded, compressed=compressed)
    return expanded


def check_inside(tally, limits: Dict[str, int], name: str, members: int,
                 expanded: int) -> None:
    '''Hold a wheel's own members to the archive's limits, counted with the archive's.'''
    tally["members"] = tally.get("members", 0) + members
    tally["expanded"] = tally.get("expanded", 0) + expanded
    compressed = tally.get("compressed", 0)
    if tally["members"] > limits["max_archive_members"]:
        raise ArchiveRejected(
            "member_count", f"the archive holds more than {limits['max_archive_members']} "
                            f"members, counting those inside {name}")
    if tally["expanded"] > limits["max_archive_expanded_bytes"]:
        raise ArchiveRejected(
            "expanded_bytes", f"the archive expands past "
                              f"{limits['max_archive_expanded_bytes']} bytes, counting "
                              f"what is inside {name}")
    if compressed >= _RATIO_FLOOR and tally["expanded"] > compressed * MAX_EXPANSION_RATIO:
        raise ArchiveRejected(
            "ratio", f"the archive expands more than {MAX_EXPANSION_RATIO}:1, counting "
                     f"what is inside {name}")


def _normalized(name: str) -> str:
    name = name.strip()
    while name.startswith("./"):
        name = name[2:]
    return name


def _check_name(name: str) -> None:
    '''No member name holds ``..``: a link's target may climb, a name may not.'''
    parts = name.replace("\\", "/").split("/")
    if os.pardir in parts:
        raise ArchiveRejected("traversal", f"the archive holds a member named with ..: {name}")


def _check_not_through_a_link(name: str, dest: Path, directory: bool, written) -> None:
    '''Nothing is written through a link: a member whose path, or any
    parent of it, is already a link, and a second non-directory member with a
    name already extracted.'''
    parts = name.split("/")
    for depth in range(1, len(parts) + 1):
        if os.path.islink(dest.joinpath(*parts[:depth])):
            raise ArchiveRejected("traversal",
                                  f"the archive would write through a link: {name}")
    if not directory and name in written:
        raise ArchiveRejected("traversal", f"the archive holds {name} twice")


def _link_target(name: str, target: str) -> Optional[str]:
    '''Where symlink ``name`` points as an archive name, or None if outside, lexically.'''
    if not target or os.path.isabs(target) or target.startswith(("/", "\\")) \
            or ":" in target.split("/", 1)[0]:
        return None
    joined = os.path.normpath(os.path.join(os.path.dirname(name), target))
    if joined in (os.curdir, os.pardir) or joined.startswith(os.pardir + os.sep) \
            or os.path.isabs(joined):
        return None
    return joined.replace(os.sep, "/")


def _stays_inside(link: Path, root: Path) -> bool:
    real = Path(os.path.realpath(str(link)))
    return real == root or root in real.parents


def _check_path(name: str, root: Path, dest: Path) -> None:
    '''Refuse a member whose joined, resolved path lands outside the destination.'''
    candidate = Path(name)
    if candidate.is_absolute() or candidate.drive or candidate.root:
        raise ArchiveRejected("traversal", f"the archive holds an absolute path: {name}")

    try:
        resolved = (dest / candidate).resolve()
    except OSError:
        raise ArchiveRejected("traversal", f"unreadable member path: {name}") from None

    if resolved != root and root not in resolved.parents:
        raise ArchiveRejected(
            "traversal", f"the archive would write outside the job directory: {name}")


def _write(tar: tarfile.TarFile, member: tarfile.TarInfo, target: Path) -> None:
    '''Write one regular file, discarding the archive's mode but the executable bit.

    A 000 member would otherwise stop the run rather than the upload.
    '''
    target.parent.mkdir(parents=True, exist_ok=True)

    source = tar.extractfile(member)
    if source is None:                                          # pragma: no cover
        return

    with open(target, "wb") as f:
        shutil.copyfileobj(source, f)

    if member.mode & 0o100:
        target.chmod(0o755)
    else:
        target.chmod(0o644)
