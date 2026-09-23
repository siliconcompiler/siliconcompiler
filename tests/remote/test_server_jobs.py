
import pytest

from conftest import call, login, slug


pytest.importorskip("flask", reason="the server extra is not installed")


# The integration rig, in process. Every ordering rule the contract calls
# normative is asserted here rather than in the conformance fixtures, because
# these are the rules the SERVER owes -- a canned answer cannot get the order of
# a digest check and an extraction wrong.


class FakeDispatcher:
    '''Records what it was asked to run, and never runs it.

    Most of what submit does is refusal, and a refusal that reached the
    dispatcher would be a bug. Where a real run is the point, `cluster="local"`
    is used instead -- see test_parity.py.
    '''

    name = "fake"

    def __init__(self):
        self.submitted = []
        self.cancelled = []
        self.handed = {}
        self.alive = True

    def submit(self, job_id, jobroot, manifest, image=None, queue=None):
        self.submitted.append((job_id, jobroot, manifest))
        self.handed = {"image": image, "queue": queue}
        return f"fake:{len(self.submitted)}"

    def is_alive(self, scheduler_job_id):
        return self.alive

    def cancel(self, scheduler_job_id):
        self.cancelled.append(scheduler_job_id)


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def jobs(server):
    return server.config["SC_JOBS"]


def create(client, key, token, **body):
    body.setdefault("design", "gcd")
    body.setdefault("jobname", "job0")
    headers = {}
    if "idempotency_key" in body:
        headers["Idempotency-Key"] = body.pop("idempotency_key")
    return call(client, key, "POST", "/v1/jobs", token, json=body, headers=headers)


def put(client, grant, data):
    return client.put(grant["url"].split("http://localhost", 1)[1], data=data)


def stage(client, key, token, archive, size, **body):
    '''A job with its bytes uploaded, ready to submit.'''
    body.setdefault("resources", {"upload_bytes": size})
    job = create(client, key, token, **body).get_json()
    grant = call(client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token).get_json()
    put(client, grant, open(archive, "rb").read())
    return job


def submit(client, key, token, job_id, digest, size, **extra):
    headers = {}
    if "idempotency_key" in extra:
        headers["Idempotency-Key"] = extra.pop("idempotency_key")
    return call(client, key, "POST", f"/v1/jobs/{job_id}/submit", token,
                json={"digest": digest, "bytes": size, **extra}, headers=headers)


###########################
# 13. create
###########################

def test_create_returns_an_id_and_a_location(server_client, key, token):
    response = create(server_client, key, token)

    assert response.status_code == 201
    body = response.get_json()
    assert body["state"] == "created"
    # null on a personal job, never absent: `null` is what a personal job on
    # any server says, and it carries no capability meaning.
    assert body["project"] is None
    assert response.headers["Location"] == f"/v1/jobs/{body['id']}"
    # No `upload` member: the grant is its own endpoint, which is what gives an
    # expired grant a way back.
    assert "upload" not in body


def test_ids_sort_by_when_they_were_minted(server_client, key, token):
    '''UUIDv7, and it is not decoration: the collection is ordered by creation
    and the cursor is a keyset over it, so the id IS the tiebreaker.'''
    first = create(server_client, key, token).get_json()["id"]
    second = create(server_client, key, token, jobname="job1").get_json()["id"]

    assert first < second


@pytest.mark.parametrize("missing", ["design", "jobname"])
def test_design_and_jobname_are_authoritative(server_client, key, token, missing):
    '''Nothing in a SiliconCompiler manifest names either, so they cannot be
    re-derived and a job row cannot exist without them.'''
    body = {"design": "gcd", "jobname": "job0"}
    del body[missing]

    response = call(server_client, key, "POST", "/v1/jobs", token, json=body)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


@pytest.mark.parametrize("name", ["../etc", "a/b", "", "." * 200, "-leading"])
def test_a_name_that_could_become_a_path_is_refused(server_client, key, token, name):
    '''Both become a path segment under the job's own root. This is the reason
    a manifest cannot name its way out of the directory it was given.'''
    response = create(server_client, key, token, design=name)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_a_project_is_refused_rather_than_ignored(server_client, key, token):
    '''Silently dropping it creates a job the caller believes is shared and
    nobody else can see -- invisible from both ends. Permanent, so a client
    stops offering the picker.'''
    response = create(server_client, key, token, project="rocket-v2")

    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"
    assert response.get_json()["feature"] == "projects"


def test_the_descriptor_refuses_before_the_bytes_move(server_client, key, token):
    response = create(server_client, key, token, flow={"nodes": 10 ** 9})

    assert response.status_code == 403
    assert slug(response) == "node-limit-exceeded"
    assert response.get_json()["limit"] == "max_job_nodes"


def test_a_declared_upload_larger_than_the_ceiling(server_client, key, token):
    response = create(server_client, key, token,
                      resources={"upload_bytes": 1 << 40})

    assert response.status_code == 413
    assert slug(response) == "upload-too-large"
    assert response.get_json()["limit"] == "max_upload_bytes"


def test_a_sparse_descriptor_is_never_refused_for_being_sparse(server_client, key, token):
    '''No field is required. The server checks whatever is present and skips
    the check a missing field would have answered.'''
    assert create(server_client, key, token, flow={}).status_code == 201


def test_pending_uploads_is_a_ceiling(server_client, key, token, server):
    ceiling = server.config["SC_CONFIG"].limits["pending_uploads"]

    for n in range(ceiling):
        assert create(server_client, key, token, jobname=f"job{n}").status_code == 201

    response = create(server_client, key, token, jobname="one-too-many")
    assert response.status_code == 429
    assert slug(response) == "limit-exceeded"
    assert response.get_json()["limit"] == "pending_uploads"
    # A 429 without it tells a client to guess.
    assert response.headers["Retry-After"]


###########################
# Idempotency-Key
###########################

def test_the_same_key_and_the_same_body_is_the_same_job(server_client, key, token):
    first = create(server_client, key, token, idempotency_key="k1")
    second = create(server_client, key, token, idempotency_key="k1")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.get_json()["id"] == second.get_json()["id"]


def test_the_same_key_with_a_different_body_is_refused(server_client, key, token):
    '''Returning the first job would answer a question the caller did not
    ask.'''
    create(server_client, key, token, idempotency_key="k1")
    response = create(server_client, key, token, jobname="other", idempotency_key="k1")

    assert response.status_code == 422
    assert slug(response) == "idempotency-key-reuse"


def test_one_users_key_does_not_collide_with_anothers(server_client, key, token):
    from siliconcompiler.remote import dpop

    other_key = dpop.generate_key()
    other = login(server_client, other_key, subject="machine:1001").get_json()

    mine = create(server_client, key, token, idempotency_key="k1").get_json()
    theirs = create(server_client, other_key, other["access_token"],
                    idempotency_key="k1").get_json()

    assert mine["id"] != theirs["id"]


###########################
# Job reuse
###########################

def reuse_job(jobs, store, user_id, run_hash, state, **columns):
    '''A finished job with a hash, written straight into the store.'''
    from siliconcompiler.remote.server.ids import uuid7

    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "                  run_hash, manifest_pdk) "
        "VALUES (?, ?, ?, 'gcd', 'old', '{}', ?, 'none')",
        (job_id, user_id, state, run_hash))
    if columns:
        # One statement, because the archived_at/archived_by CHECK is on the
        # pair: setting them one at a time fails on the first.
        assignments = ", ".join(f"{column} = ?" for column in columns)
        store.execute(f"UPDATE jobs SET {assignments} WHERE id = ?",
                      (*columns.values(), job_id))
    return job_id


@pytest.fixture
def me(server, server_client, key, token):
    return call(server_client, key, "GET", "/v1/me", token).get_json()["id"]


@pytest.mark.parametrize("state,returned", [
    ("completed", True),
    ("failed", True),         # the hash covers the environment, so a failure the
                              # hash determines is a result
    ("rejected", False),      # an entitlement is a property of the person at a
                              # moment, not of the job
    ("cancelled", False),     # user interaction, not a result
    ("abandoned", False),
    ("running", False),       # nothing to return yet
])
def test_which_states_job_reuse_returns(server, server_client, key, token, me,
                                        state, returned):
    store = server.config["SC_STORE"]
    jobs = server.config["SC_JOBS"]
    existing = reuse_job(jobs, store, me, "hash-1", state)

    response = create(server_client, key, token, run_hash="hash-1")

    if returned:
        # 200 rather than 201: a 201 carrying an old job's id is
        # indistinguishable from a new one.
        assert response.status_code == 200
        assert response.get_json()["id"] == existing
    else:
        assert response.status_code == 201
        assert response.get_json()["id"] != existing


def test_an_archived_job_is_never_returned(server, server_client, key, token, me):
    '''The one thing ever added to archived_at's "and NOTHING else". It is how a
    person says stop handing me that result, with no endpoint for it.'''
    store = server.config["SC_STORE"]
    existing = reuse_job(server.config["SC_JOBS"], store, me, "hash-1", "completed",
                         archived_at="2026-01-01T00:00:00.000Z", archived_by=me)

    response = create(server_client, key, token, run_hash="hash-1")

    assert response.status_code == 201
    assert response.get_json()["id"] != existing


def test_the_lookup_is_owner_scoped(server, server_client, key, token):
    '''🔴 The whole safety argument. A global cache would hand anyone who can
    present a derivation whatever anyone else had run.'''
    from siliconcompiler.remote import dpop

    other_key = dpop.generate_key()
    other_token = login(server_client, other_key,
                        subject="machine:1001").get_json()["access_token"]
    other_id = call(server_client, other_key, "GET", "/v1/me",
                    other_token).get_json()["id"]

    theirs = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"],
                       other_id, "hash-1", "completed")

    response = create(server_client, key, token, run_hash="hash-1")

    assert response.status_code == 201
    assert response.get_json()["id"] != theirs


def test_omitting_the_hash_runs_it_anyway(server, server_client, key, token, me):
    '''The escape hatch a script uses, and it needs no knowledge of the feature
    at all.'''
    reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"], me,
              "hash-1", "completed")

    assert create(server_client, key, token).status_code == 201


###########################
# 14. upload-grant
###########################

def test_the_grant_is_200_because_re_issue_is_the_point(server_client, key, token):
    job = create(server_client, key, token).get_json()

    first = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token)
    second = call(server_client, key, "POST",
                  f"/v1/jobs/{job['id']}/upload-grant", token)

    assert first.status_code == 200
    assert second.status_code == 200
    for response in (first, second):
        body = response.get_json()
        assert body["method"] == "PUT"
        assert body["url"]
        assert body["headers"]["content-length"]
        assert body["expires_at"]


def test_the_grant_moves_the_job_to_awaiting_input(server_client, key, token):
    job = create(server_client, key, token).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant", token)

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "awaiting_input"
    assert read["terminal"] is False


def test_the_size_comes_from_the_job_not_from_the_call(server_client, key, token):
    '''Taking a size here would let a re-issue widen a signature the first grant
    bound.'''
    job = create(server_client, key, token,
                 resources={"upload_bytes": 4096}).get_json()

    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token).get_json()

    assert grant["headers"]["content-length"] == "4096"


def test_no_grant_for_a_job_that_is_past_it(server, server_client, key, token, me):
    existing = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"],
                         me, None, "completed")

    response = call(server_client, key, "POST",
                    f"/v1/jobs/{existing}/upload-grant", token)

    assert response.status_code == 409
    assert slug(response) == "job-state-conflict"


###########################
# The signed PUT
###########################

def test_the_signature_is_the_credential(server_client, key, token, job_archive):
    '''No Authorization header and no proof: that is what a presigned URL is.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token,
                 resources={"upload_bytes": size}).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token).get_json()

    response = put(server_client, grant, open(archive, "rb").read())

    assert response.status_code == 200
    assert response.get_json()["bytes"] == size


def test_an_altered_url_is_refused(server_client, key, token, job_archive):
    archive, digest, size = job_archive()
    job = create(server_client, key, token,
                 resources={"upload_bytes": size}).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token).get_json()

    widened = grant["url"].replace(f"max_bytes={size}", "max_bytes=999999999")
    response = server_client.put(widened.split("http://localhost", 1)[1],
                                 data=b"x" * 100)

    assert response.status_code == 400


def test_the_upload_route_needs_a_signature(server_client, key, token):
    job = create(server_client, key, token).get_json()

    response = server_client.put(f"/storage/upload/{job['id']}", data=b"x")

    assert response.status_code == 400


###########################
# 15. submit
###########################

def test_submit_runs_the_job(server_client, key, token, job_archive, dispatcher):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 202
    body = response.get_json()
    assert body["state"] == "queued"
    assert body["submitted_at"]
    assert body["flow"] == "nopflow"
    assert body["progress"]["total_count"] == 2
    assert {node["step"] for node in body["nodes"]} == {"stepone", "steptwo"}
    assert all(node["state"] == "pending" for node in body["nodes"])
    assert dispatcher.submitted


def test_submit_records_the_flows_shape(server, server_client, key, token,
                                        job_archive, dispatcher):
    '''The edges are rows so a page can draw the DAG without reading object
    storage.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    edges = server.config["SC_STORE"].all(
        "SELECT * FROM job_node_edges WHERE job_id = ?", (job["id"],))

    assert [(row["from_step"], row["to_step"]) for row in edges] == \
        [("stepone", "steptwo")]


def test_a_digest_mismatch_refuses_before_anything_is_extracted(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 The order is normative. Getting it wrong is how an archive bomb gets
    opened.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"],
                      "sha256:" + "0" * 64, size)

    assert response.status_code == 422
    assert slug(response) == "upload-digest-mismatch"

    root = server.config["SC_JOBS"].job_root(
        call(server_client, key, "GET", "/v1/me", token).get_json()["id"], job["id"])
    assert not root.exists()

    # A refused job never ran, and keeping it out of `failed` is what stops an
    # entitlement-denial spike reading as a spike in broken designs.
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "rejected"
    assert read["terminal"] is True
    assert read["error"]["type"].endswith("upload-digest-mismatch")


def test_a_byte_count_that_disagrees_is_a_mismatch(server_client, key, token,
                                                   job_archive, dispatcher):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, size + 1)

    assert response.status_code == 422
    assert slug(response) == "upload-digest-mismatch"


def test_the_digest_is_prefixed_and_sha256_only(server_client, key, token,
                                                job_archive, dispatcher):
    '''One value that is either right or malformed, where two fields can
    disagree.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"],
                      digest.split(":", 1)[1], size)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_an_archive_violation_names_which_rule(server_client, key, token,
                                               job_archive, dispatcher):
    archive, digest, size = job_archive(
        extra={"../escape": b"owned"})
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 422
    assert slug(response) == "archive-rejected"
    assert response.get_json()["violation"] == "traversal"


def test_a_manifest_that_is_not_where_it_was_declared(server_client, key, token,
                                                      nop_project, job_archive,
                                                      dispatcher):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size, jobname="somethingelse")

    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 422
    assert slug(response) == "declared-mismatch"


def test_submitting_with_nothing_uploaded(server_client, key, token):
    job = create(server_client, key, token).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant", token)

    response = submit(server_client, key, token, job["id"], "sha256:" + "0" * 64, 1)

    assert response.status_code == 409
    assert slug(response) == "job-state-conflict"


def test_a_retried_submit_under_one_key_is_the_same_answer(
        server_client, key, token, job_archive, dispatcher):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    first = submit(server_client, key, token, job["id"], digest, size,
                   idempotency_key="s1")
    second = submit(server_client, key, token, job["id"], digest, size,
                    idempotency_key="s1")

    assert first.status_code == 202
    assert second.status_code == 202
    assert len(dispatcher.submitted) == 1


###########################
# 17. get
###########################

def test_a_job_is_not_readable_by_a_stranger(server, server_client, key, token):
    '''🔴 The defect the identity work exists to fix. 404, not 403: a 403 would
    confirm the id belongs to somebody.'''
    from siliconcompiler.remote import dpop

    job = create(server_client, key, token).get_json()

    other_key = dpop.generate_key()
    other_token = login(server_client, other_key,
                        subject="machine:1001").get_json()["access_token"]

    response = call(server_client, other_key, "GET", f"/v1/jobs/{job['id']}",
                    other_token)

    assert response.status_code == 404
    assert slug(response) == "not-found"


def test_the_poll_interval_comes_from_the_server(server_client, key, token):
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    assert response.status_code == 200
    assert int(response.headers["Retry-After"]) > 0


def test_a_terminal_job_asks_for_no_retry(server, server_client, key, token, me):
    existing = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"],
                         me, None, "completed")

    response = call(server_client, key, "GET", f"/v1/jobs/{existing}", token)

    assert "Retry-After" not in response.headers
    assert response.get_json()["terminal"] is True


def test_the_job_object_carries_every_required_member(server_client, key, token):
    job = create(server_client, key, token).get_json()

    body = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    for member in ("id", "state", "terminal", "state_changed_at", "design",
                   "jobname", "flow", "owner", "project", "created_at",
                   "submitted_at", "started_at", "finished_at", "archived_at",
                   "deleted_at", "error", "nodes", "progress"):
        assert member in body, member
    # ABSENT, never null, where the deployment serves no web UI: a null would
    # claim there is a portal and this job has no page.
    assert "web_url" not in body


def test_an_authenticated_response_is_never_cacheable(server_client, key, token):
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    assert response.headers["Cache-Control"] == "private, no-store"


###########################
# 16. list
###########################

def test_the_listing_is_newest_first(server_client, key, token):
    ids = [create(server_client, key, token, jobname=f"job{n}").get_json()["id"]
           for n in range(3)]

    body = call(server_client, key, "GET", "/v1/jobs", token).get_json()

    assert [item["id"] for item in body["items"]] == list(reversed(ids))
    # MINUS `nodes`: the listing is a collection, not a fan-out.
    assert "nodes" not in body["items"][0]


def test_the_listing_is_mine_only(server_client, key, token):
    from siliconcompiler.remote import dpop

    create(server_client, key, token)

    other_key = dpop.generate_key()
    other_token = login(server_client, other_key,
                        subject="machine:1001").get_json()["access_token"]

    body = call(server_client, other_key, "GET", "/v1/jobs", other_token).get_json()
    assert body["items"] == []


def test_paging_is_a_keyset_over_the_published_ordering(server_client, key, token):
    ids = [create(server_client, key, token, jobname=f"job{n}").get_json()["id"]
           for n in range(5)]

    first = call(server_client, key, "GET", "/v1/jobs?limit=2", token)
    assert len(first.get_json()["items"]) == 2
    assert 'rel="next"' in first.headers["Link"]

    seen = []
    response = first
    while True:
        seen.extend(item["id"] for item in response.get_json()["items"])
        link = response.headers.get("Link")
        if not link:
            break
        target = link.split(">", 1)[0].lstrip("<")
        response = call(server_client, key, "GET", target, token)

    assert seen == list(reversed(ids))


def test_the_link_header_is_absent_on_the_last_page(server_client, key, token):
    create(server_client, key, token)

    response = call(server_client, key, "GET", "/v1/jobs", token)

    assert "Link" not in response.headers


def test_a_made_up_cursor_is_refused(server_client, key, token):
    '''A cursor is only ever taken from a Link header. Continuing from a made-up
    position silently skips rows.'''
    response = call(server_client, key, "GET", "/v1/jobs?cursor=nonsense!!", token)

    assert response.status_code == 400
    assert slug(response) == "invalid-cursor"


def test_design_and_jobname_filter_exactly(server_client, key, token):
    create(server_client, key, token, design="gcd", jobname="nightly-1")
    create(server_client, key, token, design="picorv32", jobname="nightly-2")

    body = call(server_client, key, "GET", "/v1/jobs?design=gcd", token).get_json()
    assert [item["design"] for item in body["items"]] == ["gcd"]

    # Deliberately not a prefix search: these are free text, so a match operator
    # means a LIKE over user-controlled input.
    body = call(server_client, key, "GET", "/v1/jobs?jobname=nightly", token).get_json()
    assert body["items"] == []


def test_archived_is_the_one_filter_whose_default_is_not_everything(
        server, server_client, key, token, me):
    plain = create(server_client, key, token).get_json()["id"]
    archived = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"], me,
                         None, "completed",
                         archived_at="2026-01-01T00:00:00.000Z", archived_by=me)

    default = call(server_client, key, "GET", "/v1/jobs", token).get_json()
    assert [item["id"] for item in default["items"]] == [plain]

    only = call(server_client, key, "GET", "/v1/jobs?archived=true", token).get_json()
    assert [item["id"] for item in only["items"]] == [archived]


def test_an_unknown_state_filter_is_refused(server_client, key, token):
    response = call(server_client, key, "GET", "/v1/jobs?state=nearly", token)

    assert response.status_code == 400


###########################
# 18. cancel
###########################

def test_a_running_job_moves_to_cancelling(server_client, key, token,
                                           job_archive, dispatcher):
    '''🔴 not `cancelled` -- the scheduler writes the terminal state. This is
    the window where a 202 and a job object still reading `running` would be
    indistinguishable from the server having done nothing.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    assert response.status_code == 202
    assert response.get_json()["state"] == "cancelling"
    assert response.get_json()["terminal"] is False
    assert dispatcher.cancelled


def test_a_job_that_never_started_is_cancelled_outright(server_client, key, token):
    '''Nothing is running, so there is nothing to wind down and no `cancelling`
    in between.'''
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    assert response.get_json()["state"] == "cancelled"
    assert response.get_json()["terminal"] is True


def test_cancel_takes_no_body_at_all(server_client, key, token):
    '''Requiring one would make a Ctrl-C in a CLI impossible to express.'''
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    assert response.status_code == 202


def test_a_cancel_reason_is_recorded_where_the_portal_reads_it(
        server, server_client, key, token):
    job = create(server_client, key, token).get_json()

    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
         json={"reason": "superseded by run43"})

    rows = server.config["SC_STORE"].all(
        "SELECT * FROM job_state_transitions WHERE job_id = ?", (job["id"],))
    assert rows[-1]["reason"] == "superseded by run43"


def test_a_cancel_reason_is_bounded(server_client, key, token):
    '''User-controlled text that the portal renders and a CLI prints.'''
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                    json={"reason": "x" * 5000})

    assert response.status_code == 400


def test_cancel_is_idempotent(server_client, key, token):
    job = create(server_client, key, token).get_json()

    first = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    second = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    assert first.status_code == second.status_code == 202
    assert second.get_json()["state"] == "cancelled"


###########################
# 19. delete
###########################

def test_delete_refuses_a_job_that_is_still_spending(server_client, key, token,
                                                     job_archive, dispatcher):
    '''"delete it and its data" cannot mean "hide it and keep spending".'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    response = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert response.status_code == 409
    assert slug(response) == "job-state-conflict"


def test_delete_keeps_the_row_and_drops_the_bytes(server, server_client, key,
                                                  token, job_archive, dispatcher, me):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET state = 'cancelled' WHERE id = ?", (job["id"],))

    root = server.config["SC_JOBS"].job_root(me, job["id"])
    assert root.exists()

    response = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert response.status_code == 204
    assert not root.exists()

    # A `deleted` state was refused because it would erase whether the job had
    # completed, failed or been rejected -- the one fact you want when somebody
    # asks where their results went.
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "cancelled"
    assert read["deleted_at"]


def test_a_deleted_job_is_in_neither_listing(server_client, key, token):
    job = create(server_client, key, token).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert call(server_client, key, "GET", "/v1/jobs", token).get_json()["items"] == []
    assert call(server_client, key, "GET", "/v1/jobs?archived=true",
                token).get_json()["items"] == []


def test_delete_is_idempotent(server_client, key, token):
    job = create(server_client, key, token).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    first = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)
    second = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert first.status_code == second.status_code == 204


def test_the_audit_trail_survives_a_delete(server, server_client, key, token):
    '''An audit trail a user can erase by deleting the job is not an audit
    trail.'''
    job = create(server_client, key, token).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    rows = server.config["SC_STORE"].all(
        "SELECT * FROM job_state_transitions WHERE job_id = ?", (job["id"],))
    assert len(rows) >= 2


###########################
# Reconciliation
###########################

def test_a_job_the_scheduler_lost(server, server_client, key, token,
                                  job_archive, dispatcher):
    '''It is gone and it never said how it ended. Reported rather than polled
    for ever.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    dispatcher.alive = False

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("scheduler-lost")
    assert all(node["state"] == "cancelled" for node in read["nodes"])


def test_cannot_tell_is_not_the_same_as_gone(server, server_client, key, token,
                                             job_archive, dispatcher):
    '''Declaring a live job lost is the more expensive mistake.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    def explode(scheduler_job_id):
        raise OSError("the controller is not answering")
    dispatcher.is_alive = explode

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "queued"


def test_a_submit_key_reused_across_jobs_is_refused(server_client, key, token,
                                                    job_archive, dispatcher):
    '''Reusing one is the caller having failed to rotate a key, not a fault in
    this server -- so it is a refusal rather than a 500 out of the index that
    catches it.'''
    archive, digest, size = job_archive()
    first = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, first["id"], digest, size,
           idempotency_key="s1")

    # The same design and jobname, so the manifest still matches and the only
    # thing left to collide is the key.
    second = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, second["id"], digest, size,
                      idempotency_key="s1")

    assert response.status_code == 422
    assert slug(response) == "idempotency-key-reuse"


def test_a_descriptor_with_no_size_still_uploads(server_client, key, token,
                                                 job_archive, dispatcher):
    '''A sparse descriptor is legal. The grant then carries the deployment's
    ceiling, the upload is smaller than it, and the digest at submit is what
    settles what the bytes actually are.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token).get_json()

    assert int(grant["headers"]["content-length"]) > size

    assert put(server_client, grant, open(archive, "rb").read()).status_code == 200
    assert submit(server_client, key, token, job["id"], digest,
                  size).status_code == 202


def test_an_upload_past_the_ceiling_is_refused_as_it_arrives(
        server_client, key, token):
    '''Enforced on what has been written rather than on Content-Length, which is
    a claim the sender makes about a body it is still sending.'''
    job = create(server_client, key, token,
                 resources={"upload_bytes": 16}).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token).get_json()

    response = put(server_client, grant, b"x" * 4096)

    assert response.status_code == 413
    assert slug(response) == "upload-too-large"


def test_a_job_that_finished_while_we_looked_is_not_lost(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 "The run says it is going" and "the scheduler has never heard of it"
    are read at two different moments, and a run that finished in between
    satisfies both. The progress file in hand is stale and the scheduler's
    answer is fresh -- so the file is read once more before the job is
    declared lost.

    This is not theoretical: it fired on a real asicflow run, and everything
    reconcile does between the two readings widens the window.
    '''
    from siliconcompiler.remote.server import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = (server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0")
    progress = root / runspec.PROGRESS_FILENAME

    # What the poll reads first: still going.
    runspec.write_progress(progress, {
        "state": "running", "started_at": "2026-09-22T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"}}})

    # The scheduler has already forgotten it, and the run writes its result
    # while the server is between the two readings.
    def gone(scheduler_job_id):
        runspec.write_progress(progress, {
            "state": "completed",
            "started_at": "2026-09-22T10:00:00.000Z",
            "finished_at": "2026-09-22T10:01:00.000Z",
            "nodes": {"stepone/0": {"state": "completed", "exit_code": 0},
                      "steptwo/0": {"state": "completed", "exit_code": 0}}})
        return False
    dispatcher.is_alive = gone

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "completed"
    assert read["error"] is None


def test_a_job_that_really_is_gone_is_still_reported_lost(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''Reading the file twice must not turn a lost job into a hung one.'''
    from siliconcompiler.remote.server import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = (server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0")
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-22T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"}}})

    dispatcher.alive = False

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("scheduler-lost")


###########################
# Placing a job in a container
###########################

def digest(letter):
    return "sha256:" + letter * 64


def operator(store):
    return store.one("SELECT id FROM users WHERE issuer = 'operator'")["id"]


@pytest.fixture
def registry():
    """A curated registry, seeded before any server opens it.

    🔴 Before, and not after: a deployment that runs jobs in containers and has
    no live image holding SiliconCompiler does not start, which is the startup
    check doing exactly what it is for. One image, holding the framework and
    nothing else -- which is enough for the whole flow, because `nopflow`'s
    tool is `builtin`, nobody has registered that name, and a tool nobody
    registered raises no requirement.
    """
    import json
    import os

    from siliconcompiler.remote.server import images
    from siliconcompiler.remote.server.store import Store

    os.makedirs("container-datadir", exist_ok=True)
    with open("container-datadir/config.json", "w") as f:
        json.dump({"containers": True}, f)

    with Store("container-datadir/server.db") as store:
        with store.transaction():
            actor = store.upsert_user("operator", "someone@host")["id"]

        images.register_software(store, "siliconcompiler", "SiliconCompiler", actor)
        images.register_version(store, "siliconcompiler", "0.38.0", actor,
                                preference=10)
        images.register_image(store, "ghcr.io/x/sc:0.38.0", digest("a"),
                              [("siliconcompiler", "0.38.0")], actor)


@pytest.fixture
def container_server(registry):
    """A deployment that runs its jobs inside images it registered.

    Its own server rather than a flag on the shared one, because `containers`
    is read at startup: it decides what `GET /v1` advertises, so a value that
    changed under a running server would make two requests in the same second
    answer differently.
    """
    from siliconcompiler.remote.server.app import create_app

    return create_app("container-datadir", cluster="local")


@pytest.fixture
def container_client(container_server):
    return container_server.test_client()


@pytest.fixture
def container_token(container_client, key):
    return login(container_client, key).get_json()["access_token"]


@pytest.fixture
def container_dispatcher(container_server):
    fake = FakeDispatcher()
    container_server.config["SC_JOBS"]._dispatcher = fake
    return fake


def test_a_container_deployment_with_no_images_does_not_start():
    """🔴 Where phase 1's startup check finds its real home.

    With no fallback to this process's own version, an empty registry is a
    server on which nothing can be submitted -- and that is much cheaper to
    learn at startup than at somebody's first submit.
    """
    import json
    import os

    from siliconcompiler.remote.server.app import create_app

    os.makedirs("empty-registry", exist_ok=True)
    with open("empty-registry/config.json", "w") as f:
        json.dump({"containers": True}, f)

    with pytest.raises(RuntimeError, match="no runnable siliconcompiler"):
        create_app("empty-registry", cluster="local")


def test_submit_records_the_image_each_node_ran_in(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher):
    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                versions={"siliconcompiler": "0.38.0"})

    submit(container_client, key, container_token, job["id"], upload_digest, size)

    store = container_server.config["SC_STORE"]
    placed = store.one("SELECT image_id FROM jobs WHERE id = ?", (job["id"],))
    nodes = store.all("SELECT * FROM job_nodes WHERE job_id = ?", (job["id"],))

    assert placed["image_id"]
    assert [node["image_id"] for node in nodes] == [placed["image_id"]] * 2


def test_the_node_is_told_a_digest_and_never_a_tag(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher):
    """🔴 Rebuilding `sc:0.38.0` must not change what a job already accepted
    runs, which is only true if the pinned form is what reaches the manifest."""
    from siliconcompiler import Project

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                versions={"siliconcompiler": "0.38.0"})
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    manifest = container_dispatcher.submitted[0][2]
    project = Project.from_manifest(filepath=str(manifest))

    assert project.option.scheduler.get_name(step="stepone", index="0") == "docker"
    assert project.option.scheduler.get_queue(step="stepone", index="0") == \
        f"ghcr.io/x/sc@{digest('a')}"


def test_a_tool_with_no_image_fails_the_whole_submit(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher):
    """🔴 Before anything runs, which is the correct direction: the alternative
    is a job that queues, dispatches and dies on node thirty-one with the
    cluster already paid for."""
    from siliconcompiler.remote.server import images

    store = container_server.config["SC_STORE"]

    # The operator takes the claim on and never puts it in an image, which is
    # the whole condition: this deployment now says it curates `builtin` and
    # cannot place a node that needs it.
    images.register_software(store, "builtin", "SiliconCompiler builtins",
                             operator(store))
    images.register_version(store, "builtin", "1.0", operator(store))

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size)

    response = submit(container_client, key, container_token, job["id"],
                      upload_digest, size)

    assert response.status_code == 422
    assert slug(response) == "unsatisfiable-request"
    assert response.get_json()["resource_kind"] == "tool"
    assert response.get_json()["resource"] == "builtin"
    assert not container_dispatcher.submitted

    read = call(container_client, key, "GET", f"/v1/jobs/{job['id']}",
                container_token).get_json()
    assert read["state"] == "rejected"


def test_a_version_with_no_image_is_never_advertised(container_server, container_client):
    """So a client is refused before it uploads, rather than told yes and
    refused at submit."""
    from siliconcompiler.remote.server import images

    store = container_server.config["SC_STORE"]
    images.register_version(store, "siliconcompiler", "0.38.1", operator(store),
                            preference=99)

    software = container_client.get("/v1").get_json()["software"]

    assert software["siliconcompiler"] == ["0.38.0"]


def test_a_deployment_that_runs_no_containers_places_nothing(
        server, server_client, key, token, job_archive, dispatcher):
    """⚠️ NULL rather than a default image. `job_nodes.image_id` is what that
    node actually ran in, so writing one for a node that ran on the host would
    record something that did not happen."""
    archive, upload_digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], upload_digest, size)

    store = server.config["SC_STORE"]

    assert store.one("SELECT image_id FROM jobs WHERE id = ?",
                     (job["id"],))["image_id"] is None
    assert all(node["image_id"] is None for node in store.all(
        "SELECT image_id FROM job_nodes WHERE job_id = ?", (job["id"],)))


def test_a_cluster_gets_a_bundle_and_never_a_partition(
        container_server, container_client, key, container_token, job_archive,
        monkeypatch):
    '''🔴 On a cluster Slurm places the container, and `scheduler,queue` is its
    PARTITION -- so an image reference there would submit every node to a
    partition named after a container.'''
    from siliconcompiler import Project
    from siliconcompiler.remote.server import runspec

    from siliconcompiler.remote.server import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake

    # The unpack itself needs skopeo and umoci, which are the cluster's
    # business and not this test's: what is under test is where the bundle is
    # and what the dispatcher is handed.
    monkeypatch.setattr(
        images, "stage_bundle",
        lambda root, ref, digest, mounts=(): images.bundle_path(root, digest))

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                versions={"siliconcompiler": "0.38.0"})
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    manifest = fake.submitted[0][2]
    project = Project.from_manifest(filepath=str(manifest))
    scheduler = project.option.scheduler

    assert scheduler.get_name(step="stepone", index="0") == "slurm"
    assert scheduler.get_queue(step="stepone", index="0") is None

    options = scheduler.get_options(step="stepone", index="0")
    bundle = options[options.index("--container") + 1]
    # Content-addressed and outside any user's tree: the same digest is the
    # same read-only root filesystem for everybody who runs it.
    assert bundle.endswith(digest("a").replace("sha256:", ""))
    assert "/images/" in bundle
    assert "/users/" not in bundle

    # And the run is told where to get the bytes, which the bundle path alone
    # cannot say.
    sources, mounts = runspec.read_images(
        manifest.parent / runspec.IMAGES_FILENAME)
    assert sources[bundle] == f"ghcr.io/x/sc@{digest('a')}"
    # The data directory is always mounted: every path in a job's manifest is
    # under it, and a container's root filesystem is the image's.
    assert any(path.endswith("container-datadir") for path in mounts)

    # 🔴 And the batch job itself runs in the framework image, which is what
    # makes version matching real: the process that INTERPRETS the manifest is
    # the SiliconCompiler the job asked for rather than the cluster's own.
    assert fake.handed["image"] == bundle


def test_the_orchestrator_goes_to_its_own_queue(
        container_server, container_client, key, container_token, job_archive,
        monkeypatch):
    '''🔴 The batch job coordinates; it does not compute.

    Every node is submitted from it as a job of its own, so it holds one core
    for the length of the flow and uses almost none of it. On a compute
    partition that is a node slot doing nothing.
    '''
    from siliconcompiler.remote.server import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake
    container_server.config["SC_CONFIG"]._values["batch_queue"] = "coordinator"
    monkeypatch.setattr(
        images, "stage_bundle",
        lambda root, ref, digest, mounts=(): images.bundle_path(root, digest))

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size)
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    assert fake.handed["queue"] == "coordinator"


def test_no_queue_leaves_it_to_the_cluster(
        server, server_client, key, token, job_archive, dispatcher):
    '''None is the default, and it is correct for a deployment that has not
    made a partition for this.'''
    archive, upload_digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], upload_digest, size)

    assert dispatcher.handed == {"image": None, "queue": None}


###########################
# Reading somebody else's manifest
###########################

def test_a_manifest_from_a_newer_schema_is_refused(
        server_client, key, token, nop_project, job_archive, dispatcher):
    """🔴 Reading a manifest is only BACKWARDS compatible, and the failure in
    the other direction is silent.

    SiliconCompiler migrates an older manifest; a newer one holds keys this
    schema does not have, which are dropped, and values whose type or legal
    values changed, which are replaced by defaults. The read "either fails or
    quietly returns something other than what was written" -- and this server
    decides the node list, the flow and the limits from what it read. A warning
    is right for a scheduler that can rerun the node, and wrong for a server
    admitting somebody else's work.
    """
    import json
    import os

    from siliconcompiler.utils.paths import jobdir

    root = jobdir(nop_project)
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{nop_project.name}.pkg.json")
    nop_project.write_manifest(path)

    with open(path) as f:
        body = json.load(f)
    body["schemaversion"]["node"]["default"]["default"]["value"] = "99.0.0"

    # A second member of the same name, which is what extraction ends up with:
    # the builder writes the real manifest itself, so this is how a manifest
    # from the future gets into the archive.
    archive, upload_digest, size = job_archive(
        extra={f"{nop_project.name}.pkg.json": json.dumps(body).encode()})
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], upload_digest, size)

    assert response.status_code == 422
    assert slug(response) == "version-skew"
    assert "only backwards compatible" in response.get_json()["detail"]
    assert not dispatcher.submitted

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}",
                token).get_json()
    assert read["state"] == "rejected"


def test_a_server_may_not_advertise_what_it_cannot_read(registry):
    '''🔴 The framework image decides what RUNS a flow; it does not decide what
    READS it.

    Submit re-derives the flow from the uploaded manifest in the API process,
    with the API process's SiliconCompiler -- so advertising a newer version is
    a promise that ends in a refusal AFTER the upload. Caught when an operator
    restarts the server they just configured, which is the cheapest moment
    there is.
    '''
    from siliconcompiler.remote.server import images
    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.store import Store

    with Store("container-datadir/server.db") as store:
        actor = operator(store)
        images.register_version(store, "siliconcompiler", "99.0.0", actor)
        images.register_image(store, "ghcr.io/x/future:99", digest("f"),
                              [("siliconcompiler", "99.0.0")], actor)

    with pytest.raises(RuntimeError, match="which it cannot read"):
        create_app("container-datadir", cluster="local")
