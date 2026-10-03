import io
import os
import tarfile

import pytest

from siliconcompiler.remote.server.staging.archive import (
    ArchiveRejected, MAX_EXPANSION_RATIO, VIOLATIONS, extract)


# Nothing here runs until the digest matched; after that an archive is still
# somebody else's data, and every way it can be hostile has a named refusal.


LIMITS = {
    "max_archive_members": 100,
    "max_archive_expanded_bytes": 1 << 20,
}


def build(path, members):
    '''Member by member, including what tarfile.add cannot make.'''
    with tarfile.open(path, "w:gz") as tar:
        for info, body in members:
            tar.addfile(info, io.BytesIO(body) if body is not None else None)
    return path


def regular(name, body=b"x"):
    info = tarfile.TarInfo(name)
    info.size = len(body)
    return info, body


def special(name, kind, target=""):
    info = tarfile.TarInfo(name)
    info.type, info.linkname = kind, target
    return info, None


def symlink(name, target):
    return special(name, tarfile.SYMTYPE, target)


def refused(tmp_path, members, dest=None, limits=LIMITS, **kwargs):
    '''The violation extracting ``members`` is refused for.'''
    archive = build(tmp_path / "a.tar.gz", members)
    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, dest or tmp_path / "dest", limits, **kwargs)
    return rejected.value.reason


def test_a_plain_archive_lands(tmp_path):
    '''`tar.add(dir, arcname="")` writes a nameless root directory member: it
    names the destination and is not a traversal.'''
    archive = build(tmp_path / "a.tar.gz", [
        special("", tarfile.DIRTYPE), regular("manifest.json", b"{}"),
        regular("step/0/outputs/thing.v", b"module m; endmodule\n")])

    expanded = extract(archive, tmp_path / "dest", LIMITS)

    assert (tmp_path / "dest" / "manifest.json").read_bytes() == b"{}"
    assert (tmp_path / "dest" / "step/0/outputs/thing.v").is_file()
    assert expanded == 2 + len(b"module m; endmodule\n")


def test_every_violation_is_in_the_vocabulary():
    '''One slug, many discriminators: a value can be added after the v1 freeze
    and a slug cannot (D302, D124, D129, D283, contract D40, D165).'''
    assert set(VIOLATIONS) == {"member_count", "expanded_bytes", "ratio",
                               "link_member", "device_member", "traversal",
                               "missing_manifest", "invalid_manifest", "credential",
                               "unrequested_member", "missing_member", "python_package",
                               "extension",              # listed, never raised here
                               "breakpoint", "interactive_task"}


def test_an_unknown_violation_cannot_be_raised():
    with pytest.raises(KeyError):
        ArchiveRejected("something_new", "detail")


@pytest.mark.parametrize("members,reason,after", [
    ([regular(f"f{n}", b"") for n in range(LIMITS["max_archive_members"] + 1)],
     "member_count", {}),
    ([regular("big", b"\0" * (LIMITS["max_archive_expanded_bytes"] + 1))],
     "expanded_bytes", {}),
    # A symlink is refused, not resolved: safe here, an arbitrary-file-read there.
    ([symlink("shadow", "/etc/passwd")], "link_member", {"shadow": None}),
    ([symlink("steptwo/0/outputs/stolen", "../../../../etc/passwd")], "link_member",
     {"steptwo/0/outputs/stolen": None}),
    # Each resolves inside as it is written; together they climb out.
    ([special("d", tarfile.DIRTYPE), symlink("a/far", "x/../../out"), symlink("a/x", "../d")],
     "link_member", {"a/far": None}),
    # A hard link to anything but an earlier regular file.
    ([special("shadow", tarfile.LNKTYPE, "later.json"), regular("later.json", b"{}")],
     "link_member", {}),
    ([special("dev", tarfile.CHRTYPE)], "device_member", {}),
    ([special("dev", tarfile.BLKTYPE)], "device_member", {}),
    ([special("dev", tarfile.FIFOTYPE)], "device_member", {}),
    ([regular("../escape", b"owned")], "traversal", {"../escape": None}),
    ([regular("a/../../escape", b"owned")], "traversal", {"../escape": None}),
    ([regular("/etc/passwd", b"owned")], "traversal", {}),
    # A link's target may climb; a member's name may not.
    ([regular("stepone/../manifest.json", b"{}")], "traversal", {}),
    ([regular("manifest.json", b"{}"), regular("manifest.json", b"owned")], "traversal",
     {"manifest.json": b"{}"}),
    # A symlink planted first would let a later member overwrite the manifest.
    ([special("stepone", tarfile.DIRTYPE), regular("stepone/manifest.json", b"{}"),
      symlink("sc_collected_files", "stepone"),
      regular("sc_collected_files/manifest.json", b"owned")],
     "traversal", {"stepone/manifest.json": b"{}"}),
], ids=["members", "bytes", "absolute-link", "link-out", "link-made-to-leave",
        "hard-link-later", "chr", "blk", "fifo", "dotdot", "inner-dotdot", "absolute",
        "dotdot-inside", "duplicate", "through-earlier-link"])
def test_a_hostile_archive_is_refused_by_name(tmp_path, members, reason, after):
    assert refused(tmp_path, members) == reason

    for name, body in after.items():
        path = tmp_path / "dest" / name
        if body is None:
            assert not os.path.lexists(path), name
        else:
            assert path.read_bytes() == body


def test_an_expansion_bomb(tmp_path):
    '''Under the byte ceiling and still able to fill a disk: the ratio catches it.'''
    archive = build(tmp_path / "a.tar.gz", [regular("zeros", b"\0" * (128 << 20))])
    assert archive.stat().st_size * MAX_EXPANSION_RATIO < (128 << 20)

    with pytest.raises(ArchiveRejected) as rejected:
        extract(archive, tmp_path / "dest", dict(LIMITS, max_archive_expanded_bytes=1 << 40))
    assert rejected.value.reason == "ratio"


def test_traversal_through_a_directory_the_archive_made(tmp_path):
    '''No `..` in the name, and it still lands outside: the joined path is resolved.'''
    outside = tmp_path / "outside"
    outside.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "hop").symlink_to(outside)

    assert refused(tmp_path, [regular("hop/landed", b"owned")], dest=dest) == "traversal"
    assert not (outside / "landed").exists()


def test_a_hard_link_to_an_earlier_file_is_extracted_as_one(tmp_path):
    '''The same file under a second name (contract.md's Member types row).'''
    archive = build(tmp_path / "a.tar.gz", [
        regular("manifest.json", b"{}"), special("shadow", tarfile.LNKTYPE, "manifest.json")])

    extract(archive, tmp_path / "dest", LIMITS)

    dest = tmp_path / "dest"
    assert (dest / "shadow").read_bytes() == b"{}"
    assert os.path.samefile(dest / "shadow", dest / "manifest.json")


def test_the_uploaded_mode_is_not_honoured_but_executability_is(tmp_path):
    '''A 000 member would stop the run, not the upload; a collected script that
    arrives non-executable fails far from here.'''
    info, body = regular("locked", b"x")
    info.mode = 0o000
    script, script_body = regular("run.sh", b"#!/bin/sh\n")
    script.mode = 0o755
    archive = build(tmp_path / "a.tar.gz", [(info, body), (script, script_body)])

    extract(archive, tmp_path / "dest", LIMITS)

    assert os.access(tmp_path / "dest" / "locked", os.R_OK)
    assert os.access(tmp_path / "dest" / "run.sh", os.X_OK)


def test_nothing_is_left_behind_by_a_refusal(tmp_path):
    '''The refusal comes before the offending member is written.'''
    assert refused(tmp_path, [regular("first", b"ok"), symlink("shadow", "/etc/passwd")]) \
        == "link_member"

    assert (tmp_path / "dest" / "first").is_file()
    assert not (tmp_path / "dest" / "shadow").exists()


def test_an_inward_symlink_is_extracted_as_a_link(tmp_path):
    '''A pass-through: one node's output linked to another's, staying in the archive.'''
    archive = build(tmp_path / "a.tar.gz", [
        regular("stepone/0/outputs/gcd.vg", b"module gcd; endmodule\n"),
        symlink("steptwo/0/outputs/gcd.vg", "../../../stepone/0/outputs/gcd.vg")])

    extract(archive, tmp_path / "dest", LIMITS)

    link = tmp_path / "dest" / "steptwo/0/outputs/gcd.vg"
    assert link.is_symlink()
    assert link.read_bytes() == b"module gcd; endmodule\n"


def test_a_follow_up_link_to_what_was_not_asked_for_is_refused(tmp_path):
    '''A follow-up's link is held to what that archive may carry, target included.'''
    assert refused(tmp_path, [symlink("sc_collected_files/asked/x", "../../manifest.json")],
                   allowed=lambda name: name.startswith("sc_collected_files")) \
        == "unrequested_member"


def test_a_link_counts_as_a_member_and_not_toward_the_size(tmp_path):
    members = [regular("stepone/0/outputs/x", b"12345"),
               symlink("steptwo/0/outputs/x", "../../../stepone/0/outputs/x")]

    assert extract(build(tmp_path / "ok.tar.gz", members), tmp_path / "ok", LIMITS) == 5
    assert refused(tmp_path, members, limits=dict(LIMITS, max_archive_members=1)) \
        == "member_count"
