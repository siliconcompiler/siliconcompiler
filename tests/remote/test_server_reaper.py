'''Taking back the disk.

🔴 Nothing here was reclaiming anything, and a rig filled 28 GB in one
afternoon of rebuilds. These tests are mostly about what the reaper must NOT
take.
'''

import uuid

import pytest

from conftest import call
from test_server_jobs import FakeDispatcher, stage, submit
from test_server_artifacts import ran


pytest.importorskip("flask", reason="the server extra is not installed")


EXPIRED = "UPDATE artifacts SET retained_until = '2020-01-01T00:00:00.000Z' "


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def finished(server, server_client, key, token, job_archive, dispatcher):
    return ran(server, server_client, key, token, job_archive)


def sweep(server):
    from siliconcompiler.remote.server.outputs import reaper

    return reaper.sweep(server.config["SC_STORE"], server.config["SC_STORAGE"],
                        server.config["SC_CONFIG"], server.config["SC_DATADIR"])


def artifact_rows(server, job_id):
    return server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ?", (job_id,))


def job_root(server, job_id):
    user = server.config["SC_STORE"].one("SELECT user_id FROM jobs WHERE id = ?",
                                         (job_id,))["user_id"]
    return server.config["SC_JOBS"].job_root(user, job_id)


def stored(server, job_id):
    storage = server.config["SC_STORAGE"]
    return [storage.artifact_path(row["storage_key"]).exists()
            for row in artifact_rows(server, job_id)]


def test_an_artifact_past_its_retention_loses_its_bytes_and_keeps_its_row(
        server, server_client, key, token, finished):
    '''🔴 The row stays, so *where did my results go* stays answerable. 🔴
    `deleted_at` IS set: `fetchable`'s ladder first asks whether the bytes are
    there, and retention lapsing ends HERE, so a NULL would report reaped
    bytes fetchable. NULL `deleted_by` is the reaper -- a client reads the
    enum `expired`, and `deleted_reason` is prose for a person's deletion.
    Recording it also makes the sweep idempotent across a rig's restarts.'''
    rows = artifact_rows(server, finished["id"])
    assert rows
    server.config["SC_STORE"].execute(EXPIRED + "WHERE job_id = ?", (finished["id"],))

    assert sweep(server)["artifacts"] > 0

    after = artifact_rows(server, finished["id"])
    assert len(after) == len(rows)
    for row in after:
        assert row["deleted_at"] is not None
        assert row["deleted_by"] is None and row["deleted_reason"] is None
    assert not any(stored(server, finished["id"]))

    items = call(server_client, key, "GET", f"/v1/jobs/{finished['id']}/artifacts",
                 token).get_json()["items"]
    assert items and not any(item["fetchable"] for item in items)
    assert all(item["deleted_cause"] == "expired" for item in items)
    assert all(item["deleted_reason"] is None for item in items)
    assert all(item["retained_until"] < "2021" for item in items)

    assert sweep(server)["artifacts"] == 0


def _second_row_for(store, row, location=None):
    '''Another live row naming ``row``'s bytes -- the next upload's slot, so
    the one-per-node index allows it -- in ``location`` or the same one.'''
    values = dict(row)
    values.update(id=str(uuid.uuid4()), upload_seq=2, retained_until=None,
                  location_id=location or row["location_id"])
    columns = ", ".join(f'"{name}"' for name in values)
    store.execute(f"INSERT INTO artifacts ({columns}) VALUES "
                  f"({', '.join('?' * len(values))})", tuple(values.values()))


@pytest.mark.parametrize("elsewhere,kept", [(False, True), (True, False)])
def test_bytes_go_only_when_no_live_row_names_the_object(server, finished, elsewhere, kept):
    '''🔴 An object is its location AND its key: another live row naming the
    pair keeps the bytes; the same key in another location keeps nothing.'''
    store, storage = server.config["SC_STORE"], server.config["SC_STORAGE"]
    upload = store.one("SELECT * FROM artifacts WHERE job_id = ? AND kind = 'input' "
                       "AND step IS NULL", (finished["id"],))
    if elsewhere:
        store.execute("INSERT INTO storage_locations (id, uri_base, writable) "
                      "VALUES ('archive-2026', 'file:///elsewhere/', 0)")
    _second_row_for(store, upload, "archive-2026" if elsewhere else None)
    store.execute(EXPIRED + "WHERE id = ?", (upload["id"],))

    sweep(server)

    reaped = store.one("SELECT * FROM artifacts WHERE id = ?", (upload["id"],))
    assert reaped["deleted_at"] is not None                  # the row goes either way
    assert storage.artifact_path(upload["storage_key"]).exists() is kept


def test_an_artifact_on_legal_hold_is_never_reaped(server, finished):
    '''The table would not accept an artifact both held and deleted.'''
    server.config["SC_STORE"].execute(
        "UPDATE artifacts SET retained_until = '2020-01-01T00:00:00.000Z', "
        "  legal_hold_at = '2026-01-01T00:00:00.000Z', legal_hold_by = "
        "  (SELECT user_id FROM jobs WHERE id = ?), legal_hold_reason = 'a case' "
        "WHERE job_id = ?", (finished["id"], finished["id"]))

    sweep(server)

    assert all(stored(server, finished["id"]))


def test_a_build_tree_goes_only_after_everything_it_produced(server, finished):
    '''🔴 Never before: the tree is what the artifacts were indexed FROM, and
    the portal reads a node's log out of it. In retention, nothing goes.'''
    root = job_root(server, finished["id"])
    assert root.is_dir()

    assert sweep(server)["artifacts"] == 0
    assert root.is_dir()
    assert all(stored(server, finished["id"]))

    server.config["SC_STORE"].execute(EXPIRED + "WHERE job_id = ?", (finished["id"],))
    sweep(server)

    assert not root.exists()


def test_a_job_that_produced_nothing_keeps_its_tree(
        server, server_client, key, token, job_archive, dispatcher):
    '''⚠️ The one mistake that cannot be undone: no artifacts means indexing
    failed or has not happened, and the tree is the only copy.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = job_root(server, job["id"])
    assert root.is_dir()
    # What was sent, and the server's record of it: nothing the job produced.
    assert [row["kind"] for row in artifact_rows(server, job["id"])] == ["input", "staging"]

    sweep(server)

    assert root.is_dir()


def test_bytes_that_arrived_are_kept_past_the_grants_expiry(
        server, server_client, key, token, job_archive):
    '''🔴 The grant bounds when an upload may start; the bytes go with the
    abandoned job.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    store, storage = server.config["SC_STORE"], server.config["SC_STORAGE"]
    store.execute("UPDATE jobs SET upload_grant_expires_at = '2020-01-01T00:00:00.000Z' "
                  "WHERE id = ?", (job["id"],))

    sweep(server)
    assert storage.stat_upload(job["id"]) is not None

    store.execute("UPDATE jobs SET state_changed_at = '2020-01-01T00:00:00.000Z' "
                  "WHERE id = ?", (job["id"],))
    sweep(server)
    assert store.one("SELECT state FROM jobs WHERE id = ?", (job["id"],))["state"] \
        == "abandoned"
    assert storage.stat_upload(job["id"]) is None


def test_a_superseded_bundle_is_reclaimed_and_a_live_one_is_not(server):
    '''A rebuild's new digest supersedes the old row, and used to leave its
    6.5 GB bundle where it was. Unpack leftovers are intermediate by
    construction -- the bundle is renamed into place last -- so they go too.'''
    from siliconcompiler.remote.server.software import images

    store = server.config["SC_STORE"]
    root = server.config["SC_DATADIR"] / "images"
    who = store.upsert_user("operator", "op@example.test")["id"]
    images.register_software(store, "siliconcompiler", "SiliconCompiler", who, "python")
    images.register_version(store, "siliconcompiler", "0.38.9", who)

    old_digest, new_digest = "sha256:" + "a" * 64, "sha256:" + "b" * 64
    for digest in (old_digest, new_digest):
        bundle = images.bundle_path(root, digest)
        (bundle / "rootfs").mkdir(parents=True, exist_ok=True)
        (bundle / "config.json").write_text("{}")
        (bundle / "rootfs" / "big").write_bytes(b"x" * 4096)
    for suffix in (".part", ".oci"):
        scratch = root / (new_digest.replace("sha256:", "") + suffix)
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "junk").write_bytes(b"y" * 2048)

    for digest in (old_digest, new_digest):          # the same reference: a rebuild
        images.register_image(store, "registry:5000/sc-tools:local", digest,
                              [("siliconcompiler", "0.38.9")], who)

    assert images.sweep_bundles(root, store) > 0
    assert not images.bundle_path(root, old_digest).exists()
    assert images.is_staged(images.bundle_path(root, new_digest))
    assert not list(root.glob("*.part"))
    assert not list(root.glob("*.oci"))
