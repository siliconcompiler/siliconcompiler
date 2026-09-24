import time

import pytest

from conftest import call, login, slug
from test_server_jobs import FakeDispatcher, stage, submit


pytest.importorskip("flask", reason="the server extra is not installed")


# Endpoints 20, 21 and 22. None of the three carries bytes: two answer 303 and
# one answers a listing, which is what keeps an orchestrator's capacity off the
# size of what it stores.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def ran(server, server_client, key, token, job_archive, prepare=None,
        state="completed", error=None):
    '''Submit a job, leave what a run leaves, and let the poll index it.

    `prepare(job_root, build_dir)` runs after the work directories exist and
    before the job is read as terminal, which is the only window in which the
    indexer can see a file: `collect` runs once, at the transition.
    '''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    # The run itself is the local dispatcher's business and is covered by the
    # parity tests; here the progress file is written directly, so that what is
    # under test is the indexing rather than the scheduler.
    jobs = server.config["SC_JOBS"]
    root = jobs.job_root(
        call(server_client, key, "GET", "/v1/me", token).get_json()["id"], job["id"])

    from siliconcompiler.remote.server import runspec

    node_root = root / "gcd" / "job0"
    for step in ("stepone", "steptwo"):
        work = node_root / step / "0"
        (work / "outputs").mkdir(parents=True, exist_ok=True)
        (work / "reports").mkdir(parents=True, exist_ok=True)
        (work / "inputs").mkdir(parents=True, exist_ok=True)
        (work / f"sc_{step}_0.log").write_text(f"{step} ran\n")
        (work / "outputs" / "gcd.pkg.json").write_text('{"produced": true}')
        (work / "reports" / "metrics.json").write_text("{}")
        (work / "inputs" / "upstream.json").write_text("{}")

    if prepare is not None:
        prepare(root, node_root)

    progress = {
        "state": state,
        "started_at": "2026-09-22T10:00:00.000Z",
        "finished_at": "2026-09-22T10:01:00.000Z",
        "nodes": {f"{step}/0": {"state": "completed", "exit_code": 0,
                                "started_at": "2026-09-22T10:00:00.000Z",
                                "finished_at": "2026-09-22T10:00:30.000Z"}
                  for step in ("stepone", "steptwo")},
    }
    if error is not None:
        progress["error"] = error
    runspec.write_progress(node_root / runspec.PROGRESS_FILENAME, progress)

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == state
    return read


@pytest.fixture
def finished(server, server_client, key, token, job_archive, dispatcher):
    '''A job that ran to completion, with its results indexed.'''
    return ran(server, server_client, key, token, job_archive)


def listing(client, key, token, job_id, query=""):
    return call(client, key, "GET", f"/v1/jobs/{job_id}/artifacts{query}",
                token).get_json()["items"]


###########################
# Indexing
###########################

def test_a_finished_run_is_indexed(server_client, key, token, finished):
    items = listing(server_client, key, token, finished["id"])

    kinds = {(item["kind"], item["step"]) for item in items}
    assert ("manifest", None) in kinds
    assert ("logs", "stepone") in kinds
    assert ("logs", "steptwo") in kinds
    # A bundle per node, indexed as that node finishes -- which is what lets a
    # client take a node's results while the rest of the flow runs on. No
    # outputs or reports: they would be a second copy of what it holds.
    assert ("bundle", "stepone") in kinds
    assert ("bundle", "steptwo") in kinds
    assert not [k for k, _ in kinds if k in ("outputs", "reports")]


def test_every_required_member_is_published(server_client, key, token, finished):
    for item in listing(server_client, key, token, finished["id"]):
        for member in ("id", "step", "index", "kind", "media_type", "size_bytes",
                       "content_hash", "created_at", "expires_at", "deleted_at",
                       "fetchable"):
            assert member in item, member
        assert item["content_hash"].startswith("sha256:")
        # An unauthenticated deployment never emits these: nothing here is
        # approval-gated, and an endpoint that always refuses is worse than an
        # absent one.
        assert "blocked_by" not in item
        assert "access_request_url" not in item


def test_retention_is_per_kind_and_the_job_floor_is_only_a_floor(
        server_client, key, token, finished):
    '''A manifest and the outputs beside it go at different times, so one
    number cannot answer for a job.'''
    items = listing(server_client, key, token, finished["id"])
    by_kind = {item["kind"]: item["expires_at"] for item in items}

    assert by_kind["manifest"] > by_kind["bundle"]
    # `bundle` has no number of its own, so it gets the deployment's floor --
    # and a bundle may never outlive its contents.
    assert by_kind["bundle"] > "2026"
    # Same retention rule, so the same day; they are written moments apart.
    assert by_kind["logs"][:10] == by_kind["manifest"][:10]


def test_a_bundle_holds_its_node_and_leaves_out_its_inputs(
        server, server_client, key, token, finished):
    '''A node's bundle is that node's working directory. `inputs/` is left out
    because it is copies of the upstream node's outputs, which the caller is
    getting from the upstream node's own bundle.'''
    import tarfile

    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'bundle' "
        "AND step = 'stepone'", (finished["id"],))
    path = server.config["SC_STORAGE"].artifact_path(row["storage_key"])

    with tarfile.open(path) as tar:
        names = tar.getnames()

    # Relative to the node's own directory, so a client unpacks it straight
    # back into the same place.
    assert "outputs/gcd.pkg.json" in names
    assert "sc_stepone_0.log" in names
    assert not any("inputs" in name.split("/") for name in names)


def test_what_the_client_uploaded_is_never_sent_back(
        server, server_client, key, token, finished):
    '''`sc_collected_files/` is what the CLIENT uploaded. It deletes its own
    copy once the archive is built -- it is the largest thing in a build
    directory -- so sending it back undoes that and pays for the bytes twice.'''
    import tarfile

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    root = server.config["SC_JOBS"].job_root(me, finished["id"]) / "gcd" / "job0"
    (root / "stepone" / "0" / "sc_collected_files").mkdir(parents=True, exist_ok=True)
    (root / "stepone" / "0" / "sc_collected_files" / "gcd.v").write_text("module m;")

    store = server.config["SC_STORE"]
    store.execute("DELETE FROM artifacts WHERE job_id = ?", (finished["id"],))
    server.config["SC_JOBS"]._index(
        store.one("SELECT * FROM jobs WHERE id = ?", (finished["id"],)))

    row = store.one("SELECT * FROM artifacts WHERE job_id = ? AND kind = 'bundle' "
                    "AND step = 'stepone'", (finished["id"],))
    with tarfile.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"])) as tar:
        names = tar.getnames()

    assert not any("sc_collected_files" in name.split("/") for name in names)


def test_indexing_twice_does_not_duplicate_the_listing(server, server_client,
                                                       key, token, finished):
    before = len(listing(server_client, key, token, finished["id"]))

    jobs = server.config["SC_JOBS"]
    jobs._index(server.config["SC_STORE"].one(
        "SELECT * FROM jobs WHERE id = ?", (finished["id"],)))

    assert len(listing(server_client, key, token, finished["id"])) == before


def test_a_job_that_left_nothing_lists_nothing(server_client, key, token,
                                               job_archive, dispatcher):
    '''An empty listing is a legal answer, not an error.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    assert listing(server_client, key, token, job["id"]) == []


###########################
# 21. the listing
###########################

def test_the_listing_filters_by_kind_step_and_index(server_client, key, token,
                                                    finished):
    logs = listing(server_client, key, token, finished["id"], "?kind=logs")
    assert {item["kind"] for item in logs} == {"logs"}

    # A kind that is absent was never indexed here, which is a true answer and
    # not an error: this deployment stores a bundle instead.
    assert listing(server_client, key, token, finished["id"], "?kind=reports") == []

    one = listing(server_client, key, token, finished["id"],
                  "?step=stepone&index=0")
    assert {item["step"] for item in one} == {"stepone"}


def test_an_unknown_kind_is_refused(server_client, key, token, finished):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts?kind=souvenirs", token)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_the_listing_pages(server_client, key, token, finished):
    first = call(server_client, key, "GET",
                 f"/v1/jobs/{finished['id']}/artifacts?limit=2", token)

    assert len(first.get_json()["items"]) == 2
    assert 'rel="next"' in first.headers["Link"]

    seen, response = [], first
    while True:
        seen.extend(item["id"] for item in response.get_json()["items"])
        link = response.headers.get("Link")
        if not link:
            break
        response = call(server_client, key, "GET",
                        link.split(">", 1)[0].lstrip("<"), token)

    # manifest, plus a log and a bundle for each of the two nodes.
    assert len(seen) == len(set(seen)) == 5


def test_a_strangers_listing_is_a_404(server_client, key, token, finished):
    from siliconcompiler.remote import dpop

    other_key = dpop.generate_key()
    other = login(server_client, other_key,
                  subject="machine:1001").get_json()["access_token"]

    response = call(server_client, other_key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts", other)
    assert response.status_code == 404


def test_a_deleted_jobs_subresources_are_gone(server_client, key, token, finished):
    '''The job stays readable with deleted_at set and its subresources 404.'''
    call(server_client, key, "DELETE", f"/v1/jobs/{finished['id']}", token)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts", token)
    assert response.status_code == 404
    assert call(server_client, key, "GET", f"/v1/jobs/{finished['id']}",
                token).status_code == 200


###########################
# 22. the bytes
###########################

def test_fetching_an_artifact_is_a_303_to_a_signed_route(server_client, key,
                                                         token, finished):
    item = listing(server_client, key, token, finished["id"])[0]

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)

    assert response.status_code == 303
    target = response.headers["Location"]
    assert "/storage/artifact/" in target and "sig=" in target

    bytes_response = server_client.get(target.split("http://localhost", 1)[1])
    assert bytes_response.status_code == 200
    assert len(bytes_response.data) == item["size_bytes"]


def test_the_bytes_need_a_signature(server_client, key, token, finished):
    item = listing(server_client, key, token, finished["id"])[0]

    response = server_client.get(
        f"/storage/artifact/{finished['id']}/{item['id']}")

    assert response.status_code == 400


def test_an_expired_link_is_refused(server_client, key, token, finished):
    item = listing(server_client, key, token, finished["id"])[0]
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)

    target = response.headers["Location"].split("http://localhost", 1)[1]
    stale = target.replace(
        f"expires={target.split('expires=')[1].split('&')[0]}",
        f"expires={int(time.time()) - 10}")

    assert server_client.get(stale).status_code == 400


def test_an_upload_grant_cannot_be_presented_as_a_download(server_client, key,
                                                           token, finished):
    '''Different message prefixes, so a grant to PUT one job's archive is never
    a grant to GET another job's outputs.'''
    storage = server_client.application.config["SC_STORAGE"]
    item = listing(server_client, key, token, finished["id"])[0]

    expires = int(time.time()) + 300
    wrong = storage.sign_upload(item["id"], 1000, expires)

    response = server_client.get(
        f"/storage/artifact/{finished['id']}/{item['id']}"
        f"?expires={expires}&sig={wrong}")
    assert response.status_code == 400


def test_a_deleted_artifact_is_a_404_not_a_403(server, server_client, key,
                                               token, finished):
    '''There is nothing left to be entitled to.'''
    item = listing(server_client, key, token, finished["id"])[0]
    server.config["SC_STORE"].execute(
        "UPDATE artifacts SET deleted_at = '2026-09-22T00:00:00.000Z', "
        "deleted_by = ?, delete_reason = 'test' WHERE id = ?",
        (call(server_client, key, "GET", "/v1/me", token).get_json()["id"],
         item["id"]))

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)
    assert response.status_code == 404

    # The row stays in the listing, which is the same call jobs.deleted_at made.
    still = [a for a in listing(server_client, key, token, finished["id"])
             if a["id"] == item["id"]]
    assert still and still[0]["deleted_at"] and still[0]["fetchable"] is False


def test_an_artifact_past_its_retention_is_not_fetchable(server, server_client,
                                                         key, token, finished):
    item = listing(server_client, key, token, finished["id"])[0]
    server.config["SC_STORE"].execute(
        "UPDATE artifacts SET retention_until = '2020-01-01T00:00:00.000Z' "
        "WHERE id = ?", (item["id"],))

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)

    assert response.status_code == 403
    assert slug(response) == "entitlement-denied"


###########################
# 20. one node's log
###########################

def test_a_terminal_nodes_log_redirects_to_the_archive(server_client, key,
                                                       token, finished):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 303
    bytes_response = server_client.get(
        response.headers["Location"].split("http://localhost", 1)[1])
    assert bytes_response.data == b"stepone ran\n"
    assert bytes_response.headers["Content-Type"].startswith("text/plain")


@pytest.mark.parametrize("missing", ["?step=stepone", "?index=0", ""])
def test_both_step_and_index_are_required(server_client, key, token, finished,
                                          missing):
    '''Two fields rather than one string: step=place index=10 and step=place1
    index=0 both render place10 and are two different nodes.'''
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/logs{missing}", token)

    assert response.status_code == 400


def test_a_node_that_has_not_started_is_not_ready(server_client, key, token,
                                                  job_archive, dispatcher):
    '''Transient: ask again. Carries Retry-After and names the kind.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 409
    assert slug(response) == "not-ready"
    assert response.get_json()["artifact_kind"] == "logs"
    assert response.headers["Retry-After"]


def test_a_running_node_redirects_to_the_live_tail(server, server_client, key,
                                                   token, job_archive, dispatcher):
    '''This deployment advertises logs.stream, so a running node is a stream
    rather than a refusal.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'running' WHERE job_id = ?", (job["id"],))

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 303
    assert "/stream/logs/" in response.headers["Location"]


def test_a_deployment_without_the_tail_refuses_it_permanently(tmp_path, monkeypatch):
    '''🔴 Permanent, so a client must not retry it -- and the archive still
    arrives when the node finishes, so this refuses the live read and not the
    log. Without it a deployment that will never serve a live log could only
    say "try later", for ever.'''
    import json as _json

    from siliconcompiler.remote import dpop
    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.ids import uuid7

    datadir = tmp_path / "quiet"
    datadir.mkdir()
    (datadir / "config.json").write_text(_json.dumps({"features": ["logs"]}))

    app = create_app(datadir)
    client = app.test_client()
    quiet_key = dpop.generate_key()
    quiet_token = login(client, quiet_key).get_json()["access_token"]

    assert client.get("/v1").get_json()["features"] == ["logs"]

    store = app.config["SC_STORE"]
    me = call(client, quiet_key, "GET", "/v1/me", quiet_token).get_json()["id"]
    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
        (job_id, me))
    store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                  "VALUES (?, 'place', '0', 'running')", (job_id,))

    response = call(client, quiet_key, "GET",
                    f"/v1/jobs/{job_id}/logs?step=place&index=0", quiet_token)

    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"
    assert response.get_json()["feature"] == "logs.stream"


def test_a_finished_node_whose_log_is_not_archived_yet_is_not_ready(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 Transient, not 404. The node is over and the job is not, so the
    archive may still be on its way -- and a 404 tells a client to stop asking
    about a log that is about to exist.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job["id"],))

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 409
    assert slug(response) == "not-ready"
    assert response.headers["Retry-After"]


def test_a_node_this_job_does_not_have(server_client, key, token, finished):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/logs?step=nowhere&index=0", token)

    assert response.status_code == 404


def test_one_row_per_kind_per_node_even_under_a_race(server, finished):
    '''🔴 The check before the insert is not enough and cannot be made enough.

    Indexing runs on whichever request thread gets there first, and a client
    polling its job while tailing two logs has three of them. Two that check
    together both pass -- so a real aes run came back with 38 bundles for 23
    nodes, and the portal showed one node owning "logs, bundle, bundle". The
    unique index is what actually decides.
    '''
    import sqlite3

    from siliconcompiler.remote.server.ids import uuid7

    store = server.config["SC_STORE"]
    existing = store.one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'bundle' "
        "AND step IS NOT NULL LIMIT 1", (finished["id"],))
    assert existing is not None

    # Exactly what a second thread would attempt, having passed _exists.
    with pytest.raises(sqlite3.IntegrityError):
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", content_hash, '
            "  location_id, storage_key, size_bytes, media_type, kind, "
            "  provenance) "
            "VALUES (?, ?, ?, ?, 'sha256:x', ?, 'k', 1, 'application/gzip', "
            "        'bundle', 'declared')",
            (str(uuid7()), finished["id"], existing["step"], existing["index"],
             existing["location_id"]))


def test_the_job_level_rows_are_protected_too(server, finished):
    '''SQLite counts NULLs as distinct in a unique index, which would leave
    exactly the rows with no node unprotected -- hence the coalesce.'''
    import sqlite3

    from siliconcompiler.remote.server.ids import uuid7

    store = server.config["SC_STORE"]
    existing = store.one(
        "SELECT * FROM artifacts WHERE job_id = ? AND step IS NULL LIMIT 1",
        (finished["id"],))
    assert existing is not None

    with pytest.raises(sqlite3.IntegrityError):
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", content_hash, '
            "  location_id, storage_key, size_bytes, media_type, kind, "
            "  provenance) "
            "VALUES (?, ?, NULL, NULL, 'sha256:x', ?, 'k', 1, 'text/plain', "
            "        ?, 'declared')",
            (str(uuid7()), finished["id"], existing["location_id"],
             existing["kind"]))


###########################
# The run's own log
###########################

def _only(items, kind, step=None):
    return [item for item in items
            if item["kind"] == kind and item["step"] == step]


def test_the_runs_own_job_log_is_indexed(server, server_client, key, token,
                                         job_archive, dispatcher):
    '''🔴 It never was. The glob was `job.*.log`, which matches the timestamped
    backups a re-run leaves and never `job.log` itself -- and on this server
    every job gets its own directory, so there are no backups. The pattern
    matched nothing, every time.'''
    def prepare(job_root, build_dir):
        (build_dir / "job.log").write_text("the flow ran\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    items = listing(server_client, key, token, job["id"])

    assert len(_only(items, "logs")) == 1
    assert _only(items, "logs")[0]["media_type"] == "text/plain"


def test_a_stale_backup_log_is_not_mistaken_for_this_run(
        server, server_client, key, token, job_archive, dispatcher):
    '''What the old glob would have picked: the oldest rotated backup, which is
    a previous run's log presented as this one's.'''
    def prepare(job_root, build_dir):
        (build_dir / "job.20200101-000000.log").write_text("a different run\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    assert not _only(listing(server_client, key, token, job["id"]), "logs")


def test_the_server_run_log_stands_in_when_the_flow_wrote_none(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 The case somebody is most likely to be looking at: the run died
    before SiliconCompiler installed its file handler, so there is no
    `job.log`, and the server's own run log is the only account there is.'''
    from siliconcompiler.remote.server.dispatch import RUN_LOG

    def prepare(job_root, build_dir):
        (job_root / RUN_LOG).write_text("Traceback (most recent call last):\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    items = _only(listing(server_client, key, token, job["id"]), "logs")

    assert len(items) == 1
    got = call(server_client, key, "GET",
               f"/v1/jobs/{job['id']}/artifacts/{items[0]['id']}", token)
    assert got.status_code == 303


def test_only_one_job_level_log_is_ever_indexed(
        server, server_client, key, token, job_archive, dispatcher):
    '''⚠️ An artifact is identified by `(job, kind, step, index)` and carries no
    name on the wire, so two job-level logs would reach a client as two objects
    it cannot tell apart -- the duplicate-looking listing this server has
    already produced once.'''
    from siliconcompiler.remote.server.dispatch import RUN_LOG

    def prepare(job_root, build_dir):
        (build_dir / "job.log").write_text("the flow ran\n")
        (job_root / RUN_LOG).write_text("and the batch job said this\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    assert len(_only(listing(server_client, key, token, job["id"]), "logs")) == 1


def test_the_job_level_log_is_named_for_the_job(
        server, server_client, key, token, job_archive, dispatcher):
    '''No node in the name, because there is no node -- rather than an empty
    segment where one would go.'''
    def prepare(job_root, build_dir):
        (build_dir / "job.log").write_text("the flow ran\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    item = _only(listing(server_client, key, token, job["id"]), "logs")[0]

    got = call(server_client, key, "GET",
               f"/v1/jobs/{job['id']}/artifacts/{item['id']}", token)
    fetched = server_client.get(got.headers["Location"])
    assert "gcd-job0-logs.log" in fetched.headers["Content-Disposition"]
