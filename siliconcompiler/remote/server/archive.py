'''
Opening somebody else's archive.

🔴 **Nothing here runs until the digest has been checked.** The order is
normative and it is the one sequencing detail in the contract that is a security
property rather than a preference: compare the client's asserted digest against
what storage reports, refuse before any extraction, and only then unpack. Doing
it the other way round is how an archive bomb gets opened -- the bytes would be
examined before anything had established they are the bytes that were declared.

Every refusal is ``archive-rejected`` with a ``violation`` naming which rule was
broken. One slug and six discriminators rather than six slugs: the registry is
frozen at v1 and a member's value can be added after the freeze where a slug
cannot.
'''

import tarfile

from pathlib import Path
from typing import Dict

__all__ = ["ArchiveRejected", "extract", "VIOLATIONS", "MAX_EXPANSION_RATIO"]


# The vocabulary, and it is closed. `member_count` and `expanded_bytes` are the
# two that name a published limit; the other four are structural and have no
# number to publish.
VIOLATIONS = ("member_count", "expanded_bytes", "ratio",
              "link_member", "device_member", "traversal")

# Expanded bytes per compressed byte. Deliberately generous: a build directory
# of text -- manifests, netlists, reports -- compresses an order of magnitude,
# and the ratio check is here for the pathological case (a gigabyte of zeros in
# a kilobyte) rather than to second-guess gzip. `max_archive_expanded_bytes` is
# the limit that binds normally; this one catches the archive that is small
# enough to sail past it and still fills the disk.
MAX_EXPANSION_RATIO = 1000

# Below this, the ratio is meaningless -- a 40-byte archive of one short file
# clears 1000:1 on its header alone.
_RATIO_FLOOR = 65536


class ArchiveRejected(Exception):
    '''One archive rule was broken, and this says which.'''

    def __init__(self, violation: str, detail: str):
        if violation not in VIOLATIONS:
            raise KeyError(f"{violation} is not an archive violation")
        self.violation = violation
        self.detail = detail
        super().__init__(detail)


def extract(archive: Path, dest: Path, limits: Dict[str, int]) -> int:
    '''Unpack ``archive`` into ``dest``, or refuse.

    Streamed member by member and checked before each write, so the budget binds
    on what has been written rather than on what the headers promised. A tar
    header is a claim by whoever built the archive; the bytes are the fact.

    Returns the expanded size in bytes.
    '''
    archive = Path(archive)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # resolve() first: every member's destination is checked against this, and a
    # comparison against an unresolved root is defeated by a symlink anywhere
    # above it.
    root = dest.resolve()

    compressed = archive.stat().st_size
    max_members = limits["max_archive_members"]
    max_expanded = limits["max_archive_expanded_bytes"]

    members = 0
    expanded = 0

    with tarfile.open(archive, "r:*") as tar:
        for member in tar:
            members += 1
            if members > max_members:
                raise ArchiveRejected(
                    "member_count",
                    f"the archive holds more than {max_members} members")

            name = member.name.strip()
            while name.startswith("./"):
                name = name[2:]

            if name in ("", "."):
                # The archive's own root. `tar.add(dir, arcname="")` writes one
                # of these, and it names the destination itself rather than
                # anything inside it -- so it is a directory to skip, and
                # anything else with no name is a member that cannot be placed.
                if member.isdir():
                    continue
                raise ArchiveRejected(
                    "traversal", "the archive holds an unnamed member")

            _check_path(name, root, dest)

            if member.issym() or member.islnk():
                # Refused rather than resolved. A link is the one member whose
                # meaning depends on where it is read: the same archive is safe
                # here and an arbitrary-file-read there, and a build directory
                # has no need of one.
                raise ArchiveRejected(
                    "link_member",
                    f"the archive holds a link: {name}")

            if member.ischr() or member.isblk() or member.isfifo() or member.isdev():
                raise ArchiveRejected(
                    "device_member",
                    f"the archive holds a device node: {name}")

            if member.isdir():
                (dest / name).mkdir(parents=True, exist_ok=True)
                continue

            if not member.isfile():
                # Anything left is a type this build directory has no use for.
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

    return expanded


def _check_path(name: str, root: Path, dest: Path) -> None:
    '''Refuse a member that would land outside the destination.

    Checked on the joined, resolved path rather than by looking for `..` in the
    name: the string test misses an absolute path, a drive letter and anything
    reached through a directory this archive created earlier.
    '''
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
    '''One regular file, with the archive's mode discarded.

    The uploaded mode is not honoured: the server owns this tree, it has to stay
    readable by the account the run executes as, and a 000 member in somebody's
    build directory would otherwise stop the run rather than the upload.
    '''
    target.parent.mkdir(parents=True, exist_ok=True)

    source = tar.extractfile(member)
    if source is None:                                          # pragma: no cover
        return

    with open(target, "wb") as f:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    # Executability is the one bit worth carrying: a collected script that
    # arrives non-executable fails at the point of use, a long way from here.
    if member.mode & 0o100:
        target.chmod(0o755)
    else:
        target.chmod(0o644)
