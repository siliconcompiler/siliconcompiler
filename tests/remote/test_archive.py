import io
import os
import tarfile

import pytest

from pathlib import Path

from siliconcompiler.remote.server.archive import (
    ArchiveRejected, MAX_EXPANSION_RATIO, VIOLATIONS, extract)


# The one sequencing rule in the contract that is a security property rather
# than a preference is that nothing here runs until the digest has matched. What
# these tests cover is the other half: once it does, an archive is still
# somebody else's data, and every way it can be hostile has a named refusal.


LIMITS = {
    "max_archive_members": 100,
    "max_archive_expanded_bytes": 1 << 20,
}


def build(path, members):
    '''An archive built member by member, including members tarfile.add cannot
    make -- a device node, a link out of the tree, a path with .. in it.'''
    with tarfile.open(path, "w:gz") as tar:
        for info, body in members:
            tar.addfile(info, io.BytesIO(body) if body is not None else None)


def regular(name, body=b"x"):
    info = tarfile.TarInfo(name)
    info.size = len(body)
    return info, body


def test_a_plain_archive_lands(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("manifest.json", b"{}"),
                    regular("step/0/outputs/thing.v", b"module m; endmodule\n")])

    expanded = extract(archive, tmp_path / "dest", LIMITS)

    assert (tmp_path / "dest" / "manifest.json").read_bytes() == b"{}"
    assert (tmp_path / "dest" / "step/0/outputs/thing.v").is_file()
    assert expanded == 2 + len(b"module m; endmodule\n")


def test_the_archives_own_root_is_not_a_traversal(tmp_path):
    '''`tar.add(dir, arcname="")` writes a directory member with no name, and it
    names the destination rather than anything inside it. Refusing it would
    refuse every archive the client builds.'''
    archive = tmp_path / "a.tar.gz"
    root = tarfile.TarInfo("")
    root.type = tarfile.DIRTYPE
    build(archive, [(root, None), regular("manifest.json", b"{}")])

    extract(archive, tmp_path / "dest", LIMITS)

    assert (tmp_path / "dest" / "manifest.json").is_file()


def test_every_violation_is_in_the_vocabulary():
    '''One slug with six discriminators rather than six slugs: the registry is
    frozen at v1, and a member's value can be added after the freeze where a
    slug cannot.'''
    assert set(VIOLATIONS) == {"member_count", "expanded_bytes", "ratio",
                               "link_member", "device_member", "traversal"}


def test_too_many_members(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular(f"f{n}", b"") for n in range(LIMITS["max_archive_members"] + 1)])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.violation == "member_count"


def test_too_many_expanded_bytes(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("big", b"\0" * (LIMITS["max_archive_expanded_bytes"] + 1))])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.violation == "expanded_bytes"


def test_an_expansion_bomb(tmp_path):
    '''Small enough to clear the byte ceiling and still fill a disk. The ratio
    is the check that catches the archive the published limit does not.'''
    archive = tmp_path / "a.tar.gz"
    wide = dict(LIMITS, max_archive_expanded_bytes=1 << 40)
    build(archive, [regular("zeros", b"\0" * (128 << 20))])

    assert archive.stat().st_size * MAX_EXPANSION_RATIO < (128 << 20)

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", wide)

    assert rejected.value.violation == "ratio"


def test_a_symlink_is_refused_not_resolved(tmp_path):
    '''The one member whose meaning depends on where it is read: the same
    archive is safe here and an arbitrary-file-read there.'''
    archive = tmp_path / "a.tar.gz"
    link = tarfile.TarInfo("shadow")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    build(archive, [(link, None)])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.violation == "link_member"
    assert not (tmp_path / "dest" / "shadow").exists()


def test_a_hard_link_is_refused_too(tmp_path):
    archive = tmp_path / "a.tar.gz"
    link = tarfile.TarInfo("shadow")
    link.type = tarfile.LNKTYPE
    link.linkname = "manifest.json"
    build(archive, [regular("manifest.json", b"{}"), (link, None)])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.violation == "link_member"


@pytest.mark.parametrize("kind", [tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE])
def test_a_device_node(tmp_path, kind):
    archive = tmp_path / "a.tar.gz"
    node = tarfile.TarInfo("dev")
    node.type = kind
    build(archive, [(node, None)])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.violation == "device_member"


@pytest.mark.parametrize("name", ["../escape", "a/../../escape", "/etc/passwd"])
def test_traversal(tmp_path, name):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular(name, b"owned")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.violation == "traversal"
    assert not (tmp_path / "escape").exists()


def test_traversal_through_a_directory_the_archive_made(tmp_path):
    '''The string test for `..` is not the check: this member's name has none,
    and it still lands outside. Resolving the joined path is what catches it.'''
    outside = tmp_path / "outside"
    outside.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "hop").symlink_to(outside)

    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("hop/landed", b"owned")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, dest, LIMITS)

    assert rejected.value.violation == "traversal"
    assert not (outside / "landed").exists()


def test_the_uploaded_mode_is_not_honoured(tmp_path):
    '''The server owns this tree and the run has to be able to read it. A 000
    member in somebody's build directory would stop the run, not the upload.'''
    archive = tmp_path / "a.tar.gz"
    info, body = regular("locked", b"x")
    info.mode = 0o000
    script, script_body = regular("run.sh", b"#!/bin/sh\n")
    script.mode = 0o755
    build(archive, [(info, body), (script, script_body)])

    extract(archive, tmp_path / "dest", LIMITS)

    assert os.access(tmp_path / "dest" / "locked", os.R_OK)
    # Executability is the one bit worth carrying: a collected script that
    # arrives non-executable fails at the point of use, a long way from here.
    assert os.access(tmp_path / "dest" / "run.sh", os.X_OK)


def test_an_unknown_violation_cannot_be_raised():
    with pytest.raises(KeyError):
        ArchiveRejected("something_new", "detail")


def test_nothing_is_left_behind_by_a_refusal(tmp_path):
    '''The caller removes the directory, but what matters here is that the
    refusal happens before the offending member is written.'''
    archive = tmp_path / "a.tar.gz"
    link = tarfile.TarInfo("shadow")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    build(archive, [regular("first", b"ok"), (link, None)])

    with pytest.raises(ArchiveRejected):
        extract(archive, tmp_path / "dest", LIMITS)

    assert Path(tmp_path / "dest" / "first").is_file()
    assert not Path(tmp_path / "dest" / "shadow").exists()
