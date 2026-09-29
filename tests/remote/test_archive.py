import io
import os
import tarfile

import pytest

from pathlib import Path

from siliconcompiler.remote.server.staging.archive import (
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
                               "link_member", "device_member", "traversal",
                               "manifest_missing", "manifest_invalid",
                               # D124: a follow-up carrying what was not asked for.
                               "unrequested_member",
                               # D129: a value the flow reads, left out.
                               "missing_member",
                               # D283: an uploaded wheel that is impure or overlaps.
                               "python_package",
                               # contract D40: an extension off an allowlist this
                               # profile does not have -- listed, never raised.
                               "extension",
                               # D165: a job that would wait for a person.
                               "breakpoint", "interactive_task"}


def test_too_many_members(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular(f"f{n}", b"") for n in range(LIMITS["max_archive_members"] + 1)])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "member_count"


def test_too_many_expanded_bytes(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("big", b"\0" * (LIMITS["max_archive_expanded_bytes"] + 1))])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "expanded_bytes"


def test_an_expansion_bomb(tmp_path):
    '''Small enough to clear the byte ceiling and still fill a disk. The ratio
    is the check that catches the archive the published limit does not.'''
    archive = tmp_path / "a.tar.gz"
    wide = dict(LIMITS, max_archive_expanded_bytes=1 << 40)
    build(archive, [regular("zeros", b"\0" * (128 << 20))])

    assert archive.stat().st_size * MAX_EXPANSION_RATIO < (128 << 20)

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", wide)

    assert rejected.value.reason == "ratio"


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

    assert rejected.value.reason == "link_member"
    assert not (tmp_path / "dest" / "shadow").exists()


def test_a_hard_link_to_an_earlier_file_is_extracted_as_one(tmp_path):
    '''A tar hard link to an earlier regular-file member is the same file
    under a second name (contract.md's Member types row).'''
    archive = tmp_path / "a.tar.gz"
    link = tarfile.TarInfo("shadow")
    link.type = tarfile.LNKTYPE
    link.linkname = "manifest.json"
    build(archive, [regular("manifest.json", b"{}"), (link, None)])

    extract(archive, tmp_path / "dest", LIMITS)

    dest = tmp_path / "dest"
    assert (dest / "shadow").read_bytes() == b"{}"
    assert os.path.samefile(dest / "shadow", dest / "manifest.json")


def test_a_hard_link_to_anything_but_an_earlier_file_is_refused(tmp_path):
    archive = tmp_path / "a.tar.gz"
    link = tarfile.TarInfo("shadow")
    link.type = tarfile.LNKTYPE
    link.linkname = "later.json"
    build(archive, [(link, None), regular("later.json", b"{}")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "link_member"


@pytest.mark.parametrize("kind", [tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE])
def test_a_device_node(tmp_path, kind):
    archive = tmp_path / "a.tar.gz"
    node = tarfile.TarInfo("dev")
    node.type = kind
    build(archive, [(node, None)])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "device_member"


@pytest.mark.parametrize("name", ["../escape", "a/../../escape", "/etc/passwd"])
def test_traversal(tmp_path, name):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular(name, b"owned")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "traversal"
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

    assert rejected.value.reason == "traversal"
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


###########################
# Links that resolve inside the archive (contract.md's Links row; D65)
###########################

def symlink(name, target):
    info = tarfile.TarInfo(name)
    info.type, info.linkname = tarfile.SYMTYPE, target
    return info, None


def test_an_inward_symlink_is_extracted_as_a_link(tmp_path):
    '''A pass-through: one node's output linked to another's, climbing out of
    its own directory and staying in the archive.'''
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("stepone/0/outputs/gcd.vg", b"module gcd; endmodule\n"),
                    symlink("steptwo/0/outputs/gcd.vg", "../../../stepone/0/outputs/gcd.vg")])

    extract(archive, tmp_path / "dest", LIMITS)

    link = tmp_path / "dest" / "steptwo/0/outputs/gcd.vg"
    assert link.is_symlink()
    assert link.read_bytes() == b"module gcd; endmodule\n"


def test_a_link_out_of_the_archive_is_refused(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [symlink("steptwo/0/outputs/stolen", "../../../../etc/passwd")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "link_member"
    assert not (tmp_path / "dest" / "steptwo/0/outputs/stolen").exists()


def test_a_link_made_to_leave_by_a_later_one_is_refused(tmp_path):
    '''Each link resolves inside as it is written; together they climb out.
    Every link is resolved again once all are in place.'''
    archive = tmp_path / "a.tar.gz"
    directory = tarfile.TarInfo("d")
    directory.type = tarfile.DIRTYPE
    build(archive, [(directory, None),
                    symlink("a/far", "x/../../out"),
                    symlink("a/x", "../d")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "link_member"
    assert not (tmp_path / "dest" / "a" / "far").is_symlink()


def test_a_member_named_with_dotdot_is_traversal(tmp_path):
    '''A link's target may climb; a member's name may not.'''
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("stepone/../manifest.json", b"{}")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "traversal"


def test_nothing_is_written_through_an_earlier_link(tmp_path):
    '''🔴 A symlink planted first would let a later member overwrite the
    manifest, or a file outside the collection.'''
    archive = tmp_path / "a.tar.gz"
    directory = tarfile.TarInfo("stepone")
    directory.type = tarfile.DIRTYPE
    build(archive, [(directory, None), regular("stepone/manifest.json", b"{}"),
                    symlink("sc_collected_files", "stepone"),
                    regular("sc_collected_files/manifest.json", b"owned")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "traversal"
    assert (tmp_path / "dest" / "stepone" / "manifest.json").read_bytes() == b"{}"


def test_a_second_member_of_one_name_is_traversal(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("manifest.json", b"{}"), regular("manifest.json", b"owned")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS)

    assert rejected.value.reason == "traversal"
    assert (tmp_path / "dest" / "manifest.json").read_bytes() == b"{}"


def test_a_follow_up_link_to_what_was_not_asked_for_is_refused(tmp_path):
    '''A link in a follow-up archive is held to what that archive may carry,
    its target included.'''
    archive = tmp_path / "a.tar.gz"
    build(archive, [symlink("sc_collected_files/asked/x", "../../manifest.json")])

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", LIMITS,
                allowed=lambda name: name.startswith("sc_collected_files"))

    assert rejected.value.reason == "unrequested_member"


def test_a_link_counts_as_a_member_and_not_toward_the_size(tmp_path):
    archive = tmp_path / "a.tar.gz"
    build(archive, [regular("stepone/0/outputs/x", b"12345"),
                    symlink("steptwo/0/outputs/x", "../../../stepone/0/outputs/x")])

    assert extract(archive, tmp_path / "dest", LIMITS) == 5
    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "again", dict(LIMITS, max_archive_members=1))
    assert rejected.value.reason == "member_count"
