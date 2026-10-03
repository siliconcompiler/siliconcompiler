import json
import os
import sqlite3
import threading
import uuid

from pathlib import Path

import pytest

from siliconcompiler.remote.server.state.store import (
    STORE_VERSION, Store, StoreVersionError, now)


def in_a_thread(work):
    '''Run ``work`` on a thread of its own: what it returned, or raised.'''
    result = {}

    def run():
        try:
            result["value"] = work()
        except Exception as e:                                   # noqa: BLE001
            result["error"] = e

    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    return result


def test_the_store_is_created_on_first_open():
    '''A datadir never used starts a working server.'''
    path = Path("nested/server.db")
    assert not path.exists()

    with Store(path):
        pass

    assert path.exists()


def test_the_profiles_tables():
    '''The profile's 18 of the v1 API's 41, plus `user_limits` (a per-account
    `max_download_bytes` is stored per account; `plans` stays out, since a row
    inherits from config.json) and `job_continuations`.
    Counted exactly: every omission -- entitlements, terms, projects, the
    artifact gate, admin, metering -- was a decision, and is wholly absent.'''
    with Store("server.db") as store:
        tables = {row["name"] for row in store.all(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'")}

    assert tables == {
        "users",
        "devices", "device_events", "token_families", "refresh_tokens",
        "jobs", "job_states", "node_states", "job_state_transitions",
        "job_nodes", "job_node_edges",
        "artifact_kinds", "storage_locations", "artifacts",
        "software", "software_versions", "images", "image_contents",
        "user_limits", "job_continuations",
    }


@pytest.mark.parametrize("table,states", [
    # Eleven, and `terminal` is published rather than derived from the names.
    ("job_states", {"created": 0, "awaiting_input": 0, "staging": 0, "queued": 0,
                    "running": 0, "cancelling": 0, "completed": 1, "failed": 1,
                    "cancelled": 1, "rejected": 1, "abandoned": 1}),
    # Deliberately not the job set: no node `awaiting_input`, no job `skipped`.
    ("node_states", {"pending": 0, "queued": 0, "preparing": 0, "running": 0,
                     "completed": 1, "failed": 1, "skipped": 1, "cancelled": 1}),
])
def test_the_states_are_closed_sets(table, states):
    with Store("server.db") as store:
        assert {row["state"]: row["terminal"] for row in
                store.all(f"SELECT state, terminal FROM {table}")} == states


def test_artifact_kinds_carry_retention():
    '''NULL is the floor and nothing more; a number is a longer promise.'''
    with Store("server.db") as store:
        kinds = {row["kind"]: row["retention_seconds"] for row in
                 store.all("SELECT kind, retention_seconds FROM artifact_kinds")}

    assert set(kinds) == {"manifest", "logs", "reports", "issue", "final",
                          "outputs", "input", "node", "staging", "diagnostics"}
    assert kinds["manifest"] == 157680000   # five years
    # The server's record, kept as the run's log is; the operators', 90 days.
    assert kinds["staging"] == kinds["logs"]
    assert kinds["diagnostics"] == 90 * 86400
    assert kinds["outputs"] is None


def test_every_thread_enforces_foreign_keys():
    '''Off by default in SQLite and set per connection, so per thread: missing
    it on the worker path leaves references unenforced on every request.'''
    def orphan():
        store.execute("INSERT INTO devices (id, user_id, name, dpop_jkt, machine_id_source) "
                      "VALUES ('d', 'nosuchuser', 'laptop', 'jkt', 'none')")

    with Store("server.db") as store:
        with pytest.raises(sqlite3.IntegrityError):
            orphan()
        assert isinstance(in_a_thread(orphan).get("error"), sqlite3.IntegrityError)


@pytest.mark.parametrize("state", ["running", "sideways"],
                         ids=["admitted-without-a-pdk", "unknown-state"])
def test_a_job_row_outside_the_state_machine_is_refused(state):
    '''A job that reached the scheduler has had its PDK re-derived; and
    job_states is a table, so `terminal` can be read, that still closes the set.'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

        with pytest.raises(sqlite3.IntegrityError):
            store.execute(
                "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                "VALUES (?, ?, ?, 'gcd', 'job0', '{}')", (str(uuid.uuid4()), user["id"], state))


def test_run_hash_lookup_is_owner_scoped():
    '''Reuse trusts a client's hash because the lookup cannot leave the
    caller's rows: a wrong hash is confusing, never a disclosure.'''
    lookup = "SELECT id FROM jobs WHERE user_id = ? AND run_hash = ? AND deleted_at IS NULL"
    with Store("server.db") as store:
        mine = store.upsert_user("local", "machine:1000")
        theirs = store.upsert_user("local", "machine:1001")
        job_id = str(uuid.uuid4())
        store.execute(
            "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, run_hash) "
            "VALUES (?, ?, 'created', 'gcd', 'job0', '{}', 'sha256:abc')",
            (job_id, theirs["id"]))

        assert store.one(lookup, (mine["id"], "sha256:abc")) is None
        assert store.one(lookup, (theirs["id"], "sha256:abc"))["id"] == job_id


def test_a_user_is_minted_once_per_issuer_and_subject():
    '''What makes the ownership check real; `issuer` is in the key so a real
    identity provider cannot land on an auto-provisioned subject.'''
    with Store("server.db") as store:
        first = store.upsert_user("local", "machine:1000")
        again = store.upsert_user("local", "machine:1000")
        other = store.upsert_user("local", "machine:1001")

        assert first["id"] == again["id"]
        assert other["id"] != first["id"]
        assert store.one("SELECT count(*) AS n FROM users")["n"] == 2
        assert store.upsert_user("local", "1000")["id"] != \
            store.upsert_user("https://accounts.google.com", "1000")["id"]


def test_python_and_sqlite_write_the_same_timestamp_shape():
    '''Byte-comparable, so rows from Python and from a DEFAULT sort together.'''
    with Store("server.db") as store:
        from_default = store.upsert_user("local", "machine:1000")["created_at"]
    from_python = now()

    assert from_default.endswith("Z") and from_python.endswith("Z")
    assert len(from_default) == len(from_python)
    assert from_default[10] == from_python[10] == "T"


# 99 is newer; 1, and the store from before the v1 consistency pass, older.
@pytest.mark.parametrize("version,says", [
    (99, ["schema version 99", "Upgrade this server"]),
    (1, [f"schema version 1, and this server speaks version {STORE_VERSION}",
         "no migration", "Move server.db aside"]),
    (STORE_VERSION - 1, [f"schema version {STORE_VERSION - 1}, and this server speaks "
                         f"version {STORE_VERSION}", "no migration", "Move server.db aside"]),
])
def test_a_store_from_another_schema_version_is_refused_saying_what_to_do(version, says):
    '''An unrecognised column is a silent wrong answer; a refusal says what to
    do, since a server that will not start is the worst moment to read source.'''
    path = Path("server.db")
    with Store(path):
        pass
    con = sqlite3.connect(str(path))
    con.execute(f"PRAGMA user_version = {version}")
    con.commit()
    con.close()

    with pytest.raises(StoreVersionError) as raised:
        Store(path)

    for said in says:
        assert said in str(raised.value)


def _declare(store, user, name, kind, versions):
    store.execute("INSERT INTO software (name, display_name, kind, added_by) "
                  "VALUES (?, ?, ?, ?)", (name, name, kind, user))
    for version, preference in versions:
        store.execute("INSERT INTO software_versions (software_name, version, preference, "
                      "added_by) VALUES (?, ?, ?, ?)", (name, version, preference, user))


def _image(store, user, name, versions):
    image = str(uuid.uuid4())
    store.execute(
        "INSERT INTO images (id, registry_ref, digest, resolved_at, registered_by) "
        "VALUES (?, ?, ?, ?, ?)", (image, f"ghcr.io/x/y:{image}", f"sha256:{image}", now(), user))
    for version in versions:
        store.execute("INSERT INTO image_contents (image_id, software_name, version) "
                      "VALUES (?, ?, ?)", (image, name, version))
    return image


def test_software_is_advertised_where_a_live_image_holds_it_most_preferred_first():
    '''Otherwise GET /v1's software is a promise the server cannot keep; the
    order is the operator's.'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")["id"]
        _declare(store, user, "siliconcompiler", "python",
                 [("0.38.4", 1), ("0.39.1", 10), ("0.39.0", 5)])
        assert store.advertised_software() == {"python": {}, "tools": {}, "interpreter": {}}

        _image(store, user, "siliconcompiler", ["0.39.1"])
        assert store.advertised_software()["python"] == {"siliconcompiler": ["0.39.1"]}

        _image(store, user, "siliconcompiler", ["0.38.4", "0.39.1", "0.39.0"])
        assert store.advertised_software() == {
            "python": {"siliconcompiler": ["0.39.1", "0.39.0", "0.38.4"]},
            "tools": {}, "interpreter": {}}


def test_a_retired_image_stops_advertising_its_contents():
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")["id"]
        _declare(store, user, "openroad", "tool", [("2.0.1", 0)])
        image = _image(store, user, "openroad", ["2.0.1"])
        assert store.advertised_software() == {
            "python": {}, "tools": {"openroad": ["2.0.1"]}, "interpreter": {}}

        store.execute("UPDATE images SET retired_at = ?, retired_by = ? WHERE id = ?",
                      (now(), user, image))

        assert store.advertised_software() == {"python": {}, "tools": {}, "interpreter": {}}


def test_a_failed_transaction_leaves_nothing_behind():
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

        with pytest.raises(sqlite3.IntegrityError):
            with store.transaction() as con:
                con.execute(
                    "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                    "VALUES (?, ?, 'created', 'gcd', 'job0', ?)",
                    (str(uuid.uuid4()), user["id"], json.dumps({})))
                con.execute(
                    "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                    "VALUES ('x', 'nosuchuser', 'created', 'gcd', 'job1', '{}')")

        assert store.one("SELECT count(*) AS n FROM jobs")["n"] == 0


def test_a_second_thread_gets_a_working_connection():
    '''A connection belongs to its thread and each request runs on a worker,
    which app.test_client() cannot show: it runs handlers on the caller.'''
    with Store("server.db") as store:
        store.upsert_user("local", "machine:1000")

        result = in_a_thread(lambda: store.one("SELECT count(*) AS n FROM users")["n"])

    assert "error" not in result, result.get("error")
    assert result["value"] == 1


@pytest.mark.skipif(not os.path.isdir("/proc/self/fd"),
                    reason="needs /proc to count descriptors")
def test_a_server_polled_for_a_while_does_not_run_out_of_descriptors(tmp_path):
    '''A thread per request, three descriptors a connection under WAL, kept
    for `close()` and never released: a client polling once a second ran the
    process out in minutes.'''
    import urllib.request

    from werkzeug.serving import make_server

    from siliconcompiler.remote.server.app import create_app

    app = create_app(tmp_path / "datadir", cluster="local")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/v1/healthz"

    try:
        urllib.request.urlopen(url).read()
        before = len(os.listdir("/proc/self/fd"))
        for _ in range(300):
            urllib.request.urlopen(url).read()
        after = len(os.listdir("/proc/self/fd"))
    finally:
        server.shutdown()
        thread.join(timeout=10)

    assert after - before < 20                  # about 900 before the fix
    assert len(app.config["SC_STORE"]._connections) <= 2


def test_a_thread_that_ends_without_releasing_is_reaped(tmp_path):
    '''The backstop: the next connection opened closes what dead threads held.'''
    store = Store(tmp_path / "server.db")

    for _ in range(20):
        in_a_thread(lambda: store.one("SELECT 1"))

    store.release()
    store.one("SELECT 1")

    assert len(store._connections) == 1
    store.close()


def test_close_really_closes_other_threads_connections(tmp_path):
    '''It used to fail silently: only the opening thread may close one, unless
    the connection says otherwise.'''
    store = Store(tmp_path / "server.db")

    def use():
        store.one("SELECT 1")
        return store._local.con

    held = in_a_thread(use)["value"]
    store.close()

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        held.execute("SELECT 1")
