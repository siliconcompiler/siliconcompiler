import json
import sqlite3

from pathlib import Path

import pytest

from siliconcompiler.remote.server.ids import uuid7, _uuid7_fallback
from siliconcompiler.remote.server.store import Store, StoreVersionError, now


###########################
# Identifiers
###########################

@pytest.mark.parametrize("mint", [uuid7, _uuid7_fallback])
def test_ids_are_uuid7(mint):
    '''Both the stdlib path and the fallback mint the same kind of id.'''
    value = mint()

    assert value.version == 7
    assert value.variant == "specified in RFC 4122"


@pytest.mark.parametrize("mint", [uuid7, _uuid7_fallback])
def test_ids_sort_by_when_they_were_minted(mint):
    '''The keyset cursor over GET /v1/jobs is a keyset over this ordering.'''
    import time

    ids = []
    for _ in range(5):
        ids.append(str(mint()))
        time.sleep(0.002)

    assert ids == sorted(ids)


###########################
# The schema
###########################

def test_the_store_is_created_on_first_open():
    '''A datadir that has never been used starts a working server.'''
    path = Path("nested/server.db")
    assert not path.exists()

    with Store(path):
        pass

    assert path.exists()


def test_eighteen_tables():
    '''The profile is 18 tables of the contract's 41.

    Counted rather than listed loosely: the omissions are entitlements, terms,
    projects, the artifact gate, the admin tables and metering, and each was a
    decision rather than an oversight.
    '''
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
        # 🆕 The nineteenth, and the contract's own table. It arrived with a
        # per-user `max_download_bytes`: a limit that can differ per account
        # has to be stored per account.
        "user_limits",
    }


def test_dropped_tables_are_absent():
    '''What this profile does not have, it does not have half of.

    Several have half-shaped equivalents in the server being replaced -- a
    users.json, some quota fields -- and those were removals, not migrations.
    '''
    with Store("server.db") as store:
        tables = {row["name"] for row in store.all(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}

    # ⚠️ `user_limits` is NOT in this list any more and `plans` still is, which
    # looks inconsistent and is not. The contract pairs them -- a plan is a
    # named tier and `user_limits` is the sparse override of one -- and this
    # deployment has no tiers, so what a row inherits from is the operator's
    # config.json rather than a plan. Taking the override table without the
    # plan table is the whole of the difference.
    for dropped in ("grants", "resources", "resource_agreements", "plans",
                    "usage_events", "terms_documents",
                    "terms_versions", "terms_decisions", "projects",
                    "project_members", "job_project_assignments",
                    "ci_credentials", "device_authorizations", "auth_events",
                    "admin_actions", "admin_elevations", "artifact_resources",
                    "artifact_access", "artifact_disclosures", "audit_exports",
                    "service_notices"):
        assert dropped not in tables


def test_job_states_are_the_closed_set():
    '''Ten states, and `terminal` is what a client reads.

    The sets grew twice while the contract was being written, which is why
    terminal is published rather than derived from the names.
    '''
    with Store("server.db") as store:
        states = {row["state"]: row["terminal"] for row in
                  store.all("SELECT state, terminal FROM job_states")}

    assert states == {
        "created": 0, "awaiting_input": 0, "queued": 0, "running": 0,
        "cancelling": 0,
        "completed": 1, "failed": 1, "cancelled": 1, "rejected": 1,
        "abandoned": 1,
    }


def test_node_states_are_a_different_closed_set():
    '''Deliberately not the job set: a node is never `awaiting_input`, and a
    job is never `skipped`.'''
    with Store("server.db") as store:
        states = {row["state"]: row["terminal"] for row in
                  store.all("SELECT state, terminal FROM node_states")}

    assert states == {
        "pending": 0, "queued": 0, "preparing": 0, "running": 0,
        "completed": 1, "failed": 1, "skipped": 1, "cancelled": 1,
    }


def test_artifact_kinds_carry_retention():
    '''NULL is the floor and nothing more; a number is a longer promise.'''
    with Store("server.db") as store:
        kinds = {row["kind"]: row["retention_days"] for row in
                 store.all("SELECT kind, retention_days FROM artifact_kinds")}

    assert set(kinds) == {"manifest", "logs", "reports", "issue", "final",
                          "outputs", "input", "node"}
    assert kinds["manifest"] == 1825
    assert kinds["outputs"] is None


def test_foreign_keys_are_enforced():
    '''They are off by default in SQLite and set per connection, so this is the
    only thing making the schema's references mean anything.'''
    with Store("server.db") as store:
        with pytest.raises(sqlite3.IntegrityError):
            store.execute(
                "INSERT INTO devices "
                "(id, user_id, name, dpop_jkt, machine_id_source) "
                "VALUES ('d', 'nosuchuser', 'laptop', 'jkt', 'none')")


def test_a_job_cannot_be_admitted_without_a_resolved_pdk():
    '''The constraint the contract spells out: a job that reached the scheduler
    has had its PDK re-derived.'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

        with pytest.raises(sqlite3.IntegrityError):
            store.execute(
                "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                "VALUES (?, ?, 'running', 'gcd', 'job0', '{}')",
                (str(uuid7()), user["id"]))


def test_an_unknown_job_state_is_refused():
    '''job_states is a table rather than a CHECK so the state machine can read
    `terminal`; it still closes the set.'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

        with pytest.raises(sqlite3.IntegrityError):
            store.execute(
                "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                "VALUES (?, ?, 'sideways', 'gcd', 'job0', '{}')",
                (str(uuid7()), user["id"]))


def test_run_hash_lookup_is_owner_scoped():
    '''Job reuse trusts a client-supplied hash because the lookup cannot leave
    the caller's own rows: a wrong hash hands a user their own stale job, which
    is confusing rather than a disclosure.'''
    with Store("server.db") as store:
        mine = store.upsert_user("local", "machine:1000")
        theirs = store.upsert_user("local", "machine:1001")

        job_id = str(uuid7())
        store.execute(
            "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, run_hash) "
            "VALUES (?, ?, 'created', 'gcd', 'job0', '{}', 'sha256:abc')",
            (job_id, theirs["id"]))

        found = store.one(
            "SELECT id FROM jobs WHERE user_id = ? AND run_hash = ? "
            "AND deleted_at IS NULL",
            (mine["id"], "sha256:abc"))
        assert found is None

        found = store.one(
            "SELECT id FROM jobs WHERE user_id = ? AND run_hash = ? "
            "AND deleted_at IS NULL",
            (theirs["id"], "sha256:abc"))
        assert found["id"] == job_id


###########################
# Identity
###########################

def test_a_user_is_minted_once_per_issuer_and_subject():
    '''Minting the identity is what turns the ownership check from a
    pass-through into a real one.'''
    with Store("server.db") as store:
        first = store.upsert_user("local", "machine:1000")
        again = store.upsert_user("local", "machine:1000")
        other = store.upsert_user("local", "machine:1001")

        assert first["id"] == again["id"]
        assert other["id"] != first["id"]
        assert store.one("SELECT count(*) AS n FROM users")["n"] == 2


def test_two_issuers_cannot_collide():
    '''`issuer` is in the key so a real identity provider later cannot land on
    top of an auto-provisioned subject.'''
    with Store("server.db") as store:
        local = store.upsert_user("local", "1000")
        google = store.upsert_user("https://accounts.google.com", "1000")

        assert local["id"] != google["id"]


###########################
# Timestamps
###########################

def test_python_and_sqlite_write_the_same_timestamp_shape():
    '''A row written by Python and one written by a DEFAULT have to sort
    against each other, so they are byte-comparable rather than merely both
    "a time".'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

    from_default = user["created_at"]
    from_python = now()

    assert from_default.endswith("Z")
    assert from_python.endswith("Z")
    assert len(from_default) == len(from_python)
    assert from_default[10] == from_python[10] == "T"


###########################
# Versioning
###########################

def test_a_store_from_another_schema_version_is_refused():
    '''An unrecognised column is a silent wrong answer; a refusal is a
    message.'''
    path = Path("server.db")
    with Store(path):
        pass

    con = sqlite3.connect(str(path))
    con.execute("PRAGMA user_version = 99")
    con.commit()
    con.close()

    with pytest.raises(StoreVersionError, match="schema version 99") as raised:
        Store(path)

    # 🔴 And it says what to do about it. A server that will not start is the
    # worst moment to make somebody read the source for the answer.
    assert "Upgrade this server" in str(raised.value)


def test_a_store_from_an_older_schema_version_says_there_is_no_migration():
    """There is none, deliberately -- and the refusal has to say so rather than
    leave an operator waiting for one."""
    path = Path("older.db")
    with Store(path):
        pass

    con = sqlite3.connect(str(path))
    con.execute("PRAGMA user_version = 1")
    con.commit()
    con.close()

    with pytest.raises(StoreVersionError, match="schema version 1") as raised:
        Store(path)

    assert "no migration" in str(raised.value)
    assert "Move" in str(raised.value)


###########################
# The capabilities join
###########################

def test_software_is_advertised_only_where_a_live_image_holds_it():
    '''A version with no live image is not advertised, so GET /v1's software
    stops being a promise the server cannot keep.'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

        store.execute("INSERT INTO software (name, display_name, kind, added_by) "
                      "VALUES ('siliconcompiler', 'SiliconCompiler', 'python', ?)",
                      (user["id"],))
        store.execute("INSERT INTO software_versions "
                      "(software_name, version, preference, added_by) "
                      "VALUES ('siliconcompiler', '0.39.1', 10, ?)", (user["id"],))
        store.execute("INSERT INTO software_versions "
                      "(software_name, version, preference, added_by) "
                      "VALUES ('siliconcompiler', '0.39.0', 5, ?)", (user["id"],))

        # Declared, but nothing provides it yet.
        assert store.advertised_software() == {"python": {}, "tools": {}}

        image = str(uuid7())
        store.execute(
            "INSERT INTO images (id, registry_ref, digest, resolved_at, registered_by) "
            "VALUES (?, 'ghcr.io/x/y:0.39.1', 'sha256:aa', ?, ?)",
            (image, now(), user["id"]))
        store.execute("INSERT INTO image_contents (image_id, software_name, version) "
                      "VALUES (?, 'siliconcompiler', '0.39.1')", (image,))

        assert store.advertised_software() == {
            "python": {"siliconcompiler": ["0.39.1"]}, "tools": {}}


def test_a_retired_image_stops_advertising_its_contents():
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")
        store.execute("INSERT INTO software (name, display_name, kind, added_by) "
                      "VALUES ('openroad', 'OpenROAD', 'tool', ?)", (user["id"],))
        store.execute("INSERT INTO software_versions "
                      "(software_name, version, added_by) "
                      "VALUES ('openroad', '2.0.1', ?)", (user["id"],))

        image = str(uuid7())
        store.execute(
            "INSERT INTO images (id, registry_ref, digest, resolved_at, registered_by) "
            "VALUES (?, 'ghcr.io/x/y:2.0.1', 'sha256:bb', ?, ?)",
            (image, now(), user["id"]))
        store.execute("INSERT INTO image_contents (image_id, software_name, version) "
                      "VALUES (?, 'openroad', '2.0.1')", (image,))

        assert store.advertised_software() == {
            "python": {}, "tools": {"openroad": ["2.0.1"]}}

        store.execute("UPDATE images SET retired_at = ?, retired_by = ? WHERE id = ?",
                      (now(), user["id"], image))

        assert store.advertised_software() == {"python": {}, "tools": {}}


def test_versions_are_ordered_most_preferred_first():
    '''GET /v1 publishes an ordered array, and the order is the operator's.'''
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")
        store.execute("INSERT INTO software (name, display_name, kind, added_by) "
                      "VALUES ('siliconcompiler', 'SiliconCompiler', 'python', ?)", (user["id"],))

        image = str(uuid7())
        store.execute(
            "INSERT INTO images (id, registry_ref, digest, resolved_at, registered_by) "
            "VALUES (?, 'ghcr.io/x/y:latest', 'sha256:cc', ?, ?)",
            (image, now(), user["id"]))

        for version, preference in (("0.38.4", 1), ("0.39.1", 10), ("0.39.0", 5)):
            store.execute("INSERT INTO software_versions "
                          "(software_name, version, preference, added_by) "
                          "VALUES ('siliconcompiler', ?, ?, ?)",
                          (version, preference, user["id"]))
            store.execute("INSERT INTO image_contents "
                          "(image_id, software_name, version) "
                          "VALUES (?, 'siliconcompiler', ?)", (image, version))

        assert store.advertised_software() == {
            "python": {"siliconcompiler": ["0.39.1", "0.39.0", "0.38.4"]},
            "tools": {}}


###########################
# Transactions
###########################

def test_a_failed_transaction_leaves_nothing_behind():
    with Store("server.db") as store:
        user = store.upsert_user("local", "machine:1000")

        with pytest.raises(sqlite3.IntegrityError):
            with store.transaction() as con:
                con.execute(
                    "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                    "VALUES (?, ?, 'created', 'gcd', 'job0', ?)",
                    (str(uuid7()), user["id"], json.dumps({})))
                con.execute(
                    "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor) "
                    "VALUES ('x', 'nosuchuser', 'created', 'gcd', 'job1', '{}')")

        assert store.one("SELECT count(*) AS n FROM jobs")["n"] == 0


###########################
# Threads
###########################

def test_a_second_thread_gets_a_working_connection():
    '''A sqlite3 connection belongs to the thread that opened it, and the server
    answers each request on a worker thread. One shared connection fails on
    every request that is not the first -- which app.test_client() cannot show,
    because it runs the handler on the calling thread.
    '''
    import threading

    with Store("server.db") as store:
        store.upsert_user("local", "machine:1000")

        result = {}

        def read():
            try:
                result["n"] = store.one("SELECT count(*) AS n FROM users")["n"]
            except Exception as e:                               # noqa: BLE001
                result["error"] = e

        worker = threading.Thread(target=read)
        worker.start()
        worker.join()

    assert "error" not in result, result.get("error")
    assert result["n"] == 1


def test_every_thread_enforces_foreign_keys():
    '''PRAGMA foreign_keys is per connection, not per database.

    Missing it on the worker path would leave the schema's references enforced
    on whichever thread opened the store and unenforced everywhere else -- a
    difference nothing notices until a bad row is already written.
    '''
    import threading

    with Store("server.db") as store:
        outcome = {}

        def write():
            try:
                store.execute(
                    "INSERT INTO devices "
                    "(id, user_id, name, dpop_jkt, machine_id_source) "
                    "VALUES ('d', 'nosuchuser', 'laptop', 'jkt', 'none')")
                outcome["refused"] = False
            except sqlite3.IntegrityError:
                outcome["refused"] = True

        worker = threading.Thread(target=write)
        worker.start()
        worker.join()

    assert outcome["refused"] is True
