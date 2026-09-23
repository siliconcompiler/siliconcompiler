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


@pytest.fixture
def finished(server, server_client, key, token, job_archive, dispatcher):
    '''A job that ran to completion, with its results indexed.'''
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

    runspec.write_progress(node_root / runspec.PROGRESS_FILENAME, {
        "state": "completed",
        "started_at": "2026-09-22T10:00:00.000Z",
        "finished_at": "2026-09-22T10:01:00.000Z",
        "nodes": {f"{step}/0": {"state": "completed", "exit_code": 0,
                                "started_at": "2026-09-22T10:00:00.000Z",
                                "finished_at": "2026-09-22T10:00:30.000Z"}
                  for step in ("stepone", "steptwo")},
    })

    assert call(server_client, key, "GET", f"/v1/jobs/{job['id']}",
                token).get_json()["state"] == "completed"
    return job


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
    assert ("outputs", "stepone") in kinds
    assert ("reports", "steptwo") in kinds


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

    assert by_kind["manifest"] > by_kind["outputs"]
    # `outputs` has no number of its own, so it gets the deployment's floor.
    assert by_kind["outputs"] > "2026"


def test_inputs_are_not_shipped(server, server_client, key, token, finished):
    '''They are copies of the upstream node's outputs, which the caller is
    already getting from the upstream node.'''
    import tarfile

    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'outputs' LIMIT 1",
        (finished["id"],))
    path = server.config["SC_STORAGE"].artifact_path(row["storage_key"])

    with tarfile.open(path) as tar:
        names = tar.getnames()

    assert any(name.startswith("outputs") for name in names)
    assert not any(name.startswith("inputs") for name in names)


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

    # manifest, plus logs + reports + outputs for each of the two nodes.
    assert len(seen) == len(set(seen)) == 7


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
