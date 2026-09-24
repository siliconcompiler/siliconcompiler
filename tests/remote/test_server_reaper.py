'''Taking back the disk.

🔴 Nothing here was reclaiming anything, and a rig fills its disk fast:
measured at 28 GB on one afternoon of rebuilds, 25 of it container bundles
nothing could run any more. These tests are mostly about what the reaper must
NOT take.
'''

import pytest

from conftest import call
from test_server_jobs import FakeDispatcher, stage, submit
from test_server_artifacts import ran


pytest.importorskip("flask", reason="the server extra is not installed")


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def me(server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


def sweep(server):
    from siliconcompiler.remote.server import reaper

    return reaper.sweep(server.config["SC_STORE"], server.config["SC_STORAGE"],
                        server.config["SC_CONFIG"], server.config["SC_DATADIR"])


def artifact_rows(server, job_id):
    return server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ?", (job_id,))


###########################
# Expired artifacts
###########################

def test_an_artifact_past_its_retention_loses_its_bytes_and_keeps_its_row(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 The row stays. *Where did my results go* has to stay answerable when
    the bytes are gone -- that is the whole reason the listing exists.

    🔴 And `deleted_at` stays NULL, which is the opposite of what it looks
    like. That column means SOMEBODY DECIDED, and a client renders it as
    exactly that, ahead of every other reason. Retention lapsing is the system
    doing what it said, and `expires_at` in the past already says so -- setting
    `deleted_at` here would turn every aged-out object into a report that
    somebody took it.
    '''
    job = ran(server, server_client, key, token, job_archive)
    store, storage = server.config["SC_STORE"], server.config["SC_STORAGE"]

    rows = artifact_rows(server, job["id"])
    assert rows
    store.execute("UPDATE artifacts SET retention_until = '2020-01-01T00:00:00.000Z' "
                  "WHERE job_id = ?", (job["id"],))

    assert sweep(server)["artifacts"] > 0

    after = artifact_rows(server, job["id"])
    assert len(after) == len(rows)
    for row in after:
        assert row["deleted_at"] is None
        assert not storage.artifact_path(row["storage_key"]).exists()

    # And the endpoint still answers, with fetchable false rather than a 404.
    listing = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/artifacts",
                   token).get_json()["items"]
    assert listing and not any(item["fetchable"] for item in listing)
    # What the client branches on to pick its sentence: aged out, not removed.
    assert all(item["deleted_at"] is None for item in listing)
    assert all(item["expires_at"] < "2021" for item in listing)


def test_an_artifact_on_legal_hold_is_never_reaped(
        server, server_client, key, token, job_archive, dispatcher):
    '''The table would not even accept the write: an artifact cannot be both
    held and deleted.'''
    job = ran(server, server_client, key, token, job_archive)
    store = server.config["SC_STORE"]

    store.execute(
        "UPDATE artifacts SET retention_until = '2020-01-01T00:00:00.000Z', "
        "  legal_hold_at = '2026-01-01T00:00:00.000Z', legal_hold_by = "
        "  (SELECT user_id FROM jobs WHERE id = ?), legal_hold_reason = 'a case' "
        "WHERE job_id = ?", (job["id"], job["id"]))

    sweep(server)

    storage = server.config["SC_STORAGE"]
    for row in artifact_rows(server, job["id"]):
        assert storage.artifact_path(row["storage_key"]).exists()


def test_an_artifact_inside_its_retention_is_left_alone(
        server, server_client, key, token, job_archive, dispatcher):
    job = ran(server, server_client, key, token, job_archive)

    assert sweep(server)["artifacts"] == 0

    storage = server.config["SC_STORAGE"]
    for row in artifact_rows(server, job["id"]):
        assert storage.artifact_path(row["storage_key"]).exists()


###########################
# Build directories
###########################

def test_a_build_tree_goes_only_after_everything_it_produced(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 After the artifacts and never before: the tree is what they were
    indexed FROM, and the portal reads a node's log straight out of it while it
    is there.'''
    job = ran(server, server_client, key, token, job_archive)
    root = server.config["SC_JOBS"].job_root(me, job["id"])
    assert root.is_dir()

    # Still in retention: the tree stays.
    sweep(server)
    assert root.is_dir()

    server.config["SC_STORE"].execute(
        "UPDATE artifacts SET retention_until = '2020-01-01T00:00:00.000Z' "
        "WHERE job_id = ?", (job["id"],))
    sweep(server)

    assert not root.exists()


def test_a_job_that_produced_nothing_keeps_its_tree(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''⚠️ The one mistake here that cannot be undone. A job with no artifacts
    is a run whose indexing failed or has not happened, not one whose results
    expired, and its tree is the only copy of it.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"])
    assert root.is_dir()
    assert not artifact_rows(server, job["id"])

    sweep(server)

    assert root.is_dir()


###########################
# Container bundles
###########################

def test_a_superseded_bundle_is_reclaimed_and_a_live_one_is_not(server):
    '''A rebuild produces a new digest, which supersedes the old row and used
    to leave its six-and-a-half gigabyte bundle exactly where it was.'''
    from siliconcompiler.remote.server import images

    store = server.config["SC_STORE"]
    root = server.config["SC_DATADIR"] / "images"

    who = store.upsert_user("operator", "op@example.test")["id"]

    images.register_software(store, "siliconcompiler", "SiliconCompiler", who)
    images.register_version(store, "siliconcompiler", "0.38.9", who)

    old_digest = "sha256:" + "a" * 64
    new_digest = "sha256:" + "b" * 64
    for digest in (old_digest, new_digest):
        bundle = images.bundle_path(root, digest)
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "config.json").write_text("{}")
        (bundle / "rootfs").mkdir(exist_ok=True)
        (bundle / "rootfs" / "big").write_bytes(b"x" * 4096)

    # Leftovers from a crashed unpack. Intermediate by construction -- the real
    # bundle is renamed into place last -- so one being present means nothing
    # is using it.
    for suffix in (".part", ".oci"):
        scratch = root / (new_digest.replace("sha256:", "") + suffix)
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "junk").write_bytes(b"y" * 2048)

    images.register_image(store, "registry:5000/sc-tools:local", old_digest,
                          [("siliconcompiler", "0.38.9")], who)
    # The same reference again: this is what a rebuild does.
    images.register_image(store, "registry:5000/sc-tools:local", new_digest,
                          [("siliconcompiler", "0.38.9")], who)

    freed = images.sweep_bundles(root, store)

    assert freed > 0
    assert not images.bundle_path(root, old_digest).exists()
    assert images.is_staged(images.bundle_path(root, new_digest))
    assert not list(root.glob("*.part"))
    assert not list(root.glob("*.oci"))
