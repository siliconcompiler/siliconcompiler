import time

import pytest

from conftest import call, login, slug
from test_server_jobs import FakeDispatcher, create, stage, submit


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

    from siliconcompiler.remote.server.running import runspec

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
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, progress)

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
    # A node archive per node, indexed as that node finishes -- which is what lets a
    # client take a node's results while the rest of the flow runs on.
    assert ("node", "stepone") in kinds
    assert ("node", "steptwo") in kinds
    # 🔴 And the reports on their own, which IS a second copy of bytes the
    # node archive holds. A node's reports are kilobytes and its node archive is often
    # gigabytes, and above `max_download_bytes` the node archive is not fetched at
    # all while these still are.
    assert ("reports", "stepone") in kinds
    assert ("reports", "steptwo") in kinds
    # 🔴 And each node's own manifest, bound to the node. It is what carries
    # that node's record and metrics, so a deployment that withholds the
    # archives can still hand over the part that says what happened.
    assert ("manifest", "stepone") in kinds
    assert ("manifest", "steptwo") in kinds
    # `outputs` is still not produced: that WOULD be a second copy of the
    # large half.
    assert not [k for k, _ in kinds if k == "outputs"]


def test_every_required_member_is_published(server_client, key, token, finished):
    for item in listing(server_client, key, token, finished["id"]):
        for member in ("id", "step", "index", "kind", "media_type", "size_bytes",
                       "digest", "created_at", "retained_until", "deleted_at",
                       # 🔴 Two members, and without them `deleted_at` cannot
                       # be read: retention lapsing ends in one too, so the
                       # column alone cannot say whether the system or a
                       # person took the bytes. One is a closed enum a client
                       # branches on; the other is prose a person reads.
                       "deleted_cause", "deleted_reason",
                       "fetchable", "can_request_access"):
            assert member in item, member
        assert item["digest"].startswith("sha256:")
        assert "storage_key" not in item and "expires_at" not in item
        # 🔴 Nothing here is approval-gated, so there is never anything to ask
        # for, a fully fetchable `node` included (surface D309); and no
        # artifact carries a portal URL: an approval request's page is asked
        # for at POST /v1/auth/browser.
        assert item["can_request_access"] is False
        assert "blocked_by" not in item
        assert "access_request_url" not in item
        assert not any("portal" in str(value) for value in item.values()), item


def test_retention_is_per_kind_and_the_job_floor_is_only_a_floor(
        server_client, key, token, finished):
    '''A manifest and the outputs beside it go at different times, so one
    number cannot answer for a job.'''
    items = listing(server_client, key, token, finished["id"])
    by_kind = {item["kind"]: item["retained_until"] for item in items}

    assert by_kind["manifest"] > by_kind["node"]
    # `node archive` has no number of its own, so it gets the deployment's floor --
    # and a node archive may never outlive its contents.
    assert by_kind["node"] > "2026"
    # Same retention rule, so the same day; they are written moments apart.
    assert by_kind["logs"][:10] == by_kind["manifest"][:10]


def test_a_node_archive_holds_its_node_and_leaves_out_its_inputs(
        server, server_client, key, token, finished):
    '''A node's node archive is that node's working directory. `inputs/` is left out
    because it is copies of the upstream node's outputs, which the caller is
    getting from the upstream node's own node archive.'''
    import tarfile

    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'node' "
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

    row = store.one("SELECT * FROM artifacts WHERE job_id = ? AND kind = 'node' "
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


def test_a_job_that_ran_nothing_lists_only_what_was_sent(server_client, key, token,
                                                         job_archive, dispatcher):
    '''Nothing the run produced is a legal answer, not an error -- and what
    went in is still there to look at.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    items = listing(server_client, key, token, job["id"])
    # What was sent, and the server's record of what it did with it.
    assert [(item["kind"], item["step"]) for item in items] == [("input", None),
                                                                ("staging", None)]
    # The digest the submit checked, as the hash of the bytes it kept.
    assert items[0]["digest"] == digest and items[0]["size_bytes"] == size


###########################
# 21. the listing
###########################

def test_the_listing_filters_by_kind_step_and_index(server_client, key, token,
                                                    finished):
    logs = listing(server_client, key, token, finished["id"], "?kind=logs")
    assert {item["kind"] for item in logs} == {"logs"}

    reports = listing(server_client, key, token, finished["id"], "?kind=reports")
    assert {item["kind"] for item in reports} == {"reports"}

    # A kind that is absent was never indexed here, which is a true answer and
    # not an error: this deployment stores a node archive instead.
    assert listing(server_client, key, token, finished["id"], "?kind=outputs") == []

    one = listing(server_client, key, token, finished["id"],
                  "?step=stepone&index=0")
    assert {item["step"] for item in one} == {"stepone"}


def test_an_unknown_kind_is_refused(server_client, key, token, finished):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts?kind=souvenirs", token)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_the_next_page_keeps_the_query_encoded(server):
    '''One builder for every collection's `Link`: each value encoded, a
    repeat kept, and the cursor replaced -- `step=a b&c` is one value.'''
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
        response = call(server_client, key, "GET",
                        link.split(">", 1)[0].lstrip("<"), token)

    # The job's manifest and its upload, plus a log, a manifest, a reports, a
    # node archive and its inputs for each of the two nodes; and the server's
    # records -- the job's staging, and the operators' diagnostics for the job
    # and each node the scheduler ran.
    assert len(seen) == len(set(seen)) == 16


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


def test_a_server_on_http_issues_only_http_urls(server, server_client, key, token,
                                                finished):
    '''🔴 Contract rule 5: a deployment is one scheme throughout. This one is
    served on http, so every URL it issues is: the artifact `303`, the upload
    grant and endpoint 6's sign-in link.'''
    from test_server_jobs import create

    server.config["SC_CONFIG"]._values["web_url_base"] = "http://localhost"
    item = listing(server_client, key, token, finished["id"])[0]
    job = create(server_client, key, token, jobname="job1").get_json()

    urls = [
        call(server_client, key, "GET", f"/v1/jobs/{finished['id']}/artifacts/{item['id']}",
             token).headers["Location"],
        call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant", token,
             json={"size_bytes": 10, "digest": "sha256:" + "0" * 64}).get_json()["url"],
        call(server_client, key, "POST", "/v1/auth/browser", token,
             json={"job_id": job["id"]}).get_json()["url"],
    ]

    assert all(url.startswith("http://localhost/") for url in urls), urls


def test_every_artifact_is_stored_and_served_gzipped(server_client, key, token, finished):
    '''Every kind, the manifest and a node's logs included, and the bytes
    served are the gzip itself.'''
    items = listing(server_client, key, token, finished["id"])
    assert {item["kind"] for item in items} >= {"manifest", "logs", "staging", "reports",
                                                "node"}

    # `diagnostics` is gzipped too, and read in the portal, never over the API.
    for item in [item for item in items if item["fetchable"]]:
        response = call(server_client, key, "GET",
                        f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)
        body = server_client.get(response.headers["Location"].split("http://localhost", 1)[1])
        assert body.data[:2] == b"\x1f\x8b", item["kind"]
        assert item["media_type"] == "application/gzip", item["kind"]


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
        "deleted_by = ?, deleted_reason = 'test' WHERE id = ?",
        (call(server_client, key, "GET", "/v1/me", token).get_json()["id"],
         item["id"]))

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)
    assert response.status_code == 404

    # The row stays in the listing, which is the same call jobs.deleted_at made.
    still = [a for a in listing(server_client, key, token, finished["id"])
             if a["id"] == item["id"]]
    assert still and still[0]["deleted_at"] and still[0]["fetchable"] is False


def test_past_its_retention_and_not_yet_swept_is_still_fetchable(
        server, server_client, key, token, finished):
    '''⚠️ Retention passing is deliberately not a row of the ladder: the reaper
    follows it by setting `deleted_at`, and until then the bytes are here. A
    promise to keep data at least that long says nothing about the minute
    after it -- this used to answer *not fetchable* the moment the date passed.'''
    item = listing(server_client, key, token, finished["id"])[0]
    server.config["SC_STORE"].execute(
        "UPDATE artifacts SET retained_until = '2020-01-01T00:00:00.000Z' "
        "WHERE id = ?", (item["id"],))

    assert next(i for i in listing(server_client, key, token, finished["id"])
                if i["id"] == item["id"])["fetchable"] is True
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)
    assert response.status_code == 303


def _mark(server, item, **columns):
    sets = ", ".join(f"{name} = ?" for name in columns)
    server.config["SC_STORE"].execute(
        f"UPDATE artifacts SET {sets} WHERE id = ?", (*columns.values(), item["id"]))


def _fetch(server_client, key, token, job_id, item):
    return call(server_client, key, "GET",
                f"/v1/jobs/{job_id}/artifacts/{item['id']}", token)


def test_a_pending_artifact_is_not_ready_and_never_refused_for_good(
        server, server_client, key, token, finished):
    '''🔴 The live bug. Still being described is transient, and a permanent
    `403` told a client to abandon an artifact that was about to be
    fetchable.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _mark(server, item, provenance="pending")

    response = _fetch(server_client, key, token, finished["id"], item)

    assert response.status_code == 409
    assert slug(response) == "not-ready"
    assert response.get_json()["artifact_kind"] == item["kind"]
    assert response.headers["Retry-After"]


def test_an_artifact_still_being_described_is_not_listed_nor_is_its_node(
        server, server_client, key, token, finished):
    '''🔴 Surface D308: listed once described, so a client fetching at
    `terminal` misses nothing it could have had. A `node` archive with such a
    member is held back with it; the other node's are listed.'''
    items = listing(server_client, key, token, finished["id"])
    log = next(i for i in items if i["kind"] == "logs" and i["step"] == "stepone")
    node = next(i for i in items if i["kind"] == "node" and i["step"] == "stepone")
    other = next(i for i in items if i["kind"] == "node" and i["step"] == "steptwo")
    _mark(server, log, provenance="pending")

    listed = {i["id"] for i in listing(server_client, key, token, finished["id"])}

    assert log["id"] not in listed and node["id"] not in listed
    assert other["id"] in listed


def test_a_withheld_artifact_is_not_approved(server, server_client, key, token,
                                             finished):
    '''The per-object gate said no -- and no `resource_kind` is forced onto a
    refusal that involves no resource.'''
    item = listing(server_client, key, token, finished["id"])[0]
    me = server.config["SC_STORE"].one("SELECT user_id FROM jobs WHERE id = ?",
                                       (finished["id"],))["user_id"]
    _mark(server, item, withheld_at="2026-09-25T00:00:00.000Z", withheld_by=me)

    response = _fetch(server_client, key, token, finished["id"], item)

    assert response.status_code == 403
    assert slug(response) == "artifact-not-approved"
    assert "resource_kind" not in response.get_json()


def test_a_node_archive_holding_a_withheld_member_is_not_fetchable(
        server, server_client, key, token, finished):
    '''Row 4: the archive holds every artifact at its coordinates, so handing
    it over would hand over the one that is withheld.'''
    items = listing(server_client, key, token, finished["id"])
    log = next(i for i in items if i["kind"] == "logs" and i["step"] == "stepone")
    node = next(i for i in items if i["kind"] == "node" and i["step"] == "stepone")
    me = server.config["SC_STORE"].one("SELECT user_id FROM jobs WHERE id = ?",
                                       (finished["id"],))["user_id"]
    _mark(server, log, withheld_at="2026-09-25T00:00:00.000Z", withheld_by=me)

    relisted = {i["id"]: i for i in listing(server_client, key, token, finished["id"])}
    assert relisted[node["id"]]["fetchable"] is False
    assert slug(_fetch(server_client, key, token, finished["id"], node)) == \
        "artifact-not-approved"


def test_a_node_archive_held_back_only_by_a_pending_member_is_not_ready(
        server, server_client, key, token, finished):
    '''🔴 D120: the worst member's refusal, and a member still being
    described is transient -- it was a blanket `artifact-not-approved`, the
    `pending` mistake one level down.'''
    items = listing(server_client, key, token, finished["id"])
    log = next(i for i in items if i["kind"] == "logs" and i["step"] == "stepone")
    node = next(i for i in items if i["kind"] == "node" and i["step"] == "stepone")
    _mark(server, log, provenance="pending")

    response = _fetch(server_client, key, token, finished["id"], node)

    assert response.status_code == 409
    assert slug(response) == "not-ready"
    assert response.headers["Retry-After"]


def test_a_withheld_member_is_worse_than_a_pending_one():
    from siliconcompiler.remote.server.outputs import artifacts

    assert artifacts.worst([None, "not-ready", "artifact-not-approved"]) == \
        "artifact-not-approved"
    assert artifacts.worst(["not-ready", "entitlement-denied"]) == "entitlement-denied"
    assert artifacts.worst([None, None]) is None


###########################
# max_download_bytes
###########################

def _ceiling(server, bytes_allowed):
    server.config["SC_CONFIG"].limits["max_download_bytes"] = bytes_allowed


def test_an_object_over_the_ceiling_is_refused_rather_than_redirected(
        server, server_client, key, token, finished):
    '''🔴 A real limit, not advice. It began as a number a client was trusted
    to apply to itself, which made it the only published ceiling with no
    refusal behind it -- so an operator who set it was setting policy any
    client could ignore by not reading it.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, item["size_bytes"] - 1)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)

    # 🔴 D117: a 403 and its own type, not `429 limit-exceeded` -- a client
    # obeying `Retry-After` on a ceiling that never refills retries for ever.
    assert response.status_code == 403
    assert slug(response) == "download-too-large"
    # The key it names is the key it is published under, which is what makes
    # the registry double as the enforcement trace.
    assert response.get_json()["limit"] == "max_download_bytes"


def test_an_object_exactly_at_the_ceiling_is_served(
        server, server_client, key, token, finished):
    '''A ceiling is inclusive. The alternative makes a limit set to exactly
    an object's size refuse it, which reads as off by one to everybody.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, item["size_bytes"])

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)

    assert response.status_code == 303


def test_no_query_parameter_or_header_lifts_the_ceiling(
        server, server_client, key, token, finished):
    '''🔴 There is no API override, and this is what that means in practice:
    the obvious spellings do nothing. A limit a caller can switch off is not a
    limit, so the way past it is a different surface -- the portal -- and not
    a flag on this one.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, 1)

    for attempt in (f"/v1/jobs/{finished['id']}/artifacts/{item['id']}?force=1",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}"
                    "?max_download_bytes=0"):
        assert call(server_client, key, "GET", attempt, token).status_code == 403

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token,
                    headers={"X-Max-Download-Bytes": "0",
                             "Range": "bytes=0-100"})
    assert response.status_code == 403


def test_unlimited_is_null_and_serves_anything(
        server, server_client, key, token, finished):
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, None)

    assert call(server_client, key, "GET",
                f"/v1/jobs/{finished['id']}/artifacts/{item['id']}",
                token).status_code == 303


def test_the_ceiling_that_binds_is_this_accounts_and_not_the_deployments(
        server, server_client, key, token, finished):
    '''🔴 `max_download_bytes` is the one limit a `user_limits` row may
    override, so reading the deployment's number here would enforce a ceiling
    the account was deliberately lifted above.'''
    from siliconcompiler.remote.server.identity import accounts

    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, 1)

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    accounts.set_limit(server.config["SC_STORE"], me, "max_download_bytes",
                       -1, me)          # -1 is the table's spelling of unlimited

    assert call(server_client, key, "GET",
                f"/v1/jobs/{finished['id']}/artifacts/{item['id']}",
                token).status_code == 303


def test_a_log_is_the_same_bytes_and_therefore_the_same_ceiling(
        server, server_client, key, token, finished):
    '''`/logs` hands out the signed URL endpoint 22 hands out, so a caller
    that cannot fetch a log as an artifact must not get it by asking for it as
    a log.'''
    _ceiling(server, 1)

    artifact_id = _ended_stream(server_client, key, token, finished["id"])
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{artifact_id}", token)

    assert response.status_code == 403
    assert slug(response) == "download-too-large"
    assert response.get_json()["limit"] == "max_download_bytes"


def test_retrying_is_not_the_answer_so_no_retry_after_is_offered(
        server, server_client, key, token, finished):
    '''This ceiling never clears on its own, and naming a moment to come
    back would be a lie -- which is why it is not `limit-exceeded`.'''
    item = listing(server_client, key, token, finished["id"])[0]
    _ceiling(server, 1)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{item['id']}", token)

    assert "Retry-After" not in response.headers


###########################
# 20. one node's log
###########################

def _ended_stream(server_client, key, token, job_id):
    import json as _json

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job_id}/logs?step=stepone&index=0", token)
    assert response.status_code == 303
    body = server_client.get(
        response.headers["Location"].split("http://localhost", 1)[1]).data.decode()
    events = [block for block in body.split("\n\n") if "event: node_state" in block]
    data = next(line for line in events[0].splitlines() if line.startswith("data:"))
    state = _json.loads(data[5:])
    assert state["terminal"] is True
    assert "event: end" in body
    return state["artifact_id"]


def test_a_terminal_nodes_stream_ends_at_once_naming_its_archive(
        server_client, key, token, finished):
    '''🔴 `/logs` is live only; a finished node's log is its gzipped
    `logs` artifact, which carries nothing but the node's logs.'''
    import io
    import tarfile

    artifact_id = _ended_stream(server_client, key, token, finished["id"])
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/artifacts/{artifact_id}", token)
    if response.status_code in (302, 303):
        response = server_client.get(
            response.headers["Location"].split("http://localhost", 1)[1])

    assert response.headers["Content-Type"].startswith("application/gzip")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Disposition"].startswith("attachment")
    with tarfile.open(fileobj=io.BytesIO(response.data), mode="r:gz") as tar:
        texts = [tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()]
    assert b"stepone ran\n" in texts


@pytest.mark.parametrize("missing", ["?step=stepone", "?index=0"])
def test_both_step_and_index_are_required(server_client, key, token, finished,
                                          missing):
    '''Two fields rather than one string: step=place index=10 and step=place1
    index=0 both render place10 and are two different nodes. Both or neither:
    neither is the whole job, and one alone is neither.'''
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
    import uuid

    datadir = tmp_path / "quiet"
    datadir.mkdir()
    (datadir / "config.json").write_text(_json.dumps({"features": []}))

    app = create_app(datadir)
    client = app.test_client()
    quiet_key = dpop.generate_key()
    quiet_token = login(client, quiet_key).get_json()["access_token"]

    assert client.get("/v1").get_json()["features"] == []

    store = app.config["SC_STORE"]
    me = call(client, quiet_key, "GET", "/v1/me", quiet_token).get_json()["id"]
    job_id = str(uuid.uuid4())
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


def test_a_finished_node_with_no_log_is_not_found(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 `/logs` is live only, and a node is completed only after it is
    indexed: a terminal node with no `logs` artifact never will have one.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job["id"],))

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 404


def test_a_node_this_job_does_not_have(server_client, key, token, finished):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/logs?step=nowhere&index=0", token)

    assert response.status_code == 404


def test_one_row_per_kind_per_node_even_under_a_race(server, finished):
    '''🔴 The check before the insert is not enough and cannot be made enough.

    Indexing runs on whichever request thread gets there first, and a client
    polling its job while tailing two logs has three of them. Two that check
    together both pass -- so a real aes run came back with 38 node archives for 23
    nodes, and the portal showed one node owning "logs, node archive, node archive". The
    unique index is what actually decides.
    '''
    import sqlite3

    import uuid

    store = server.config["SC_STORE"]
    existing = store.one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'node' "
        "AND step IS NOT NULL LIMIT 1", (finished["id"],))
    assert existing is not None

    # Exactly what a second thread would attempt, having passed _exists.
    with pytest.raises(sqlite3.IntegrityError):
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", digest, '
            "  location_id, storage_key, size_bytes, media_type, kind, "
            "  provenance) "
            "VALUES (?, ?, ?, ?, 'sha256:x', ?, 'k', 1, 'application/gzip', "
            "        'node', 'declared')",
            (str(uuid.uuid4()), finished["id"], existing["step"], existing["index"],
             existing["location_id"]))


def test_the_job_level_rows_are_protected_too(server, finished):
    '''SQLite counts NULLs as distinct in a unique index, which would leave
    exactly the rows with no node unprotected -- hence the coalesce.'''
    import sqlite3

    import uuid

    store = server.config["SC_STORE"]
    existing = store.one(
        "SELECT * FROM artifacts WHERE job_id = ? AND step IS NULL "
        "AND kind <> 'input' LIMIT 1", (finished["id"],))
    assert existing is not None

    with pytest.raises(sqlite3.IntegrityError):
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", digest, '
            "  location_id, storage_key, size_bytes, media_type, kind, "
            "  provenance) "
            "VALUES (?, ?, NULL, NULL, 'sha256:x', ?, 'k', 1, 'text/plain', "
            "        ?, 'declared')",
            (str(uuid.uuid4()), finished["id"], existing["location_id"],
             existing["kind"]))


def test_uploads_are_numbered_and_the_number_is_in_the_key(server, finished):
    '''🔴 One per UPLOAD rather than exempt (database D101): an exemption
    holds only while the code writes each row once, an ordinal in the key holds
    anyway -- and a CHECK ties the ordinal to job-level `input` exactly.'''
    import sqlite3

    import uuid

    store = server.config["SC_STORE"]
    first = store.one("SELECT * FROM artifacts WHERE job_id = ? AND kind = 'input' "
                      "AND step IS NULL", (finished["id"],))
    assert first["upload_seq"] == 1

    def insert(kind, seq, step=None):
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", digest, '
            "  location_id, storage_key, size_bytes, media_type, kind, upload_seq, "
            "  provenance) VALUES (?, ?, ?, ?, 'sha256:x', ?, 'k', 1, "
            "  'application/gzip', ?, ?, 'declared')",
            (str(uuid.uuid4()), finished["id"], step, step and "0", first["location_id"],
             kind, seq))

    insert("input", 2)
    with pytest.raises(sqlite3.IntegrityError):
        insert("input", 2)                       # the same upload twice
    with pytest.raises(sqlite3.IntegrityError):
        insert("input", None)                    # a job-level input with no number
    with pytest.raises(sqlite3.IntegrityError):
        insert("logs", 3)                        # a number on anything else
    with pytest.raises(sqlite3.IntegrityError):
        insert("input", 3, step="stepone")       # or on a node's input


def test_a_node_input_is_what_it_was_handed_and_no_member_of_its_archive(
        server_client, key, token, finished):
    '''The node archive leaves `inputs/` out, so a node's `input` decides
    nothing about whether that archive may be fetched.'''
    items = listing(server_client, key, token, finished["id"], "?kind=input&step=stepone")

    assert [(item["step"], item["index"]) for item in items] == [("stepone", "0")]
    assert items[0]["media_type"] == "application/gzip" and items[0]["fetchable"]


def _node_with_inputs(server, finished, step, links):
    job = server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (finished["id"],))
    root = server.config["SC_JOBS"].job_root(job["user_id"], job["id"])
    node = root / job["design"] / job["jobname"] / step / "0"
    (node / "inputs").mkdir(parents=True)
    (node / f"sc_{step}_0.log").write_text("log\n")
    for name, target in links.items():
        (node / "inputs" / name).symlink_to(target)
    from siliconcompiler.remote.server.outputs import artifacts
    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, step, "0")
    return server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ? AND step = ?", (job["id"], step))


def _upstream_file(server, finished):
    job = server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (finished["id"],))
    root = server.config["SC_JOBS"].job_root(job["user_id"], job["id"])
    upstream = root / "gcd" / "job0" / "stepone" / "0" / "outputs"
    upstream.mkdir(parents=True, exist_ok=True)
    (upstream / "gcd.vg").write_text("module gcd; endmodule\n")
    return job, root, upstream / "gcd.vg"


def _members(server, row):
    import tarfile

    with tarfile.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"])) as tar:
        return {member.name: member for member in tar.getmembers()}


def test_the_node_bound_input_holds_links_not_bytes(server, finished):
    '''🔴 An upstream output linked into a node's `inputs/` is stored as one
    link to its home, never as the bytes (database D142).'''
    _, _, upstream = _upstream_file(server, finished)

    rows = _node_with_inputs(server, finished, "linked", {"gcd.vg": upstream})
    row, = [row for row in rows if row["kind"] == "input"]

    member = _members(server, row)["inputs/gcd.vg"]
    assert member.issym()
    assert member.linkname == "../../../stepone/0/outputs/gcd.vg"


def _pass_through(server, finished, hard: bool):
    '''A node that passes its input through: `outputs/x` -> `inputs/x` ->
    the upstream `outputs/x`, by symlink or by hard link, as
    `link_symlink_copy` makes it.'''
    import os

    from siliconcompiler.remote.server.outputs import artifacts

    job, root, upstream = _upstream_file(server, finished)
    node = root / "gcd" / "job0" / "passed" / "0"
    (node / "inputs").mkdir(parents=True)
    (node / "outputs").mkdir()
    (node / "sc_passed_0.log").write_text("log\n")
    if hard:
        os.link(upstream, node / "inputs" / "gcd.vg")
        os.link(node / "inputs" / "gcd.vg", node / "outputs" / "gcd.vg")
    else:
        (node / "inputs" / "gcd.vg").symlink_to(upstream)
        (node / "outputs" / "gcd.vg").symlink_to("../inputs/gcd.vg")
    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, "passed", "0")
    return {row["kind"]: row for row in server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ? AND step = 'passed'", (job["id"],))}


@pytest.mark.parametrize("hard", [False, True], ids=["symlinked", "hard-linked"])
def test_a_pass_through_nodes_archive_holds_one_link_to_its_home(server, finished, hard):
    '''SiliconCompiler's chain becomes one relative link to the upstream
    node's `outputs/` -- a symlinked chain by reading it, a hard-linked one by
    finding the file's home by inode. Nothing is copied.'''
    rows = _pass_through(server, finished, hard)

    for kind, name in (("node", "outputs/gcd.vg"), ("input", "inputs/gcd.vg")):
        member = _members(server, rows[kind])[name]
        assert member.issym(), (kind, member.type)
        assert member.linkname == "../../../stepone/0/outputs/gcd.vg"


def test_a_hard_linked_pair_in_one_node_is_a_tar_hard_link(server, finished):
    '''Both names in the same archive: the bytes once, and a hard link to
    their first appearance.'''
    import os

    from siliconcompiler.remote.server.outputs import artifacts

    job, root, _ = _upstream_file(server, finished)
    node = root / "gcd" / "job0" / "twice" / "0"
    (node / "outputs").mkdir(parents=True)
    (node / "outputs" / "a.vg").write_text("module a; endmodule\n")
    os.link(node / "outputs" / "a.vg", node / "outputs" / "b.vg")
    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, "twice", "0")
    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND step = 'twice' AND kind = 'node'",
        (job["id"],))

    members = _members(server, row)
    assert members["outputs/a.vg"].isfile()
    assert members["outputs/b.vg"].islnk()
    assert members["outputs/b.vg"].linkname == "outputs/a.vg"


def test_a_file_with_a_name_outside_the_job_is_dropped(server, finished, tmp_path):
    '''🔴 A link count above the names the job's tree holds is a name
    outside the job -- PDK data hard-linked in, perhaps -- and it is treated as
    a link leaving the job: dropped, never stored.'''
    import os

    from siliconcompiler.remote.server.outputs import artifacts

    job, root, _ = _upstream_file(server, finished)
    outside = tmp_path / "pdk.lib"
    outside.write_text("the foundry's own file\n")
    node = root / "gcd" / "job0" / "borrowed" / "0"
    (node / "outputs").mkdir(parents=True)
    (node / "outputs" / "mine.v").write_text("module mine; endmodule\n")
    try:
        os.link(outside, node / "outputs" / "pdk.lib")
    except OSError:
        pytest.skip("the job tree and tmp_path are on different filesystems")
    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, "borrowed", "0")
    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND step = 'borrowed' AND kind = 'node'",
        (job["id"],))

    members = _members(server, row)
    assert "outputs/pdk.lib" not in members
    assert members["outputs/mine.v"].isfile()


def test_a_name_the_next_node_adds_while_a_node_is_archived_is_inside_the_job(
        server, finished, monkeypatch):
    '''🔴 The race that lost a compiled testbench: a node is archived as it
    finishes, which is when the scheduler starts the next node and hard-links
    this node's outputs into its inputs. A name that appears after the walk is
    still inside the job, and the file is stored, not left out as if it had a
    name outside.'''
    import os

    from siliconcompiler.remote import links
    from siliconcompiler.remote.server.outputs import artifacts

    job, root, _ = _upstream_file(server, finished)
    node = root / "gcd" / "job0" / "compile" / "0"
    (node / "outputs").mkdir(parents=True)
    built = node / "outputs" / "tb.vexe"
    built.write_bytes(b"\x7fELF the compiled testbench")
    inputs = root / "gcd" / "job0" / "simulate" / "0" / "inputs"
    inputs.mkdir(parents=True)

    walk = links.Homes._walk

    def walk_then_start_the_next_node(self):
        walk(self)
        if not (inputs / "tb.vexe").exists():
            os.link(built, inputs / "tb.vexe")

    monkeypatch.setattr(links.Homes, "_walk", walk_then_start_the_next_node)

    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, "compile", "0")
    row = server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE job_id = ? AND step = 'compile' AND kind = 'node'",
        (job["id"],))

    members = _members(server, row)
    assert members["outputs/tb.vexe"].isfile()
    assert members["outputs/tb.vexe"].size == built.stat().st_size


def test_a_link_out_of_the_job_is_never_read_nor_stored(
        server, finished, tmp_path):
    '''🔴 The attack (surface D133): a node's own code leaves a link to a
    host file in its inputs. Following it would pack the host's bytes as the
    job's; storing it would hand out the host's path (D159).'''
    import tarfile

    secret = tmp_path / "host-secret"
    secret.write_text("the host's own file\n")
    rows = _node_with_inputs(server, finished, "outward", {"stolen": secret})
    row, = [row for row in rows if row["kind"] == "input"]

    with tarfile.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"])) as tar:
        assert not any(m.name.endswith("stolen") for m in tar.getmembers())
        assert not any(str(secret) in (m.linkname or "") for m in tar.getmembers())


def test_a_log_that_is_a_link_out_is_not_indexed(server, finished, tmp_path):
    '''The same attack on the files indexed one by one: a node that replaces
    its log with a link does not get the host's file published as its log.'''
    secret = tmp_path / "host-secret"
    secret.write_text("the host's own file\n")
    job = server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (finished["id"],))
    root = server.config["SC_JOBS"].job_root(job["user_id"], job["id"])
    node = root / "gcd" / "job0" / "linklog" / "0"
    (node / "outputs").mkdir(parents=True)
    (node / "sc_linklog_0.log").symlink_to(secret)
    (node / "outputs" / "gcd.pkg.json").symlink_to(secret)

    from siliconcompiler.remote.server.outputs import artifacts
    artifacts.collect_node(server.config["SC_STORE"], server.config["SC_STORAGE"],
                           server.config["SC_CONFIG"], job, root, "linklog", "0")

    rows = server.config["SC_STORE"].all(
        "SELECT kind, storage_key FROM artifacts WHERE job_id = ? AND step = 'linklog'",
        (job["id"],))
    assert {row["kind"] for row in rows} == {"node"}
    import tarfile
    with tarfile.open(server.config["SC_STORAGE"].artifact_path(rows[0]["storage_key"])) as tar:
        # Not in the node archive at all: never as the bytes, and not as a link
        # naming the host's path either.
        assert "sc_linklog_0.log" not in tar.getnames()
        assert all(not member.isfile() for member in tar.getmembers())


###########################
# A refused upload: kept, except when it is restricted
###########################

def _uploads(server, job_id):
    return server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ? AND upload_seq IS NOT NULL "
        "ORDER BY upload_seq", (job_id,))


def test_an_upload_refused_for_its_digest_stays_where_the_grant_put_it(
        server, server_client, key, token, job_archive, dispatcher):
    '''A refusal of the request, so the job still waits and its upload is
    kept where the grant put it; the bytes the grant was issued for, sent to
    it, are recorded -- under the hash storage holds.'''
    from test_server_jobs import put, sized

    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                 token, json=sized(size, digest)).get_json()
    put(server_client, grant, b"\0" * size)

    response = submit(server_client, key, token, job["id"])

    assert slug(response) == "upload-digest-mismatch"
    assert not _uploads(server, job["id"])
    assert server.config["SC_STORAGE"].stat_upload(job["id"])[0] == size

    put(server_client, grant, open(archive, "rb").read())
    submit(server_client, key, token, job["id"])
    kept, = _uploads(server, job["id"])
    assert kept["digest"] == digest and kept["upload_seq"] == 1


def test_an_upload_refused_as_restricted_is_deleted_and_the_reason_kept(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 `upload-forbidden`, on either detection: the bytes are not kept
    (surface D133). The job, its reason, and the member and hash the reason
    names are what remains.'''
    from siliconcompiler.remote.server.errors import ProblemError

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    kept, = _uploads(server, job["id"])
    stored = server.config["SC_STORAGE"].artifact_path(kept["storage_key"])
    assert stored.is_file()

    jobs = server.config["SC_JOBS"]
    row = server.config["SC_STORE"].one("SELECT * FROM jobs WHERE id = ?", (job["id"],))
    jobs._refuse(None, row, ProblemError(
        "upload-forbidden", resource_kind="pdk", detected="content",
        member="sc_collected_files/cells.lef",
        detail="sc_collected_files/cells.lef (sha256:abc) matches a controlled pdk"))

    assert _uploads(server, job["id"]) == [] and not stored.exists()
    reason = server.config["SC_STORE"].one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? AND to_state = "
        "'rejected'", (job["id"],))["reason"]
    assert "cells.lef" in reason and "sha256:abc" in reason


def test_a_node_over_a_member_deleted_on_its_own_is_not_approved_and_alerts(
        server, server_client, key, token, finished, caplog):
    '''🔴 Handing the archive over would undo the deletion (entitlements
    D41). The state should not exist -- a node is reaped with its first member
    -- so an operator is told, once.'''
    items = listing(server_client, key, token, finished["id"])
    log = next(i for i in items if i["kind"] == "logs" and i["step"] == "stepone")
    node = next(i for i in items if i["kind"] == "node" and i["step"] == "stepone")
    _mark(server, log, deleted_at="2026-09-26T00:00:00.000Z")

    with caplog.at_level("ERROR", logger="sc-server"):
        first = _fetch(server_client, key, token, finished["id"], node)
        _fetch(server_client, key, token, finished["id"], node)

    assert slug(first) == "artifact-not-approved"
    assert sum("deleted on its own" in record.message for record in caplog.records) == 1


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
    assert _only(items, "logs")[0]["media_type"] == "application/gzip"


def test_a_stale_backup_log_is_not_mistaken_for_this_run(
        server, server_client, key, token, job_archive, dispatcher):
    '''What the old glob would have picked: the oldest rotated backup, which is
    a previous run's log presented as this one's.'''
    def prepare(job_root, build_dir):
        (build_dir / "job.20200101-000000.log").write_text("a different run\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    assert not _only(listing(server_client, key, token, job["id"]), "logs")


def test_the_runners_own_log_is_the_operators_and_never_the_jobs_log(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 The run died before SiliconCompiler wrote its `job.log`, and the
    runner's own log is the only account there is. It is the operators'
    record, `diagnostics` (surface D295): listed, never fetchable over the API,
    and refused when asked for. Job-level `logs` is `job.log` alone.'''
    from siliconcompiler.remote.server.running.dispatch import RUN_LOG

    def prepare(job_root, build_dir):
        (job_root / RUN_LOG).write_text("Traceback (most recent call last):\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    items = listing(server_client, key, token, job["id"])

    assert not [item for item in _only(items, "logs") if item["step"] is None]
    held, = [item for item in _only(items, "diagnostics") if item["step"] is None]
    assert held["fetchable"] is False
    got = call(server_client, key, "GET",
               f"/v1/jobs/{job['id']}/artifacts/{held['id']}", token)
    assert got.status_code == 403
    assert slug(got) == "artifact-not-approved"

    members = _members(server, server.config["SC_STORE"].one(
        "SELECT * FROM artifacts WHERE id = ?", (held["id"],)))
    assert "run.log" in members


def test_only_one_job_level_log_is_ever_indexed(
        server, server_client, key, token, job_archive, dispatcher):
    '''⚠️ An artifact is identified by `(job, kind, step, index)` and carries no
    name on the wire, so two job-level logs would reach a client as two objects
    it cannot tell apart -- the duplicate-looking listing this server has
    already produced once.'''
    from siliconcompiler.remote.server.running.dispatch import RUN_LOG

    def prepare(job_root, build_dir):
        (build_dir / "job.log").write_text("the flow ran\n")
        (job_root / RUN_LOG).write_text("and the batch job said this\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    assert len(_only(listing(server_client, key, token, job["id"]), "logs")) == 1


def test_the_job_level_log_is_the_runs_job_log_alone(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 SiliconCompiler's `job.log`, and nothing of this server's: its record
    of the job is `staging` and `diagnostics`, never inside the run's own log,
    where the two read as one confusing file (surface D295).'''
    import gzip

    from siliconcompiler.remote.server.running.dispatch import RUN_LOG

    def prepare(job_root, build_dir):
        (build_dir / "job.log").write_text("the flow ran\n")
        (job_root / RUN_LOG).write_text("and the batch job said this\n")

    job = ran(server, server_client, key, token, job_archive, prepare)
    item, = [item for item in _only(listing(server_client, key, token, job["id"]), "logs")
             if item["step"] is None]
    row = server.config["SC_STORE"].one("SELECT storage_key FROM artifacts WHERE id = ?",
                                        (item["id"],))
    with gzip.open(server.config["SC_STORAGE"].artifact_path(row["storage_key"]), "rt") as f:
        assert f.read() == "the flow ran\n"


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


def test_the_two_ways_bytes_go_are_told_apart_by_an_enum(
        server, server_client, key, token, finished):
    '''🔴 `deleted_by` decides it and `deleted_by` is not on the wire: it names
    a user, which is a fact about an account rather than about the object. NULL
    is the reaper -- retention doing what it said -- and set is a person.'''
    items = listing(server_client, key, token, finished["id"])
    assert all(item["deleted_cause"] is None for item in items)

    call(server_client, key, "DELETE", f"/v1/jobs/{finished['id']}", token)

    after = server.config["SC_STORE"].all(
        "SELECT * FROM artifacts WHERE job_id = ?", (finished["id"],))
    from siliconcompiler.remote.server.outputs import artifacts as art

    assert after and all(art.cause(row) == "removed" for row in after)


def test_a_deletion_nobody_gave_a_reason_for_says_where_it_came_from(
        server, server_client, key, token, finished):
    '''✅ Synthesized rather than left null, naming who acted -- the owner
    here -- and never the device or an id (surface §17, §19).'''
    call(server_client, key, "DELETE", f"/v1/jobs/{finished['id']}", token)

    reasons = {row["deleted_reason"] for row in server.config["SC_STORE"].all(
        "SELECT deleted_reason FROM artifacts WHERE job_id = ?",
        (finished["id"],))}

    assert len(reasons) == 1
    said = reasons.pop()
    assert said == "deleted by its owner"
    read = call(server_client, key, "GET", f"/v1/jobs/{finished['id']}", token).get_json()
    # Set exactly when deleted_at is, and no deleted_cause on a job (D279).
    assert read["deleted_reason"] == said and "deleted_cause" not in read
    # And never the account it acted as.
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    assert me not in said
