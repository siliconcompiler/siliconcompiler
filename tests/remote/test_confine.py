import io
import os
import sys
import tarfile

import pytest

from siliconcompiler.remote.server import confine


# A job's build directory is written by the job, and a node's own code can leave
# a link anywhere in it. What is asserted is that no read through here follows
# one out -- and, where the platform allows, not even one that points inside,
# since a link swapped in after a check is exactly what a race would use.

pytestmark = pytest.mark.skipif(sys.platform == "win32",
                                reason="creating links needs privileges on Windows")


@pytest.fixture(params=[True, False], ids=["dir_fd", "by-path"])
def mode(request, monkeypatch):
    '''Both implementations: race-free, and the fallback without dir_fd.'''
    if request.param and not confine._SAFE:
        pytest.skip("no dir_fd here")
    monkeypatch.setattr(confine, "_SAFE", request.param)
    return request.param


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "job"
    (root / "node" / "outputs").mkdir(parents=True)
    (root / "node" / "outputs" / "gcd.vg").write_text("module gcd; endmodule\n")
    secret = tmp_path / "host-secret"
    secret.write_text("the host's own file\n")
    return root, secret


def test_a_regular_file_inside_is_read(tree, mode):
    root, _ = tree
    with confine.open_inside(root, root / "node" / "outputs" / "gcd.vg", "r") as f:
        assert f.read() == "module gcd; endmodule\n"
    assert confine.size_inside(root, root / "node" / "outputs" / "gcd.vg") == 22


def test_a_link_out_is_refused(tree, mode):
    root, secret = tree
    (root / "node" / "stolen").symlink_to(secret)

    with pytest.raises(OSError):
        confine.open_inside(root, root / "node" / "stolen")
    assert confine.size_inside(root, root / "node" / "stolen") == 0


def test_a_linked_directory_on_the_way_is_refused(tree, mode, tmp_path):
    root, secret = tree
    (root / "node" / "escape").symlink_to(tmp_path)

    with pytest.raises(OSError):
        confine.open_inside(root, root / "node" / "escape" / "host-secret")


def test_a_path_out_of_the_root_is_refused(tree, mode):
    root, _ = tree
    with pytest.raises(OSError):
        confine.open_inside(root, root / ".." / "host-secret")


def test_even_a_link_inside_is_refused_where_there_is_dir_fd(tree):
    '''🔴 Race-free means no link at all: one that points inside now can point
    out a moment later.'''
    if not confine._SAFE:
        pytest.skip("no dir_fd here")
    root, _ = tree
    (root / "node" / "alias.vg").symlink_to(root / "node" / "outputs" / "gcd.vg")

    with pytest.raises(OSError):
        confine.open_inside(root, root / "node" / "alias.vg")


def test_a_fifo_is_refused_rather_than_blocking(tree, mode):
    '''Opening one blocks the reader forever -- the stream, the request.'''
    root, _ = tree
    os.mkfifo(root / "node" / "sc_node_0.log")

    with pytest.raises(OSError):
        confine.open_inside(root, root / "node" / "sc_node_0.log")


def test_the_root_itself_may_be_reached_through_a_link(tree, tmp_path, mode):
    '''It is the server's own directory; a datadir mounted through a link is
    ordinary.'''
    root, _ = tree
    alias = tmp_path / "alias"
    alias.symlink_to(root)

    with confine.open_inside(alias, alias / "node" / "outputs" / "gcd.vg", "r") as f:
        assert f.read().startswith("module")


def archived(root, top, base, **kwargs):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        confine.add_tree(tar, root, top, base, **kwargs)
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer)
    return {member.name: member for member in tar.getmembers()}, tar


def test_a_tree_stores_a_link_inside_it_as_a_link(tree, mode):
    root, _ = tree
    (root / "node" / "outputs" / "alias.vg").symlink_to("gcd.vg")
    (root / "node" / "outputs" / "up.vg").symlink_to("../outputs/gcd.vg")

    members, _ = archived(root, root / "node", root / "node")

    assert members["outputs/alias.vg"].issym()
    assert members["outputs/alias.vg"].linkname == "gcd.vg"
    assert members["outputs/up.vg"].issym()
    assert members["outputs/gcd.vg"].isfile()


@pytest.mark.parametrize("target", ["secret", "../../elsewhere", "inside-but-absolute"])
def test_a_link_out_of_the_tree_is_left_out(tree, mode, target):
    '''🔴 Its target names this server's paths -- where a private PDK is
    mounted, another user's tree -- and lands outside a naive extractor's
    directory. Absolute, even pointing inside: the path itself is the leak.'''
    root, secret = tree
    linked = {"secret": str(secret), "../../elsewhere": "../../elsewhere",
              "inside-but-absolute": str(root / "node" / "outputs" / "gcd.vg")}[target]
    (root / "node" / "outputs" / "stolen").symlink_to(linked)

    members, _ = archived(root, root / "node", root / "node")

    assert "outputs/stolen" not in members
    assert members["outputs/gcd.vg"].isfile()


def test_a_link_climbing_out_of_the_archived_tree_is_left_out_though_in_the_root(tree, mode):
    '''Inside the job, outside what is being archived: the archive is what
    travels, so it is the archive's own tree that bounds a link.'''
    root, _ = tree
    (root / "node" / "outputs" / "sibling").symlink_to("../../other/file")

    members, _ = archived(root, root / "node" / "outputs", root / "node")

    assert "outputs/sibling" not in members


def test_a_tree_follows_a_link_inside_only_when_asked(tree, mode):
    root, secret = tree
    inputs = root / "node" / "inputs"
    inputs.mkdir()
    (inputs / "gcd.vg").symlink_to(root / "node" / "outputs" / "gcd.vg")
    (inputs / "stolen").symlink_to(secret)

    members, tar = archived(root, inputs, root / "node", follow_inside=True)

    assert members["inputs/gcd.vg"].isfile()
    assert tar.extractfile(members["inputs/gcd.vg"]).read() == b"module gcd; endmodule\n"
    assert "inputs/stolen" not in members


def test_a_tree_leaves_out_what_it_is_told_to_wherever_it_is(tree, mode):
    root, _ = tree
    (root / "node" / "inputs").mkdir()
    (root / "node" / "inputs" / "x").write_text("x")
    (root / "node" / "outputs" / "inputs").mkdir()

    members, _ = archived(root, root / "node", root / "node", skip=("inputs",))

    assert not any("inputs" in name.split("/") for name in members)
    assert "." not in members                    # no entry for the top itself
