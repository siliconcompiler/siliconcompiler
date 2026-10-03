import gzip
import io
import os
import sqlite3
import tarfile
import time
import uuid

import pytest

from conftest import call, login, slug
from test_server_jobs import FakeDispatcher, create, put, sized, stage, submit


pytest.importorskip("flask", reason="the server extra is not installed")


# Endpoints 20, 21 and 22. None carries bytes -- two answer 303 and one a
# listing -- which keeps an orchestrator's capacity off the size of what it stores.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def ran(server, server_client, key, token, job_archive, prepare=None,
        state="completed", error=None):
    '''Submit a job, leave what a run leaves, and let the poll index it.

    `prepare(job_root, build_dir)` runs before the job is read as terminal:
    the only window in which the indexer, which runs once, can see a file.
    The progress file is written directly, so the scheduler is not under test.
    '''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(
        call(server_client, key, "GET", "/v1/me", token).get_json()["id"], job["id"])
    node_root = root / "gcd" / "job0"
    for step in ("stepone", "steptwo"):
        work = node_root / step / "0"
        for sub in ("outputs", "reports", "inputs"):
            (work / sub).mkdir(parents=True, exist_ok=True)
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
    runspec.write_json(root / runspec.PROGRESS_FILENAME, progress)

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


def _fetch(client, key, token, job_id, item, query="", **kwargs):
    return call(client, key, "GET", f"/v1/jobs/{job_id}/artifacts/{item['id']}{query}",
                token, **kwargs)


def _follow(client, response):
    return client.get(response.headers["Location"].split("http://localhost", 1)[1])


def _item(items, kind, step):
    return next(item for item in items if item["kind"] == kind and item["step"] == step)


def _only(items, kind, step=None):
    return [item for item in items if item["kind"] == kind and item["step"] == step]


def _job(server, job_id):
    return server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (job_id,))


def _mark(server, item, **columns):
    sets = ", ".join(f"{name} = ?" for name in columns)
    server.config["SC_STORE"].execute(
        f"UPDATE artifacts SET {sets} WHERE id = ?", (*columns.values(), item["id"]))


def _members(server, row):
    with tarfile.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"])) as tar:
        return {member.name: member for member in tar.getmembers()}


def test_a_finished_run_is_indexed(server_client, key, token, finished):
    '''Per node: its log; its `node` archive, indexed as the node finishes; its
    reports (🔴 a deliberate second copy -- kilobytes, still fetchable when the
    archive is over `max_download_bytes`); and its manifest (🔴 its record and
    metrics). Never `outputs`, a second copy of the large half.'''
    kinds = {(item["kind"], item["step"])
             for item in listing(server_client, key, token, finished["id"])}

    assert ("manifest", None) in kinds
    for step in ("stepone", "steptwo"):
        for kind in ("logs", "node", "reports", "manifest"):
            assert (kind, step) in kinds, (kind, step)
    assert not [k for k, _ in kinds if k == "outputs"]


def test_every_required_member_is_published(server_client, key, token, finished):
    '''🔴 `deleted_cause` (an enum) and `deleted_reason` (prose) say whether the
    system or a person took the bytes. Nothing is approval-gated (surface
    D309), so nothing can be asked for, and no artifact carries a portal URL.'''
    for item in listing(server_client, key, token, finished["id"]):
        for member in ("id", "step", "index", "kind", "media_type", "size_bytes",
                       "digest", "created_at", "retained_until", "deleted_at",
                       "deleted_cause", "deleted_reason", "fetchable", "can_request_access"):
            assert member in item, member
        assert item["digest"].startswith("sha256:")
        assert item["can_request_access"] is False
        for absent in ("storage_key", "expires_at", "blocked_by", "access_request_url"):
            assert absent not in item
        assert not any("portal" in str(value) for value in item.values()), item


def test_retention_is_per_kind_and_the_job_floor_is_only_a_floor(
        server_client, key, token, finished):
    '''`node` has no number of its own, so it gets the deployment's floor.'''
    by_kind = {item["kind"]: item["retained_until"]
               for item in listing(server_client, key, token, finished["id"])}

    assert by_kind["manifest"] > by_kind["node"] > "2026"
    assert by_kind["logs"][:10] == by_kind["manifest"][:10]


def test_a_node_archive_is_its_directory_without_inputs_or_uploads(server, finished):
    '''Relative to the node's directory, so a client unpacks it in place.
    `inputs/` is the upstream node's outputs, in that node's archive;
    `sc_collected_files/` is what the client uploaded and deleted its copy of.'''
    job = _job(server, finished["id"])
    work = server.config["SC_JOBS"].job_root(job["user_id"], job["id"]) / "gcd/job0/stepone/0"
    (work / "sc_collected_files").mkdir(parents=True, exist_ok=True)
    (work / "sc_collected_files" / "gcd.v").write_text("module m;")
    server.config["SC_STORE"].execute("DELETE FROM artifacts WHERE job_id = ?", (job["id"],))
    server.config["SC_JOBS"]._index(job)

    names = _members(server, server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'node' AND step = 'stepone'",
        (job["id"],)))

    assert "outputs/gcd.pkg.json" in names
    assert "sc_stepone_0.log" in names
    for left_out in ("inputs", "sc_collected_files"):
        assert not any(left_out in name.split("/") for name in names)


def test_indexing_twice_does_not_duplicate_the_listing(server, server_client,
                                                       key, token, finished):
    before = len(listing(server_client, key, token, finished["id"]))

    server.config["SC_JOBS"]._index(_job(server, finished["id"]))

    assert len(listing(server_client, key, token, finished["id"])) == before


def test_a_job_that_ran_nothing_lists_only_what_was_sent(server_client, key, token,
                                                         job_archive, dispatcher):
    '''A legal answer, not an error: the upload, as the digest submit checked,
    and the server's record of what it did with it.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    items = listing(server_client, key, token, job["id"])
    assert [(item["kind"], item["step"]) for item in items] == [("input", None),
                                                                ("staging", None)]
    assert items[0]["digest"] == digest and items[0]["size_bytes"] == size


def test_the_listing_filters_by_kind_step_and_index(server_client, key, token, finished):
    '''An absent kind is a true answer (this deployment stores `node`, not
    `outputs`); an unknown one is refused.'''
    for kind in ("logs", "reports"):
        assert {item["kind"] for item in listing(server_client, key, token, finished["id"],
                                                 f"?kind={kind}")} == {kind}
    assert listing(server_client, key, token, finished["id"], "?kind=outputs") == []
    one = listing(server_client, key, token, finished["id"], "?step=stepone&index=0")
    assert {item["step"] for item in one} == {"stepone"}

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts?kind=souvenirs", token)
    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_the_next_page_keeps_the_query_encoded(server):
    '''One builder for every collection's `Link`: each value encoded, a repeat
    kept, the cursor replaced -- `step=a b&c` is one value.'''
    from siliconcompiler.remote.server.routes import next_page

    with server.test_request_context("/v1/jobs/J/artifacts?step=a%20b%26c&kind=logs"
                                     "&kind=reports&cursor=old"):
        link = next_page("/v1/jobs/J/artifacts", "new")

    assert link == ('</v1/jobs/J/artifacts?step=a+b%26c&kind=logs&kind=reports'
                    '&cursor=new>; rel="next"')


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
        response = call(server_client, key, "GET", link.split(">", 1)[0].lstrip("<"), token)

    # The job's manifest and upload; per node a log, manifest, reports, node
    # archive and input; the job's staging; diagnostics for the job and each node.
    assert len(seen) == len(set(seen)) == 16


def test_a_strangers_listing_is_a_404(server_client, finished):
    from siliconcompiler.remote import dpop

    other_key = dpop.generate_key()
    other = login(server_client, other_key, subject="machine:1001").get_json()["access_token"]

    assert call(server_client, other_key, "GET", f"/v1/jobs/{finished['id']}/artifacts",
                other).status_code == 404


def test_a_deleted_jobs_subresources_are_gone(server_client, key, token, finished):
    '''The job stays readable with deleted_at set and its subresources 404.'''
    call(server_client, key, "DELETE", f"/v1/jobs/{finished['id']}", token)

    assert call(server_client, key, "GET", f"/v1/jobs/{finished['id']}/artifacts",
                token).status_code == 404
    assert call(server_client, key, "GET", f"/v1/jobs/{finished['id']}",
                token).status_code == 200


def test_every_artifact_is_a_303_to_its_gzip_on_a_signed_route(server_client, key, token,
                                                               finished):
    '''Every kind, the manifest and logs included. `diagnostics` is gzipped
    too, and read only in the portal.'''
    items = listing(server_client, key, token, finished["id"])
    assert {item["kind"] for item in items} >= {"manifest", "logs", "staging", "reports",
                                                "node"}

    for item in [item for item in items if item["fetchable"]]:
        response = _fetch(server_client, key, token, finished["id"], item)
        assert response.status_code == 303
        assert "/storage/artifact/" in response.headers["Location"]
        assert "sig=" in response.headers["Location"]
        body = _follow(server_client, response)
        assert body.status_code == 200
        assert len(body.data) == item["size_bytes"], item["kind"]
        assert body.data[:2] == b"\x1f\x8b", item["kind"]
        assert item["media_type"] == "application/gzip", item["kind"]


def test_a_server_on_http_issues_only_http_urls(server, server_client, key, token,
                                                finished):
    '''🔴 Contract rule 5: one scheme throughout -- the artifact `303`, the
    upload grant and endpoint 6's sign-in link.'''
    server.config["SC_CONFIG"]._values["web_url_base"] = "http://localhost"
    item = listing(server_client, key, token, finished["id"])[0]
    job = create(server_client, key, token, jobname="job1").get_json()

    urls = [
        _fetch(server_client, key, token, finished["id"], item).headers["Location"],
        call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant", token,
             json={"size_bytes": 10, "digest": "sha256:" + "0" * 64}).get_json()["url"],
        call(server_client, key, "POST", "/v1/auth/browser", token,
             json={"job_id": job["id"]}).get_json()["url"],
    ]

    assert all(url.startswith("http://localhost/") for url in urls), urls


def test_the_bytes_need_a_live_download_signature(server_client, key, token, finished):
    '''Unsigned, expired, or an upload grant's signature -- a different message
    prefix, so a PUT grant is never a GET of another job's outputs.'''
    storage = server_client.application.config["SC_STORAGE"]
    item = listing(server_client, key, token, finished["id"])[0]
    target = _fetch(server_client, key, token, finished["id"], item) \
        .headers["Location"].split("http://localhost", 1)[1]
    expires = target.split("expires=")[1].split("&")[0]
    soon = int(time.time()) + 300
    route = f"/storage/artifact/{finished['id']}/{item['id']}"

    for forged in (route,
                   target.replace(f"expires={expires}", f"expires={int(time.time()) - 10}"),
                   f"{route}?expires={soon}&sig={storage.sign_upload(item['id'], 1000, soon)}"):
        assert server_client.get(forged).status_code == 400, forged


def test_a_deleted_artifact_is_a_404_and_its_node_is_not_approved(
        server, server_client, key, token, finished, caplog):
    '''Nothing is left to be entitled to, and the row stays listed. 🔴 Handing
    its node archive over would undo the deletion (entitlements D41); the
    state should not exist -- a node is reaped whole -- so an operator is told,
    once.'''
    items = listing(server_client, key, token, finished["id"])
    log, node = _item(items, "logs", "stepone"), _item(items, "node", "stepone")
    _mark(server, log, deleted_at="2026-09-22T00:00:00.000Z",
          deleted_by=_job(server, finished["id"])["user_id"], deleted_reason="test")

    assert _fetch(server_client, key, token, finished["id"], log).status_code == 404
    still = [a for a in listing(server_client, key, token, finished["id"])
             if a["id"] == log["id"]]
    assert still and still[0]["deleted_at"] and still[0]["fetchable"] is False

    with caplog.at_level("ERROR", logger="sc-server"):
        first = _fetch(server_client, key, token, finished["id"], node)
        _fetch(server_client, key, token, finished["id"], node)
    assert slug(first) == "artifact-not-approved"
    assert sum("deleted on its own" in record.message for record in caplog.records) == 1


def test_past_its_retention_and_not_yet_swept_is_still_fetchable(
        server, server_client, key, token, finished):
    '''⚠️ Retention passing is not a rung of the ladder: the reaper follows it
    by setting `deleted_at`, and until then the bytes are here.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _mark(server, item, retained_until="2020-01-01T00:00:00.000Z")

    assert next(i for i in listing(server_client, key, token, finished["id"])
                if i["id"] == item["id"])["fetchable"] is True
    assert _fetch(server_client, key, token, finished["id"], item).status_code == 303


def test_an_artifact_still_being_described_is_not_ready_nor_is_its_node(
        server, server_client, key, token, finished):
    '''🔴 The live bug: a permanent `403` told a client to abandon an artifact
    about to be fetchable. Listed once described (surface D308), so a client
    fetching at `terminal` misses nothing; its `node` archive is held back,
    refused as its worst member is (D120): transient, not a blanket
    `artifact-not-approved`.'''
    items = listing(server_client, key, token, finished["id"])
    log, node = _item(items, "logs", "stepone"), _item(items, "node", "stepone")
    other = _item(items, "node", "steptwo")
    _mark(server, log, provenance="pending")

    listed = {i["id"] for i in listing(server_client, key, token, finished["id"])}
    assert log["id"] not in listed and node["id"] not in listed
    assert other["id"] in listed

    for item in (log, node):
        response = _fetch(server_client, key, token, finished["id"], item)
        assert (response.status_code, slug(response)) == (409, "not-ready")
        assert response.get_json()["artifact_kind"] == item["kind"]
        assert response.headers["Retry-After"]


def test_a_withheld_artifact_is_not_approved_nor_is_its_node(
        server, server_client, key, token, finished):
    '''The per-object gate, with no `resource_kind` forced onto it; row 4:
    handing the node archive over would hand over the withheld member.'''
    items = listing(server_client, key, token, finished["id"])
    log, node = _item(items, "logs", "stepone"), _item(items, "node", "stepone")
    _mark(server, log, withheld_at="2026-09-25T00:00:00.000Z",
          withheld_by=_job(server, finished["id"])["user_id"])

    response = _fetch(server_client, key, token, finished["id"], log)
    assert (response.status_code, slug(response)) == (403, "artifact-not-approved")
    assert "resource_kind" not in response.get_json()

    relisted = {i["id"]: i for i in listing(server_client, key, token, finished["id"])}
    assert relisted[node["id"]]["fetchable"] is False
    assert slug(_fetch(server_client, key, token, finished["id"], node)) == \
        "artifact-not-approved"


def test_a_withheld_member_is_worse_than_a_pending_one():
    from siliconcompiler.remote.server.outputs import artifacts

    assert artifacts.worst([None, "not-ready", "artifact-not-approved"]) == \
        "artifact-not-approved"
    assert artifacts.worst(["not-ready", "entitlement-denied"]) == "entitlement-denied"
    assert artifacts.worst([None, None]) is None


def _ceiling(server, bytes_allowed):
    server.config["SC_CONFIG"].limits["max_download_bytes"] = bytes_allowed


@pytest.mark.parametrize("over,status", [(1, 403), (0, 303), (None, 303)],
                         ids=["over", "at", "unlimited"])
def test_max_download_bytes_is_a_real_inclusive_limit(server, server_client, key, token,
                                                      finished, over, status):
    '''🔴 A refusal, not advice a client applies to itself; inclusive, and null
    is unlimited. D117: `403 download-too-large` naming its published key, not
    `429 limit-exceeded`; it never clears, so no `Retry-After`.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, None if over is None else item["size_bytes"] - over)

    response = _fetch(server_client, key, token, finished["id"], item)

    assert response.status_code == status
    if status == 403:
        assert slug(response) == "download-too-large"
        assert response.get_json()["limit"] == "max_download_bytes"
        assert "Retry-After" not in response.headers


def test_no_query_parameter_or_header_lifts_the_ceiling(
        server, server_client, key, token, finished):
    '''🔴 No API override: the way past it is the portal, not a flag.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, 1)

    for query in ("?force=1", "?max_download_bytes=0"):
        assert _fetch(server_client, key, token, finished["id"], item,
                      query).status_code == 403
    assert _fetch(server_client, key, token, finished["id"], item,
                  headers={"X-Max-Download-Bytes": "0",
                           "Range": "bytes=0-100"}).status_code == 403


def test_the_ceiling_that_binds_is_this_accounts_and_not_the_deployments(
        server, server_client, key, token, finished):
    '''🔴 The one limit a `user_limits` row may override.'''
    from siliconcompiler.remote.server.identity import accounts

    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, 1)
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    accounts.set_limit(server.config["SC_STORE"], me, "max_download_bytes",
                       -1, me)          # -1 is the table's spelling of unlimited

    assert _fetch(server_client, key, token, finished["id"], item).status_code == 303


def test_a_log_is_the_same_bytes_and_therefore_the_same_ceiling(
        server, server_client, key, token, finished):
    '''`/logs` names the artifact endpoint 22 serves, so it is no way around it.'''
    _ceiling(server, 1)

    response = _fetch(server_client, key, token, finished["id"],
                      {"id": _ended_stream(server_client, key, token, finished["id"])})

    assert (response.status_code, slug(response)) == (403, "download-too-large")
    assert response.get_json()["limit"] == "max_download_bytes"


def _ended_stream(server_client, key, token, job_id):
    '''Open a finished node's stream; the `logs` artifact its `node_state` names.'''
    import json

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job_id}/logs?step=stepone&index=0", token)
    assert response.status_code == 303
    body = _follow(server_client, response).data.decode()
    events = [block for block in body.split("\n\n") if "event: node_state" in block]
    data = next(line for line in events[0].splitlines() if line.startswith("data:"))
    state = json.loads(data[5:])
    assert state["terminal"] is True
    assert "event: end" in body
    return state["artifact_id"]


def test_a_terminal_nodes_stream_ends_at_once_naming_its_archive(
        server_client, key, token, finished):
    '''🔴 `/logs` is live only; a finished node's log is its gzipped `logs`
    artifact, which carries nothing but the node's logs.'''
    artifact_id = _ended_stream(server_client, key, token, finished["id"])
    response = _follow(server_client, _fetch(server_client, key, token, finished["id"],
                                             {"id": artifact_id}))

    assert response.headers["Content-Type"].startswith("application/gzip")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Disposition"].startswith("attachment")
    with tarfile.open(fileobj=io.BytesIO(response.data), mode="r:gz") as tar:
        texts = [tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()]
    assert b"stepone ran\n" in texts


def test_a_node_that_has_not_started_is_not_ready(server_client, key, token,
                                                  job_archive, dispatcher):
    '''Transient: carries Retry-After and names the kind.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/logs?step=stepone&index=0", token)

    assert (response.status_code, slug(response)) == (409, "not-ready")
    assert response.get_json()["artifact_kind"] == "logs"
    assert response.headers["Retry-After"]


def test_a_finished_node_with_no_log_is_not_found(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 A node is completed only once indexed, so it never will have one.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job["id"],))

    assert call(server_client, key, "GET", f"/v1/jobs/{job['id']}/logs?step=stepone&index=0",
                token).status_code == 404


def test_a_node_log_names_a_node_this_job_has(server_client, key, token, finished):
    '''Both step and index, or neither: `place`/`10` and `place1`/`0` both
    render `place10`.'''
    logs = f"/v1/jobs/{finished['id']}/logs"

    assert call(server_client, key, "GET", f"{logs}?step=nowhere&index=0",
                token).status_code == 404
    for half in ("?step=stepone", "?index=0"):
        assert call(server_client, key, "GET", logs + half, token).status_code == 400


def _insert(store, like, **values):
    '''Another artifact row at ``like``'s coordinates, as a racing indexer would.'''
    row = {"id": str(uuid.uuid4()), "job_id": like["job_id"], "step": like["step"],
           "index": like["index"], "digest": "sha256:x", "location_id": like["location_id"],
           "storage_key": "k", "size_bytes": 1, "media_type": "application/gzip",
           "kind": like["kind"], "provenance": "declared", **values}
    columns = ", ".join(f'"{name}"' for name in row)
    store.execute(f"INSERT INTO artifacts ({columns}) VALUES ({', '.join('?' * len(row))})",
                  tuple(row.values()))


@pytest.mark.parametrize("where", ["kind = 'node' AND step IS NOT NULL",
                                   "step IS NULL AND kind <> 'input'"],
                         ids=["node", "job-level"])
def test_one_row_per_kind_per_node_even_under_a_race(server, finished, where):
    '''🔴 Indexing runs on whichever request thread gets there first, so a
    check before the insert cannot hold (a real aes run listed 38 node
    archives for 23 nodes): the unique index decides, coalesced so a row with
    no node, NULL in SQLite's eyes, is protected too.'''
    store = server.config["SC_STORE"]
    existing = store.one(f"SELECT * FROM artifacts WHERE job_id = ? AND {where} LIMIT 1",
                         (finished["id"],))

    with pytest.raises(sqlite3.IntegrityError):
        _insert(store, existing)


def test_uploads_are_numbered_and_the_number_is_in_the_key(server, finished):
    '''🔴 One per UPLOAD (database D101); a CHECK ties the ordinal to
    job-level `input` exactly.'''
    store = server.config["SC_STORE"]
    first = store.one("SELECT * FROM artifacts WHERE job_id = ? AND kind = 'input' "
                      "AND step IS NULL", (finished["id"],))
    assert first["upload_seq"] == 1

    _insert(store, first, upload_seq=2)
    for refused in ({"upload_seq": 2},                       # the same upload twice
                    {"upload_seq": None},                    # a job-level input, unnumbered
                    {"kind": "logs", "upload_seq": 3},       # a number on anything else
                    {"upload_seq": 3, "step": "stepone", "index": "0"}):   # or a node's
        with pytest.raises(sqlite3.IntegrityError):
            _insert(store, first, **refused)


def test_a_node_input_is_what_it_was_handed_and_no_member_of_its_archive(
        server_client, key, token, finished):
    '''The node archive leaves `inputs/` out, so `input` gates nothing there.'''
    items = listing(server_client, key, token, finished["id"], "?kind=input&step=stepone")

    assert [(item["step"], item["index"]) for item in items] == [("stepone", "0")]
    assert items[0]["media_type"] == "application/gzip" and items[0]["fetchable"]


def _collected(server, finished, step, plant):
    '''Lay out node ``step``/0 with ``plant(node, upstream)`` and collect it:
    each archive's members, by kind. ``upstream`` is stepone's
    `outputs/gcd.vg`.'''
    from siliconcompiler.remote.server.outputs import artifacts

    store = server.config["SC_STORE"]
    job = _job(server, finished["id"])
    root = server.config["SC_JOBS"].job_root(job["user_id"], job["id"])
    upstream = root / "gcd" / "job0" / "stepone" / "0" / "outputs" / "gcd.vg"
    upstream.write_text("module gcd; endmodule\n")
    node = root / "gcd" / "job0" / step / "0"
    node.mkdir(parents=True)
    plant(node, upstream)
    artifacts.collect_node(store, server.config["SC_STORAGE"], server.config["SC_CONFIG"],
                           job, root, step, "0")
    return {row["kind"]: _members(server, row) for row in store.all(
        "SELECT * FROM artifacts WHERE job_id = ? AND step = ?", (job["id"], step))}


@pytest.mark.parametrize("hard", [False, True], ids=["symlinked", "hard-linked"])
def test_a_pass_through_nodes_archive_holds_one_link_to_its_home(server, finished, hard):
    '''🔴 `outputs/x` -> `inputs/x` -> upstream `outputs/x`, as
    `link_symlink_copy` makes it, is one relative link to the upstream file in
    both archives (database D142) -- read off a symlink, found by inode for a
    hard link. Nothing is copied.'''
    def plant(node, upstream):
        (node / "inputs").mkdir()
        (node / "outputs").mkdir()
        (node / "sc_passed_0.log").write_text("log\n")
        if hard:
            os.link(upstream, node / "inputs" / "gcd.vg")
            os.link(node / "inputs" / "gcd.vg", node / "outputs" / "gcd.vg")
        else:
            (node / "inputs" / "gcd.vg").symlink_to(upstream)
            (node / "outputs" / "gcd.vg").symlink_to("../inputs/gcd.vg")

    members = _collected(server, finished, "passed", plant)

    for kind, name in (("node", "outputs/gcd.vg"), ("input", "inputs/gcd.vg")):
        assert members[kind][name].issym(), (kind, members[kind][name].type)
        assert members[kind][name].linkname == "../../../stepone/0/outputs/gcd.vg"


def test_a_hard_linked_pair_in_one_node_is_a_tar_hard_link(server, finished):
    '''The bytes once, and a hard link to their first appearance.'''
    def plant(node, upstream):
        (node / "outputs").mkdir()
        (node / "outputs" / "a.vg").write_text("module a; endmodule\n")
        os.link(node / "outputs" / "a.vg", node / "outputs" / "b.vg")

    members = _collected(server, finished, "twice", plant)["node"]

    assert members["outputs/a.vg"].isfile()
    assert members["outputs/b.vg"].islnk()
    assert members["outputs/b.vg"].linkname == "outputs/a.vg"


def test_a_file_with_a_name_outside_the_job_is_dropped(server, finished, tmp_path):
    '''🔴 More links than names in the job's tree means a name outside it -- PDK
    data hard-linked in -- so it is a link leaving the job: never stored.'''
    outside = tmp_path / "pdk.lib"
    outside.write_text("the foundry's own file\n")

    def plant(node, upstream):
        (node / "outputs").mkdir()
        (node / "outputs" / "mine.v").write_text("module mine; endmodule\n")
        try:
            os.link(outside, node / "outputs" / "pdk.lib")
        except OSError:
            pytest.skip("the job tree and tmp_path are on different filesystems")

    members = _collected(server, finished, "borrowed", plant)["node"]

    assert "outputs/pdk.lib" not in members
    assert members["outputs/mine.v"].isfile()


def test_a_name_the_next_node_adds_while_a_node_is_archived_is_inside_the_job(
        server, finished, monkeypatch):
    '''🔴 The race that lost a compiled testbench: the next node starts, and
    hard-links this node's outputs into its inputs, while this one is
    archived. That name is inside the job, and the file is stored.'''
    from siliconcompiler.remote import links

    paths = {}

    def plant(node, upstream):
        (node / "outputs").mkdir()
        paths["built"] = node / "outputs" / "tb.vexe"
        paths["built"].write_bytes(b"\x7fELF the compiled testbench")
        paths["inputs"] = node.parents[1] / "simulate" / "0" / "inputs"
        paths["inputs"].mkdir(parents=True)

    walk = links.Homes._walk

    def walk_then_start_the_next_node(self):
        walk(self)
        if not (paths["inputs"] / "tb.vexe").exists():
            os.link(paths["built"], paths["inputs"] / "tb.vexe")

    monkeypatch.setattr(links.Homes, "_walk", walk_then_start_the_next_node)

    members = _collected(server, finished, "compile", plant)["node"]

    assert members["outputs/tb.vexe"].isfile()
    assert members["outputs/tb.vexe"].size == paths["built"].stat().st_size


def test_a_link_out_of_the_job_is_never_read_nor_stored(server, finished, tmp_path):
    '''🔴 Surface D133: following it packs the host's bytes as the job's;
    storing it hands out the host's path (D159).'''
    secret = tmp_path / "host-secret"
    secret.write_text("the host's own file\n")

    def plant(node, upstream):
        (node / "inputs").mkdir()
        (node / "sc_outward_0.log").write_text("log\n")
        (node / "inputs" / "stolen").symlink_to(secret)

    members = _collected(server, finished, "outward", plant)["input"].values()

    assert not any(m.name.endswith("stolen") for m in members)
    assert not any(str(secret) in (m.linkname or "") for m in members)


def test_a_log_that_is_a_link_out_is_not_indexed(server, finished, tmp_path):
    '''The same attack on the files indexed one by one: not as the bytes, and
    not as a link naming the host's path.'''
    secret = tmp_path / "host-secret"
    secret.write_text("the host's own file\n")

    def plant(node, upstream):
        (node / "outputs").mkdir()
        (node / "sc_linklog_0.log").symlink_to(secret)
        (node / "outputs" / "gcd.pkg.json").symlink_to(secret)

    members = _collected(server, finished, "linklog", plant)

    assert set(members) == {"node"}
    assert "sc_linklog_0.log" not in members["node"]
    assert all(not member.isfile() for member in members["node"].values())


def _uploads(server, job_id):
    return server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ? AND upload_seq IS NOT NULL "
        "ORDER BY upload_seq", (job_id,))


def test_an_upload_refused_for_its_digest_stays_where_the_grant_put_it(
        server, server_client, key, token, job_archive, dispatcher):
    '''A refusal of the request: the job waits and its upload is kept; the
    right bytes, sent again, are recorded under the hash storage holds.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                 token, json=sized(size, digest)).get_json()
    put(server_client, grant, b"\0" * size)

    assert slug(submit(server_client, key, token, job["id"])) == "upload-digest-mismatch"
    assert not _uploads(server, job["id"])
    assert server.config["SC_STORAGE"].stat_upload(job["id"])[0] == size

    put(server_client, grant, open(archive, "rb").read())
    submit(server_client, key, token, job["id"])
    kept, = _uploads(server, job["id"])
    assert kept["digest"] == digest and kept["upload_seq"] == 1


def test_an_upload_refused_for_a_private_value_is_deleted_and_the_reason_kept(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 A private dataroot's value is not kept (surface D308): the job, its
    reason, and the member and hash it names remain.'''
    from siliconcompiler.remote.server.errors import ProblemError

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    kept, = _uploads(server, job["id"])
    stored = server.config["SC_STORAGE"].artifact_path(kept["storage_key"])
    assert stored.is_file()

    server.config["SC_JOBS"]._refuse(_job(server, job["id"]), ProblemError(
        "archive-rejected", reason="unrequested_member",
        keypath=["library", "acme", "dataroot", "cells"],
        detail="sc_collected_files/cells.lef (sha256:abc) is under the private dataroot "
               "library,acme,dataroot,cells"))

    assert _uploads(server, job["id"]) == [] and not stored.exists()
    reason = server.config["SC_STORE"].one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? AND to_state = "
        "'rejected'", (job["id"],))["reason"]
    assert "cells.lef" in reason and "sha256:abc" in reason


def _job_logs(server, server_client, key, token, job_archive, **files):
    '''Run with ``files`` (`job_log`, `backup`, `run_log`) left behind; the
    job and its listing.'''
    from siliconcompiler.remote.server.running.dispatch import RUN_LOG

    def prepare(job_root, build_dir):
        for name, path in (("job_log", build_dir / "job.log"),
                           ("backup", build_dir / "job.20200101-000000.log"),
                           ("run_log", job_root / RUN_LOG)):
            if name in files:
                path.write_text(files[name])

    job = ran(server, server_client, key, token, job_archive, prepare)
    return job, listing(server_client, key, token, job["id"])


def test_the_job_level_log_is_the_runs_job_log_alone(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 It was never indexed: the glob `job.*.log` matched only re-run backups.
    One job-level log, since an artifact carries no name on the wire, and
    SiliconCompiler's alone -- this server's record is `staging` and
    `diagnostics` (surface D295) -- named for the job, with no node segment.'''
    job, items = _job_logs(server, server_client, key, token, job_archive,
                           job_log="the flow ran\n", run_log="and the batch job said this\n")

    item, = _only(items, "logs")
    assert item["media_type"] == "application/gzip"
    row = server.config["SC_STORE"].one("SELECT storage_key FROM artifacts WHERE id = ?",
                                        (item["id"],))
    with gzip.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"]), "rt") as f:
        assert f.read() == "the flow ran\n"
    fetched = server_client.get(_fetch(server_client, key, token, job["id"],
                                       item).headers["Location"])
    assert "gcd-job0-logs.log" in fetched.headers["Content-Disposition"]


def test_the_runners_own_log_is_the_operators_and_a_backup_is_nobodys(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 A run that died before `job.log` leaves only the runner's log: the
    operators' `diagnostics` (surface D295), listed, never fetchable over the
    API. A stale rotated backup is a previous run's log, never this one's.'''
    job, items = _job_logs(server, server_client, key, token, job_archive,
                           backup="a different run\n",
                           run_log="Traceback (most recent call last):\n")

    assert not _only(items, "logs")
    held, = _only(items, "diagnostics")
    assert held["fetchable"] is False
    got = _fetch(server_client, key, token, job["id"], held)
    assert (got.status_code, slug(got)) == (403, "artifact-not-approved")
    assert "run.log" in _members(server, server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE id = ?", (held["id"],)))


def test_a_deletion_says_who_took_the_bytes(server, server_client, key, token, finished):
    '''🔴 `deleted_by` decides `deleted_cause` and is not on the wire (it names
    a user): NULL is the reaper, set is a person. ✅ The reason is synthesized,
    naming who acted and never the device or an id (surface §17, §19); a job
    carries no `deleted_cause` (D279).'''
    from siliconcompiler.remote.server.outputs import artifacts

    assert all(item["deleted_cause"] is None
               for item in listing(server_client, key, token, finished["id"]))

    call(server_client, key, "DELETE", f"/v1/jobs/{finished['id']}", token)

    after = server.config["SC_STORE"].all("SELECT * FROM artifacts WHERE job_id = ?",
                                          (finished["id"],))
    assert after and all(artifacts.cause(row) == "removed" for row in after)
    assert {row["deleted_reason"] for row in after} == {"deleted by its owner"}
    read = call(server_client, key, "GET", f"/v1/jobs/{finished['id']}", token).get_json()
    assert read["deleted_reason"] == "deleted by its owner" and "deleted_cause" not in read
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    assert me not in read["deleted_reason"]
