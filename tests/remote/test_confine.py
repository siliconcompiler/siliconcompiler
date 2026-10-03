import io
import os
import sys
import tarfile

import pytest

from siliconcompiler.remote.server.outputs import confine


# A node's own code can leave a link anywhere in its build directory: no read
# through here follows one out, and with dir_fd not even one pointing inside,
# since a link swapped in after a check is what a race would use.

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


@pytest.mark.parametrize("plant,path", [
    (lambda root, secret: (root / "node" / "stolen").symlink_to(secret), "node/stolen"),
    (lambda root, secret: (root / "node" / "escape").symlink_to(secret.parent),
     "node/escape/host-secret"),
    (lambda root, secret: None, "../host-secret"),
    # A FIFO would block the reader forever -- the stream, the request.
    (lambda root, secret: os.mkfifo(root / "node" / "sc_node_0.log"), "node/sc_node_0.log"),
], ids=["link-out", "linked-directory", "dotdot", "fifo"])
def test_a_read_that_leaves_the_root_or_would_block_is_refused(tree, mode, plant, path):
    root, secret = tree
    plant(root, secret)

    with pytest.raises(OSError):
        confine.open_inside(root, root / path)
    assert confine.size_inside(root, root / path) == 0


def test_even_a_link_inside_is_refused_where_there_is_dir_fd(tree):
    '''Race-free means no link at all: one pointing inside now can point out later.'''
    if not confine._SAFE:
        pytest.skip("no dir_fd here")
    root, _ = tree
    (root / "node" / "alias.vg").symlink_to(root / "node" / "outputs" / "gcd.vg")

    with pytest.raises(OSError):
        confine.open_inside(root, root / "node" / "alias.vg")


def test_the_root_itself_may_be_reached_through_a_link(tree, tmp_path, mode):
    '''It is the server's own directory; a datadir mounted through a link is ordinary.'''
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
    return {member.name: member for member in tarfile.open(fileobj=buffer).getmembers()}


def test_a_link_inside_the_tree_is_stored_as_a_relative_link(tree, mode):
    '''An absolute one too, so the archive names no path of this server's.'''
    root, _ = tree
    outputs = root / "node" / "outputs"
    (outputs / "alias.vg").symlink_to("gcd.vg")
    (outputs / "up.vg").symlink_to("../outputs/gcd.vg")
    (outputs / "absolute").symlink_to(outputs / "gcd.vg")

    members = archived(root, root / "node", root / "node")

    assert members["outputs/gcd.vg"].isfile()
    assert members["outputs/up.vg"].issym()
    for name in ("alias.vg", "absolute"):
        assert members[f"outputs/{name}"].issym()
        assert members[f"outputs/{name}"].linkname == "gcd.vg"


@pytest.mark.parametrize("target,top", [
    ("secret", "node"), ("../../elsewhere", "node"),
    # Inside the job, outside the archived tree: the archive's own tree bounds it.
    ("../../other/file", "node/outputs"),
])
def test_a_link_out_of_the_archived_tree_is_left_out(tree, mode, target, top):
    '''Its target names this server's paths -- a private PDK's mount,
    another user's tree. Never followed, never stored.'''
    root, secret = tree
    (root / "node" / "outputs" / "stolen").symlink_to(
        str(secret) if target == "secret" else target)

    members = archived(root, root / top, root / "node")

    assert "outputs/stolen" not in members
    assert members["outputs/gcd.vg"].isfile()


def test_a_chain_is_one_link_to_where_it_ends_and_nothing_is_copied(tree, mode):
    '''`outputs/x` -> `inputs/x` -> upstream `outputs/x` becomes one link to
    the upstream file; a link out of the job is dropped.'''
    root, secret = tree
    upstream = root / "up" / "outputs"
    upstream.mkdir(parents=True)
    (upstream / "gcd.vg").write_text("module gcd; endmodule\n")
    inputs = root / "node" / "inputs"
    inputs.mkdir()
    (inputs / "gcd.vg").symlink_to(upstream / "gcd.vg")
    (inputs / "stolen").symlink_to(secret)
    (root / "node" / "outputs" / "passed.vg").symlink_to("../inputs/gcd.vg")

    members = archived(root, root / "node", root / "node", job_tree=root)

    assert members["outputs/passed.vg"].issym()
    assert members["outputs/passed.vg"].linkname == "../../up/outputs/gcd.vg"
    assert members["inputs/gcd.vg"].linkname == "../../up/outputs/gcd.vg"
    assert "inputs/stolen" not in members


def test_a_tree_leaves_out_what_it_is_told_to_wherever_it_is(tree, mode):
    root, _ = tree
    (root / "node" / "inputs").mkdir()
    (root / "node" / "inputs" / "x").write_text("x")
    (root / "node" / "outputs" / "inputs").mkdir()

    members = archived(root, root / "node", root / "node", skip=("inputs",))

    assert not any("inputs" in name.split("/") for name in members)
    assert "." not in members                    # no entry for the top itself
