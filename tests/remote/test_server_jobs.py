import json

from pathlib import Path

import pytest

from conftest import FakeDispatcher, call, job_after, login, read, run_manifest, slug, stranger


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.state.store import now                  # noqa: E402


# The integration rig, in process: every ordering rule the contract calls
# normative, since a canned answer cannot get one wrong.


def wants(sc=None, tools=None):
    '''A bucketed `requested_versions`, every value a list: the python set is
    held by ONE image, and a tool is satisfied per node.'''
    def listed(value):
        return value if isinstance(value, list) else [value]

    return {"python": {"siliconcompiler": listed(f"=={sc}" if sc[0].isdigit() else sc)}
            if sc else {},
            "tools": {name: listed(value) for name, value in (tools or {}).items()}}


# What goes under `descriptor`; anything else is a top-level member.
DESCRIPTOR = ("flow", "node_count", "needs", "requested_versions", "sources")


def create(client, key, token, **body):
    body.setdefault("design", "gcd")
    body.setdefault("jobname", "job0")
    headers = {}
    if "idempotency_key" in body:
        headers["Idempotency-Key"] = body.pop("idempotency_key")
    descriptor = {name: body.pop(name) for name in DESCRIPTOR if name in body}
    if descriptor:
        body["descriptor"] = descriptor
    return call(client, key, "POST", "/v1/jobs", token, json=body, headers=headers)


def created_in_order(client, key, token, count):
    '''``count`` job ids, a few milliseconds apart: the listing orders by
    `created_at`, and a tie falls to the id, a UUIDv4.'''
    import time

    ids = []
    for n in range(count):
        if ids:
            time.sleep(0.002)
        ids.append(create(client, key, token, jobname=f"job{n}").get_json()["id"])
    return ids


def put(client, grant, data):
    return client.put(grant["url"].split("http://localhost", 1)[1], data=data)


# A digest for a grant whose bytes the test never submits.
ANY_DIGEST = "sha256:" + "0" * 64


def sized(size, digest=ANY_DIGEST):
    return {"size_bytes": size, "digest": digest}


def grant_for(archive):
    '''The grant request for an archive: its size and its digest.'''
    import hashlib

    data = open(archive, "rb").read()
    return {"size_bytes": len(data), "digest": f"sha256:{hashlib.sha256(data).hexdigest()}"}


def grant(client, key, token, job_id, body=None):
    return call(client, key, "POST", f"/v1/jobs/{job_id}/upload-grant", token, json=body)


def stage(client, key, token, archive, size, **body):
    '''A job with its bytes uploaded, ready to submit.'''
    job = create(client, key, token, **body).get_json()
    granted = grant(client, key, token, job["id"],
                    dict(grant_for(archive), size_bytes=size)).get_json()
    put(client, granted, open(archive, "rb").read())
    return job


def submit(client, key, token, job_id, digest=None, size=None, **extra):
    '''Submit takes no body (surface §15): ``digest`` and ``size`` are taken
    for symmetry with `stage` and never sent; ``extra`` is, to test refusal.'''
    headers = {}
    if "idempotency_key" in extra:
        headers["Idempotency-Key"] = extra.pop("idempotency_key")
    return call(client, key, "POST", f"/v1/jobs/{job_id}/submit", token,
                json=extra, headers=headers)


def submitted(client, key, token, built, **body):
    '''Stage a `job_archive` result and submit it: the job, and the answer.'''
    archive, _, size = built
    job = stage(client, key, token, archive, size, **body)
    return job, submit(client, key, token, job["id"])


def cancel(client, key, token, job_id, **body):
    return call(client, key, "POST", f"/v1/jobs/{job_id}/cancel", token, json=body)


def listing(client, key, token, query=""):
    path = f"/v1/jobs?{query}" if query else "/v1/jobs"
    return [item["id"] for item in call(client, key, "GET", path, token).get_json()["items"]]


STARTED, FINISHED = "2026-09-23T10:00:00.000Z", "2026-09-23T10:01:00.000Z"


def report(server, me, job, state="running", nodes=None, **progress):
    '''Write the run's progress file, as the runner does: a running one beats
    now unless told otherwise, and a finished one has finished.'''
    from siliconcompiler.remote.server.running import runspec

    progress.setdefault("heartbeat" if state == "running" else "finished_at",
                        now() if state == "running" else FINISHED)
    if nodes is None:
        nodes = {"stepone/0": {"state": "running"}, "steptwo/0": {"state": "pending"}}
    runspec.write_json(
        server.config["SC_JOBS"].job_root(me, job["id"]) / runspec.PROGRESS_FILENAME,
        {"state": state, "started_at": STARTED, "nodes": nodes, **progress})


def running(server, server_client, key, token, job_archive, me):
    '''A submitted job whose run has reported its nodes as started.'''
    job, _ = submitted(server_client, key, token, job_archive())
    report(server, me, job)
    return job


COMPLETED = {"stepone/0": {"state": "completed", "exit_code": 0},
             "steptwo/0": {"state": "completed", "exit_code": 0}}


def settles_between_readings(server, me, job, dispatcher):
    '''The scheduler has forgotten the job, and its run writes the result
    while the server is between its two readings of the progress file.'''
    def gone(scheduler_job_id):
        report(server, me, job, "completed", COMPLETED)
        return False
    dispatcher.is_alive = gone


###########################
# 13. create
###########################

def test_create_returns_the_job_object_and_a_location(server_client, key, token):
    '''`project` is null on a personal job, never absent; no `upload` member,
    the grant being its own endpoint.'''
    response = create(server_client, key, token)

    assert response.status_code == 201
    body = response.get_json()
    assert (body["state"], body["terminal"], body["project"]) == ("created", False, None)
    assert response.headers["Location"] == f"/v1/jobs/{body['id']}"
    assert "upload" not in body and "upload_sources" not in body


def test_the_listing_is_newest_first_by_creation_never_by_id(
        server_client, key, token, monkeypatch):
    '''By `created_at`, the id only breaking a tie (surface §6): here each id
    sorts below the one before it. A collection, so MINUS `nodes`.'''
    import types
    import uuid

    from siliconcompiler.remote.server.jobs import create as creating

    minted = iter([uuid.UUID(int=n << 64) for n in (3, 2, 1)])
    monkeypatch.setattr(creating, "uuid", types.SimpleNamespace(uuid4=lambda: next(minted)))

    ids = created_in_order(server_client, key, token, 3)
    assert ids == sorted(ids, reverse=True)

    items = call(server_client, key, "GET", "/v1/jobs", token).get_json()["items"]
    assert [item["id"] for item in items] == list(reversed(ids))
    assert "nodes" not in items[0]


_ABSENT = object()


@pytest.mark.parametrize("change", [
    # Authoritative: nothing in a manifest names either.
    {"design": _ABSENT}, {"jobname": _ABSENT},
    # Each becomes a path segment under the job's own root.
    *[{"design": name} for name in ("../etc", "a/b", "", "." * 200, "-leading")],
    # Strict on requests: unknown or misshapen is refused, never ignored.
    {"versions": {"python": {}}},                      # gone: `requested_versions` pins
    {"resources": {"upload_bytes": 10}},               # gone: the grant's size
    {"descriptor": {"resources": {"upload_bytes": 10}}},
    {"descriptor": {"flow": {"name": "f", "tools": ["yosys"]}}},
    {"descriptor": {"requires": {"python": {}}}},      # pre-D289 names, none kept
    {"descriptor": {"flow": {"name": "asicflow", "nodes": 3}}},
    {"descriptor": {"node_count": "3"}},
    {"extra": 1},
    # `run_hash` is top-level (D160), and 1 to 128 printable ASCII.
    {"descriptor": {"run_hash": "abc"}},
    *[{"run_hash": value} for value in ("", "x" * 129, "ok✓", "tab\there", 7)],
])
def test_a_malformed_create_is_refused(server_client, key, token, change):
    body = {name: value for name, value in {"design": "gcd", "jobname": "job0",
                                            **change}.items() if value is not _ABSENT}

    response = call(server_client, key, "POST", "/v1/jobs", token, json=body)

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_a_project_is_refused_rather_than_ignored(server_client, key, token):
    '''Dropped, it makes a job the caller believes shared and nobody else can
    see. Permanent, so a client stops offering the picker.'''
    response = create(server_client, key, token, project="rocket-v2")

    assert (response.status_code, slug(response)) == (501, "feature-unsupported")
    assert response.get_json()["feature"] == "projects"


def test_the_descriptor_refuses_before_the_bytes_move(server_client, key, token):
    response = create(server_client, key, token, flow="asicflow", node_count=10 ** 9)

    assert (response.status_code, slug(response)) == (403, "node-limit-exceeded")
    assert response.get_json()["limit"] == "max_job_nodes"


def test_a_requirement_is_always_a_list(server_client, key, token):
    '''As SiliconCompiler's own is: a list of alternatives, one per task.'''
    bare = create(server_client, key, token,
                  requested_versions={"python": {"siliconcompiler": "==0.38.0"}, "tools": {}})
    listed = create(server_client, key, token, jobname="job1",
                    requested_versions={"python": {}, "tools": {"yosys": []}})

    assert bare.status_code == 400 and "list" in bare.get_json()["detail"]
    assert listed.status_code == 201


@pytest.mark.parametrize("source", [
    "git+ssh://git@example.com/ip.git",
    "https://alice:ghp_TOKEN@example.com/ip.tar.gz",
    "git+https+private://ghp_TOKEN@example.com/ip.git"])
def test_a_source_carrying_userinfo_is_refused_at_create_by_its_keypath(
        server, server_client, key, token, caplog, source):
    '''Surface D310: refused, never stripped, naming the keypath and never the
    value, which is neither stored nor logged.'''
    import logging

    caplog.set_level(logging.DEBUG)
    response = create(server_client, key, token, sources=[
        {"keypath": ["library", "ip", "dataroot", "ip"], "source": source,
         "private": "private" in source}])

    assert (response.status_code, slug(response)) == (400, "invalid-request")
    body = response.get_json()
    assert "library,ip,dataroot,ip" in body["detail"]
    secret = source.split("://", 1)[1].split("@", 1)[0]
    assert secret not in json.dumps(body) and secret not in caplog.text
    assert server.config["SC_STORE"].one("SELECT count(*) AS n FROM jobs")["n"] == 0


def test_a_need_the_server_lacks_is_refused_at_create_naming_it(server_client, key, token):
    '''Before the upload, not at submit after it.'''
    lacking = create(server_client, key, token, needs=["python.env"])
    known = create(server_client, key, token, jobname="job1", needs=["logs.stream"])

    assert lacking.status_code == 501
    assert (slug(lacking), lacking.get_json()["feature"]) == \
        ("feature-unsupported", "python.env")
    assert known.status_code == 201


def test_a_sparse_descriptor_is_never_refused_for_being_sparse(server_client, key, token):
    '''No field is required: a missing one skips the check it would answer.'''
    assert create(server_client, key, token, descriptor={}).status_code == 201


def test_pending_uploads_is_a_ceiling_naming_the_jobs_holding_it(
        server, server_client, key, token):
    server.config["SC_CONFIG"].limits["pending_uploads"] = 1
    held = create(server_client, key, token).get_json()

    refused = create(server_client, key, token, jobname="job1")

    assert (refused.status_code, slug(refused)) == (429, "limit-exceeded")
    assert refused.get_json()["limit"] == "pending_uploads"
    assert refused.get_json()["job_ids"] == [held["id"]]
    assert refused.headers["Retry-After"]           # without it, a client guesses


###########################
# Idempotency-Key
###########################

def test_the_same_key_and_the_same_body_is_the_same_job(server_client, key, token):
    first = create(server_client, key, token, idempotency_key="k1")
    second = create(server_client, key, token, idempotency_key="k1")

    # A replayed create is `201`, with the original body.
    assert first.status_code == second.status_code == 201
    assert first.get_json() == second.get_json()


def test_the_same_key_with_a_different_body_is_refused(server_client, key, token):
    '''Returning the first job would answer a question not asked.'''
    create(server_client, key, token, idempotency_key="k1")
    response = create(server_client, key, token, jobname="other", idempotency_key="k1")

    assert (response.status_code, slug(response)) == (422, "idempotency-key-reuse")


def test_a_refused_create_binds_no_key(server, server_client, key, token):
    '''A refusal has no side effect, so a retry is evaluated afresh (surface
    §6; database D144).'''
    server.config["SC_CONFIG"].limits["pending_uploads"] = 1
    held = create(server_client, key, token, jobname="held").get_json()

    refused = create(server_client, key, token, idempotency_key="k1")
    assert (refused.status_code, slug(refused)) == (429, "limit-exceeded")

    cancel(server_client, key, token, held["id"])
    again = create(server_client, key, token, idempotency_key="k1")

    assert again.status_code == 201, again.get_json()


def test_one_users_key_does_not_collide_with_anothers(server_client, key, token):
    other_key, other_token = stranger(server_client)

    mine = create(server_client, key, token, idempotency_key="k1").get_json()
    theirs = create(server_client, other_key, other_token, idempotency_key="k1").get_json()

    assert mine["id"] != theirs["id"]


def test_a_key_older_than_a_day_is_forgotten(server, server_client, key, token):
    first = create(server_client, key, token, idempotency_key="old").get_json()
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET created_at = '2020-01-01T00:00:00.000Z' WHERE id = ?",
        (first["id"],))

    again = create(server_client, key, token, idempotency_key="old")

    assert again.status_code == 201
    assert again.get_json()["id"] != first["id"]


@pytest.mark.parametrize("what", ["create", "submit"])
def test_a_retry_while_the_original_is_handled_is_in_progress(
        server, server_client, key, token, job_archive, dispatcher, me, what):
    '''Only a final answer binds a key: a retry meanwhile is `409`,
    `in_progress`, with `Retry-After`.'''
    server.config["SC_JOBS"]._in_flight.add((me, what, "k-busy"))

    if what == "create":
        response = create(server_client, key, token, idempotency_key="k-busy")
    else:
        archive, digest, size = job_archive()
        job = stage(server_client, key, token, archive, size)
        response = submit(server_client, key, token, job["id"], idempotency_key="k-busy")

    assert (response.status_code, slug(response)) == (409, "job-state-conflict")
    assert response.get_json()["reason"] == "in_progress"
    assert int(response.headers["Retry-After"]) >= 1


###########################
# Job reuse
###########################

@pytest.fixture
def reuses(server):
    '''A deployment advertising `jobs.reuse`, which this one does not by default.'''
    config = server.config["SC_CONFIG"]
    config._values["features"] = list(config["features"]) + ["jobs.reuse"]


@pytest.fixture
def container_reuses(container_server):
    config = container_server.config["SC_CONFIG"]
    config._values["features"] = list(config["features"]) + ["jobs.reuse"]


def reuse_job(jobs, store, user_id, run_hash, state, declared=None, **columns):
    '''A finished job with a hash, written straight into the store, with the
    `job_identity` the lookup is keyed on.'''
    import uuid

    from siliconcompiler.remote.server.software import images

    image = images.job_image_for(store, declared or {}) \
        if jobs._config["containers"] else None
    job_id = str(uuid.uuid4())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "                  run_hash, job_identity, manifest_pdk) "
        "VALUES (?, ?, ?, 'gcd', 'old', '{}', ?, ?, 'none')",
        (job_id, user_id, state, run_hash,
         jobs._identity(run_hash, declared or {}, image=image)))
    if columns:
        # One statement: the archived_at/archived_by CHECK is on the pair.
        assignments = ", ".join(f"{column} = ?" for column in columns)
        store.execute(f"UPDATE jobs SET {assignments} WHERE id = ?",
                      (*columns.values(), job_id))
    return job_id


def reused(server, me, state="completed", run_hash="hash-1", **columns):
    return reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"], me, run_hash,
                     state, **columns)


@pytest.mark.parametrize("state,returned", [
    ("completed", True),
    ("failed", True),         # the hash covers the environment, so it is a result
    ("rejected", False),      # an entitlement is the person's, at a moment
    ("cancelled", False),     # user interaction, not a result
    ("abandoned", False),
    ("running", False),       # nothing to return yet
])
def test_which_states_job_reuse_returns(server, server_client, key, token, me,
                                        state, returned, reuses):
    existing = reused(server, me, state)

    response = create(server_client, key, token, run_hash="hash-1")

    # 200, not 201: a 201 carrying an old id is indistinguishable from a new one.
    assert response.status_code == (200 if returned else 201)
    assert (response.get_json()["id"] == existing) is returned


def test_an_archived_job_or_an_omitted_hash_runs_anew(server, server_client, key, token,
                                                      me, reuses):
    '''Archiving is how a person says stop handing me that result, with no
    endpoint for it; omitting the hash is a script's escape hatch.'''
    archived = reused(server, me, archived_at="2026-01-01T00:00:00.000Z", archived_by=me)
    plain = reused(server, me, run_hash="hash-2")

    for response in (create(server_client, key, token, run_hash="hash-1"),
                     create(server_client, key, token, jobname="job1")):
        assert response.status_code == 201
        assert response.get_json()["id"] not in (archived, plain)


def test_the_lookup_is_owner_scoped(server, server_client, key, token, reuses):
    '''The whole safety argument: a global cache would hand anyone who can
    present a derivation whatever anyone else had run.'''
    other_key, other_token = stranger(server_client)
    theirs = reused(server, call(server_client, other_key, "GET", "/v1/me",
                                 other_token).get_json()["id"])

    response = create(server_client, key, token, run_hash="hash-1")

    assert response.status_code == 201
    assert response.get_json()["id"] != theirs


def test_without_jobs_reuse_a_hash_is_validated_and_ignored(
        server, server_client, key, token, me):
    '''Not advertised here, so create is always a 201, even for the hash of a
    finished job.'''
    assert "jobs.reuse" not in server.config["SC_CONFIG"]["features"]
    existing = reused(server, me)

    response = create(server_client, key, token, run_hash="hash-1")

    assert response.status_code == 201
    assert response.get_json()["id"] != existing
    stored = server.config["SC_STORE"].one(
        "SELECT run_hash, job_identity FROM jobs WHERE id = ?", (response.get_json()["id"],))
    assert (stored["run_hash"], stored["job_identity"]) == ("hash-1", None)


###########################
# 14. upload-grant, and the signed PUT
###########################

def test_the_grant_fixes_the_size_and_a_re_issue_repeats_it(server_client, key, token):
    '''`200`, since re-issue is the point; the first grant fixes the size
    (D125) and a re-issue cannot widen it. The job is now `awaiting_input`.'''
    job = create(server_client, key, token).get_json()

    first = grant(server_client, key, token, job["id"], sized(4096))
    again = grant(server_client, key, token, job["id"], sized(4096))
    widened = grant(server_client, key, token, job["id"], sized(8192))

    for response in (first, again):
        body = response.get_json()
        assert response.status_code == 200
        assert (body["method"], body["headers"]["content-length"]) == ("PUT", "4096")
        assert body["url"] and body["expires_at"]
    assert (widened.status_code, slug(widened)) == (409, "job-state-conflict")
    body = read(server_client, key, token, job["id"])
    assert (body["state"], body["terminal"]) == ("awaiting_input", False)


def test_a_grant_without_its_size_is_refused(server_client, key, token):
    job = create(server_client, key, token).get_json()

    response = grant(server_client, key, token, job["id"])

    assert (response.status_code, slug(response)) == (400, "invalid-request")


@pytest.mark.parametrize("ceiling,size", [(None, 1 << 40), (1000, 1001)])
def test_an_upload_over_the_ceiling_is_refused_at_the_grant(
        server, server_client, key, token, ceiling, size):
    '''At the grant, which fixes the size, before any byte moves; the ceiling
    bounds a job's uploads together.'''
    if ceiling:
        server.config["SC_CONFIG"].limits["max_upload_bytes"] = ceiling
    job = create(server_client, key, token).get_json()

    response = grant(server_client, key, token, job["id"], sized(size))

    assert (response.status_code, slug(response)) == (413, "upload-too-large")
    assert response.get_json()["limit"] == "max_upload_bytes"


def test_no_grant_for_a_job_that_is_past_it(server, server_client, key, token, me):
    response = grant(server_client, key, token, reused(server, me, run_hash=None),
                     sized(4096))

    assert (response.status_code, slug(response)) == (409, "job-state-conflict")


def test_the_signature_is_the_credential(server_client, key, token, job_archive, dispatcher):
    '''No Authorization and no proof, as a presigned URL is; and a descriptor
    with no size still uploads, the size being the grant's (D125).'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    granted = grant(server_client, key, token, job["id"], sized(size, digest)).get_json()
    assert int(granted["headers"]["content-length"]) == size

    response = put(server_client, granted, open(archive, "rb").read())

    assert response.status_code == 200 and response.get_json()["size_bytes"] == size
    assert submit(server_client, key, token, job["id"]).status_code == 202


def test_an_unsigned_or_altered_upload_url_is_refused(server_client, key, token, job_archive):
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    granted = grant(server_client, key, token, job["id"], sized(size, digest)).get_json()
    widened = granted["url"].replace(f"max_bytes={size}", "max_bytes=999999999")

    assert server_client.put(widened.split("http://localhost", 1)[1],
                             data=b"x" * 100).status_code == 400
    assert server_client.put(f"/storage/upload/{job['id']}", data=b"x").status_code == 400


def test_an_upload_past_the_ceiling_is_refused_as_it_arrives(server_client, key, token):
    '''On what has been written, not on Content-Length, a claim about a body
    still being sent.'''
    job = create(server_client, key, token).get_json()
    granted = grant(server_client, key, token, job["id"], sized(16)).get_json()

    response = put(server_client, granted, b"x" * 4096)

    assert (response.status_code, slug(response)) == (413, "upload-too-large")


###########################
# 15. submit
###########################

def test_submit_runs_the_job(server, server_client, key, token, job_archive, dispatcher):
    '''`staging` always, since the request only matched the digest; then
    `queued`, every node pending, the edges rows a page draws the DAG from.'''
    job, response = submitted(server_client, key, token, job_archive())

    assert response.status_code == 202
    assert (response.get_json()["state"], response.get_json()["state_reason"]) == \
        ("staging", "unpacking the upload")
    body = job_after(server_client, key, token, response)
    assert body["state"] == "queued" and "state_reason" not in body
    assert [entry["state"] for entry in body["transitions"]] == \
        ["created", "awaiting_input", "staging", "queued"]
    assert body["submitted_at"] and body["flow"] == "nopflow"
    assert body["progress"]["total_count"] == 2
    assert {node["step"] for node in body["nodes"]} == {"stepone", "steptwo"}
    assert all(node["state"] == "pending" for node in body["nodes"])
    assert dispatcher.submitted
    edges = server.config["SC_STORE"].all(
        "SELECT * FROM job_node_edges WHERE job_id = ?", (job["id"],))
    assert [(row["from_step"], row["to_step"]) for row in edges] == [("stepone", "steptwo")]


@pytest.mark.parametrize("sent", ["zeros", "short"])
def test_a_digest_mismatch_refuses_before_anything_is_extracted(
        server, server_client, key, token, job_archive, dispatcher, me, sent):
    '''The order is normative: getting it wrong opens an archive bomb. A
    refusal of the request, not of the archive, so the job still waits and the
    bytes the grant was issued for then submit it.'''
    archive, digest, size = job_archive()
    data = open(archive, "rb").read()
    job = create(server_client, key, token).get_json()
    granted = grant(server_client, key, token, job["id"], sized(size, digest)).get_json()
    put(server_client, granted, b"\0" * size if sent == "zeros" else data[: size // 2])

    response = submit(server_client, key, token, job["id"])

    assert (response.status_code, slug(response)) == (422, "upload-digest-mismatch")
    assert "the grant bound" in response.get_json()["detail"]
    assert not server.config["SC_JOBS"].job_root(me, job["id"]).exists()
    body = read(server_client, key, token, job["id"])
    assert (body["state"], body["error"]) == ("awaiting_input", None)

    put(server_client, granted, data)
    again = submit(server_client, key, token, job["id"])
    assert again.status_code == 202
    assert job_after(server_client, key, token, again)["state"] == "queued"


@pytest.mark.parametrize("body,status", [(None, 202), ({}, 202), ("bytes", 400),
                                         ("digest", 400)])
def test_submit_takes_no_body_and_ignores_nothing(server_client, key, token,
                                                  job_archive, dispatcher, body, status):
    '''Surface §15 (D277): sent empty or as `{}` (D306), and a member is
    refused, the digest a client used to send included.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    if isinstance(body, str):
        body = {body: {"bytes": size, "digest": digest}[body]}

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/submit", token,
                    **({} if body is None else {"json": body}))

    assert response.status_code == status, response.get_json()
    if status == 400:
        assert slug(response) == "invalid-request"


def test_an_archive_violation_is_published_on_the_job_naming_the_rule(
        server_client, key, token, job_archive, dispatcher):
    '''`detail` too, so whoever reads the job later learns what the
    submitter would have.'''
    _, response = submitted(server_client, key, token,
                            job_archive(extra={"../escape": b"owned"}))

    assert response.status_code == 202
    body = job_after(server_client, key, token, response)
    assert body["state"] == "rejected"
    assert body["error"]["type"].endswith("archive-rejected")
    assert (body["error"]["status"], body["error"]["reason"]) == (422, "traversal")
    assert body["error"]["detail"]


def test_a_manifest_that_is_not_where_it_was_declared(server_client, key, token,
                                                      job_archive, dispatcher):
    _, response = submitted(server_client, key, token, job_archive(), jobname="somethingelse")

    assert response.status_code == 202
    assert job_after(server_client, key, token,
                     response)["error"]["type"].endswith("declared-mismatch")


def test_submitting_with_nothing_uploaded(server_client, key, token):
    job = create(server_client, key, token).get_json()
    grant(server_client, key, token, job["id"], sized(4096))

    response = submit(server_client, key, token, job["id"])

    assert (response.status_code, slug(response)) == (409, "job-state-conflict")


def test_a_replayed_submit_answers_the_original_202(server_client, key, token,
                                                    job_archive, dispatcher):
    '''The original body, `staging` and all, whatever the job did since
    (surface §6), and dispatched once.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    first = submit(server_client, key, token, job["id"], idempotency_key="s1")
    again = submit(server_client, key, token, job["id"], idempotency_key="s1")

    assert (first.status_code, again.status_code) == (202, 202)
    assert again.get_json() == first.get_json()
    assert again.get_json()["state"] == "staging"
    assert len(dispatcher.submitted) == 1


def test_a_submit_key_reused_across_jobs_is_refused(server_client, key, token,
                                                    job_archive, dispatcher):
    '''The caller failing to rotate a key: a refusal, not a 500 from the index.
    The same design and jobname, so only the key collides.'''
    archive, digest, size = job_archive()
    first = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, first["id"], idempotency_key="s1")

    second = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, second["id"], idempotency_key="s1")

    assert (response.status_code, slug(response)) == (422, "idempotency-key-reuse")


@pytest.mark.parametrize("member,named", [
    ("sc-server-progress.json", "sc-server-progress.json"),
    ("sc_configs/sc_slurm_stepone_0.sh", "sc_configs"),
])
def test_a_member_the_first_archive_does_not_carry_is_unrequested(
        server_client, key, token, job_archive, dispatcher, member, named):
    '''A planted progress file, or the old client's `sc_configs/` (Slurm's
    scripts): the server's own files live above the tree an upload expands into.'''
    _, response = submitted(server_client, key, token, job_archive(extra={
        member: b'{"state": "completed", "nodes": {}}'}))

    body = job_after(server_client, key, token, response)
    assert body["state"] == "rejected"
    assert body["error"]["reason"] == "unrequested_member"
    assert named in body["error"]["detail"]
    assert not dispatcher.submitted


def test_an_asic_project_with_no_pdk_is_unresolved(server_client, key, token,
                                                   job_archive, dispatcher, gcd_design):
    '''The PDK fails closed where the class has one; a class with none
    resolves to 'none', as every nopflow job here does.'''
    import os

    from siliconcompiler import ASIC, Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    project.set_flow(flow)
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(os.path.abspath("build"))

    _, response = submitted(server_client, key, token, job_archive(project))

    body = job_after(server_client, key, token, response)
    assert body["state"] == "rejected"
    assert body["error"]["type"].endswith("resource-unresolved")
    assert body["error"]["resource_kind"] == "pdk"


def test_a_manifest_from_a_newer_schema_is_refused(
        server_client, key, token, nop_project, job_archive, dispatcher):
    '''A read is only BACKWARDS compatible, and the other direction fails
    silently: keys dropped, values defaulted, and the server decides the
    nodes and limits from what it read.'''
    import io
    import os
    import tarfile

    from siliconcompiler.utils.paths import jobdir

    path = os.path.join(jobdir(nop_project), f"{nop_project.name}.pkg.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    nop_project.write_manifest(path)
    with open(path) as f:
        body = json.load(f)
    body["schemaversion"]["node"]["default"]["default"]["value"] = "99.0.0"

    # Replaced in the archive: a second member of one name is `traversal`.
    built, _, _ = job_archive()
    archive = os.path.abspath("future.tar.gz")
    with tarfile.open(built) as source, tarfile.open(archive, "w:gz") as out:
        for member in source.getmembers():
            data = source.extractfile(member) if member.isfile() else None
            if member.name.lstrip("./") == f"{nop_project.name}.pkg.json":
                encoded = json.dumps(body).encode()
                member.size, data = len(encoded), io.BytesIO(encoded)
            out.addfile(member, data)

    _, response = submitted(server_client, key, token,
                            (archive, None, os.path.getsize(archive)))

    assert response.status_code == 202
    assert not dispatcher.submitted
    body = job_after(server_client, key, token, response)
    assert body["state"] == "rejected"
    assert body["error"]["type"].endswith("declared-mismatch")
    assert "only backwards compatible" in body["error"]["detail"]


def test_a_manifests_scheduler_settings_are_overridden(nop_project, tmp_path):
    from siliconcompiler.remote.server.running import runspec

    nop_project.option.set_jobincr(True)
    nop_project.option.scheduler.set_name("slurm")
    nop_project.option.scheduler.set_queue("gpu-partition")
    nop_project.option.scheduler.add_options(["--exclusive"], step="stepone", index="0")

    runspec.normalize(nop_project, "job-1", tmp_path / "b", tmp_path / "c")

    assert nop_project.option.get_jobincr() is False
    assert nop_project.option.scheduler.get_name() is None
    assert nop_project.option.scheduler.get_queue() is None
    assert not nop_project.option.scheduler.get_options(step="stepone", index="0")


###########################
# 17. get
###########################

def test_another_user_can_neither_read_nor_list_my_job(server_client, key, token):
    '''404, not 403: a 403 would confirm the id belongs to somebody.'''
    job = create(server_client, key, token).get_json()
    other_key, other_token = stranger(server_client)

    response = call(server_client, other_key, "GET", f"/v1/jobs/{job['id']}", other_token)

    assert (response.status_code, slug(response)) == (404, "not-found")
    assert listing(server_client, other_key, other_token) == []


def test_only_a_live_job_says_when_to_ask_again_and_none_is_cacheable(
        server, server_client, key, token, me):
    job = create(server_client, key, token).get_json()

    live = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    ended = call(server_client, key, "GET", f"/v1/jobs/{reused(server, me, run_hash=None)}",
                 token)

    assert live.status_code == 200
    assert int(live.headers["Retry-After"]) >= 1
    assert live.headers["Cache-Control"] == "private, no-store"
    assert "Retry-After" not in ended.headers
    assert ended.get_json()["terminal"] is True


def test_the_job_object_carries_every_required_member(server_client, key, token):
    '''`transitions` in place of `state_changed_at` (D278), never empty, and
    no `deleted_cause`: every deletion is a person's (D279).'''
    body = read(server_client, key, token, create(server_client, key, token).get_json()["id"])

    for member in ("id", "state", "terminal", "transitions", "design",
                   "jobname", "flow", "owner", "project", "created_at",
                   "submitted_at", "started_at", "finished_at", "archived_at",
                   "deleted_at", "deleted_reason", "error", "nodes", "progress"):
        assert member in body, member
    assert "state_changed_at" not in body and "deleted_cause" not in body
    assert [entry["state"] for entry in body["transitions"]] == ["created"]


@pytest.mark.parametrize("web_url_base", [None, "http://sc.example/"])
def test_no_job_object_carries_a_portal_url(server, server_client, key, token,
                                            web_url_base):
    '''Surface D309: a job's page is asked for at `POST /v1/auth/browser`, so
    no answer carries one, with a portal configured or not.'''
    server.config["SC_CONFIG"]._values["web_url_base"] = web_url_base

    created = create(server_client, key, token).get_json()
    listed = call(server_client, key, "GET", "/v1/jobs", token).get_json()["items"]

    for job in [created, read(server_client, key, token, created["id"])] + listed:
        assert "web_url" not in job
        assert not any("portal" in str(value) for value in job.values()), job


###########################
# 16. list
###########################

def test_paging_is_a_keyset_over_the_published_ordering(server_client, key, token):
    '''Following `Link` until it is absent, on the last page, sees every job.'''
    ids = created_in_order(server_client, key, token, 5)

    response = call(server_client, key, "GET", "/v1/jobs?limit=2", token)
    assert len(response.get_json()["items"]) == 2

    seen = []
    while True:
        seen.extend(item["id"] for item in response.get_json()["items"])
        link = response.headers.get("Link")
        if not link:
            break
        assert 'rel="next"' in link
        response = call(server_client, key, "GET", link.split(">", 1)[0].lstrip("<"), token)

    assert seen == list(reversed(ids))


@pytest.mark.parametrize("query,refused", [
    ("cursor=nonsense!!", "invalid-cursor"),   # only ever taken from a Link header
    ("state=nearly", "invalid-request"),
    # S §16: a boolean is `true` or `false`; `archived=yes` read as false
    # would answer the unarchived list.
    *[(query, "invalid-request") for query in (
        "archived=yes", "archived=True", "archived=1", "terminal=no",
        "archived=true&archived=maybe")],
])
def test_a_listing_query_it_cannot_honour_is_refused(server_client, key, token, query,
                                                     refused):
    response = call(server_client, key, "GET", f"/v1/jobs?{query}", token)

    assert (response.status_code, slug(response)) == (400, refused)


def test_design_and_jobname_filter_exactly(server_client, key, token):
    '''Not a prefix: free text under a match operator is a LIKE over user input.'''
    create(server_client, key, token, design="gcd", jobname="nightly-1")
    create(server_client, key, token, design="picorv32", jobname="nightly-2")

    body = call(server_client, key, "GET", "/v1/jobs?design=gcd", token).get_json()
    assert [item["design"] for item in body["items"]] == ["gcd"]
    assert listing(server_client, key, token, "jobname=nightly") == []


def test_repeated_filters_or_within_a_key_and_terminal_filters(
        server, server_client, key, token):
    '''`archived` is the one filter whose default is not everything;
    `?archived=true&archived=false` is both views; `?terminal=` is the flag.'''
    kept = create(server_client, key, token).get_json()["id"]
    gone = create(server_client, key, token, jobname="job1").get_json()["id"]
    cancel(server_client, key, token, gone)
    call(server_client, key, "POST", f"/v1/jobs/{gone}/archive", token, json={})
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET archived_at = ?, archived_by = user_id WHERE id = ?", (now(), gone))

    def ids(query):
        return set(listing(server_client, key, token, query))

    assert ids("") == {kept}
    assert ids("archived=true") == {gone}
    assert ids("archived=true&archived=false") == {kept, gone}
    assert ids("archived=true&archived=false&terminal=true") == {gone}
    assert ids("terminal=false") == {kept}
    assert ids("jobname=job0&jobname=job1&archived=true&archived=false") == {kept, gone}


def test_the_next_page_keeps_every_repeat(server_client, key, token):
    for n in range(3):
        create(server_client, key, token, jobname=f"job{n}")

    first = call(server_client, key, "GET",
                 "/v1/jobs?limit=1&jobname=job0&jobname=job1&jobname=job2", token)

    link = first.headers["Link"]
    assert link.count("jobname=") == 3
    target = link.split(">", 1)[0].lstrip("<")
    assert len(call(server_client, key, "GET", target, token).get_json()["items"]) == 1


@pytest.mark.parametrize("value", [0, 0.5, "1"])
def test_a_poll_interval_below_one_whole_second_is_refused(value):
    from siliconcompiler.remote.server.config import DEFAULTS, _check_policy

    with pytest.raises(ValueError, match="poll_interval_seconds"):
        _check_policy(dict(DEFAULTS, poll_interval_seconds=value))


###########################
# 18. cancel
###########################

def test_a_running_job_moves_to_cancelling(server_client, key, token, job_archive, dispatcher):
    '''Not `cancelled`: the scheduler writes the terminal state, and a 202 with
    a job still `running` would look like nothing happened.'''
    job, _ = submitted(server_client, key, token, job_archive())

    response = cancel(server_client, key, token, job["id"])

    assert response.status_code == 202
    assert (response.get_json()["state"], response.get_json()["terminal"]) == \
        ("cancelling", False)
    assert dispatcher.cancelled


def test_cancel_takes_no_body_and_is_idempotent(server_client, key, token):
    '''No body at all, or a Ctrl-C could not be expressed. A job that never
    started is `cancelled` outright, with no `cancelling` between.'''
    job = create(server_client, key, token).get_json()

    first = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)
    second = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token)

    assert first.status_code == second.status_code == 202
    for response in (first, second):
        assert (response.get_json()["state"], response.get_json()["terminal"]) == \
            ("cancelled", True)


@pytest.mark.parametrize("reason,status", [
    ("é" * 300, 202),        # code points, not bytes: 600 bytes of UTF-8 (D306)
    ("é" * 301, 400), ("x" * 301, 400), ("x" * 5000, 400),
    ("two\nlines", 400), ("a\x07bell", 400)])
def test_a_cancel_reason_is_one_line_of_at_most_300_code_points(
        server, server_client, key, token, reason, status):
    '''Text the portal renders and a CLI prints (D288): refused rather than
    cut, naming the rule it broke and never echoed; a taken one is recorded
    where the portal reads it.'''
    job = create(server_client, key, token).get_json()

    response = cancel(server_client, key, token, job["id"], reason=reason)

    assert response.status_code == status
    if status == 202:
        rows = server.config["SC_STORE"].all(
            "SELECT reason FROM job_state_transitions WHERE job_id = ?", (job["id"],))
        assert rows[-1]["reason"] == reason
    else:
        detail = response.get_json()["detail"]
        assert slug(response) == "invalid-request"
        assert ("300" if len(reason) > 300 else "control character") in detail
        assert reason not in detail


def test_a_cancel_of_a_job_the_scheduler_already_ended_leaves_it(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''Conditional on the state it moves from: the `202` carries the job as
    the scheduler left it.'''
    job = running(server, server_client, key, token, job_archive, me)
    jobs = server.config["SC_JOBS"]
    original = jobs._transition_if

    def ended_first(job_id, from_state, to_state, **kwargs):
        # The scheduler got there between the read and the write.
        jobs._transition(job_id, from_state, "completed")
        return original(job_id, from_state, to_state, **kwargs)

    jobs._transition_if = ended_first
    response = cancel(server_client, key, token, job["id"])

    assert response.status_code == 202
    assert response.get_json()["state"] == "completed"
    assert not dispatcher.cancelled


def test_a_cancelling_job_ends_cancelled_even_if_its_run_finished(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''The reason is on its `transitions` entry, never the job's
    `state_reason`, a live staging phase's (D278); a node the cancel stopped
    has no exit code and says why.'''
    job = running(server, server_client, key, token, job_archive, me)
    cancelled = cancel(server_client, key, token, job["id"], reason="wrong corner").get_json()
    assert cancelled["state"] == "cancelling" and "state_reason" not in cancelled
    assert (cancelled["transitions"][-1]["state"],
            cancelled["transitions"][-1]["reason"]) == ("cancelling", "wrong corner")

    report(server, me, job, "completed", {"stepone/0": {"state": "completed", "exit_code": 0},
                                          "steptwo/0": {"state": "running"}})

    body = read(server_client, key, token, job["id"])
    assert body["state"] == "cancelled"
    assert [entry["state"] for entry in body["transitions"]][-2:] == ["cancelling", "cancelled"]
    assert body["transitions"][-2]["reason"] == "wrong corner"
    nodes = {node["step"]: node for node in body["nodes"]}
    assert all(node["terminal"] for node in body["nodes"])
    assert (nodes["steptwo"]["state"], nodes["steptwo"]["exit_code"],
            nodes["steptwo"]["state_reason"]) == ("cancelled", None, "wrong corner")


# 300 characters, and two spaces a `detail`'s bound would fold into one.
LONG_REASON = ("stopped by hand:  " + "the corner was wrong and the run is repeated " * 7)[:300]


def test_a_300_character_reason_is_served_whole(
        server, server_client, key, token, job_archive, dispatcher, me, monkeypatch):
    '''What is accepted is what everyone reads (D288): whole, on both
    transitions and each node the cancel stopped, even where a deployment
    bounds its own text shorter.'''
    from siliconcompiler.remote.server import errors

    assert len(LONG_REASON) == 300
    monkeypatch.setattr(errors, "DETAIL_MAX", 100)
    job = running(server, server_client, key, token, job_archive, me)
    cancelled = cancel(server_client, key, token, job["id"], reason=LONG_REASON).get_json()
    assert cancelled["transitions"][-1] == {**cancelled["transitions"][-1],
                                            "state": "cancelling", "reason": LONG_REASON}

    report(server, me, job, "completed", {"stepone/0": {"state": "completed", "exit_code": 0},
                                          "steptwo/0": {"state": "running"}},
           error="the run's own words")

    body = read(server_client, key, token, job["id"])
    assert body["state"] == "cancelled"
    assert [(entry["state"], entry.get("reason")) for entry in body["transitions"]][-2:] == \
        [("cancelling", LONG_REASON), ("cancelled", LONG_REASON)]
    assert {node["step"]: node for node in body["nodes"]}["steptwo"]["state_reason"] == \
        LONG_REASON
    assert "state_reason" not in body


def test_a_cancel_that_lands_while_staging_carries_its_reason_to_cancelled(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''The staging thread writes `cancelled` with the cancel's reason, not a
    word of its own.'''
    job = running(server, server_client, key, token, job_archive, me)
    cancel(server_client, key, token, job["id"], reason=LONG_REASON)
    jobs = server.config["SC_JOBS"]

    jobs._settle_cancelled(jobs._row(job["id"]))

    body = read(server_client, key, token, job["id"])
    assert (body["transitions"][-1]["state"], body["transitions"][-1]["reason"]) == \
        ("cancelled", LONG_REASON)
    assert all(node["state_reason"] == LONG_REASON for node in body["nodes"]
               if node["state"] == "cancelled")


def test_the_servers_own_reasons_keep_their_bound(
        server, server_client, key, token, monkeypatch):
    '''Only a cancel's reason is served whole; the server's are bounded like
    a `detail`.'''
    from siliconcompiler.remote.server import errors

    monkeypatch.setattr(errors, "DETAIL_MAX", 100)
    job = create(server_client, key, token).get_json()
    with server.config["SC_STORE"].transaction():
        server.config["SC_JOBS"]._transition(job["id"], "created", "awaiting_input",
                                             reason="y " * 200)

    served = read(server_client, key, token, job["id"])["transitions"][-1]["reason"]
    assert served.endswith("...") and len(served) < 110


###########################
# 19. delete
###########################

def test_delete_refuses_a_job_that_is_still_spending(server_client, key, token,
                                                     job_archive, dispatcher):
    '''"Delete it and its data" cannot mean "hide it and keep spending".'''
    job, _ = submitted(server_client, key, token, job_archive())

    response = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert (response.status_code, slug(response)) == (409, "job-state-conflict")


def test_delete_keeps_the_row_and_drops_the_bytes(server, server_client, key,
                                                  token, job_archive, dispatcher, me):
    '''No `deleted` state: it would erase whether the job had completed,
    failed or been rejected, the fact wanted when results go missing.'''
    job, _ = submitted(server_client, key, token, job_archive())
    cancel(server_client, key, token, job["id"])
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET state = 'cancelled' WHERE id = ?", (job["id"],))
    root = server.config["SC_JOBS"].job_root(me, job["id"])
    assert root.exists()

    response = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert response.status_code == 204
    assert not root.exists()
    body = read(server_client, key, token, job["id"])
    assert body["state"] == "cancelled" and body["deleted_at"]


def test_a_delete_is_idempotent_unlisted_and_keeps_the_audit_trail(
        server, server_client, key, token):
    '''An audit trail a user can erase by deleting the job is not one.'''
    job = create(server_client, key, token).get_json()
    cancel(server_client, key, token, job["id"])

    first = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)
    second = call(server_client, key, "DELETE", f"/v1/jobs/{job['id']}", token)

    assert first.status_code == second.status_code == 204
    assert listing(server_client, key, token) == []
    assert listing(server_client, key, token, "archived=true") == []
    assert len(server.config["SC_STORE"].all(
        "SELECT * FROM job_state_transitions WHERE job_id = ?", (job["id"],))) >= 2


###########################
# Reconciliation
###########################

def test_cannot_tell_is_not_the_same_as_gone(server, server_client, key, token,
                                             job_archive, dispatcher):
    '''Declaring a live job lost is the more expensive mistake.'''
    job, _ = submitted(server_client, key, token, job_archive())

    def explode(scheduler_job_id):
        raise OSError("the controller is not answering")
    dispatcher.is_alive = explode

    assert read(server_client, key, token, job["id"])["state"] == "queued"


def test_a_job_that_finished_while_we_looked_is_not_lost(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''"Going" and "never heard of it" are read at two moments, and a run
    that finished between satisfies both, so the file is read once more
    before the job is declared lost. It fired on a real asicflow run.'''
    job = running(server, server_client, key, token, job_archive, me)
    settles_between_readings(server, me, job, dispatcher)

    body = read(server_client, key, token, job["id"])

    assert body["state"] == "completed" and body["error"] is None
    # And its nodes as the settled file has them, not cancelled as unfinished.
    assert {node["step"]: node["state"] for node in body["nodes"]} == \
        {"stepone": "completed", "steptwo": "completed"}


def test_a_cancel_still_wins_when_the_run_finished_while_we_looked(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''What it managed before it died does not change what was asked for.'''
    job = running(server, server_client, key, token, job_archive, me)
    read(server_client, key, token, job["id"])
    cancel(server_client, key, token, job["id"])
    settles_between_readings(server, me, job, dispatcher)

    assert read(server_client, key, token, job["id"])["state"] == "cancelled"


@pytest.mark.parametrize("heartbeat,state", [("2026-09-24T10:00:00.000Z", "failed"),
                                             (None, "running")])
def test_a_silent_run_is_lost_even_while_the_scheduler_says_running(
        server, server_client, key, token, job_archive, dispatcher, me, heartbeat, state):
    '''The backstop for a wrong scheduler: a dynamic node killed without
    deleting itself leaves Slurm saying RUNNING for ever. A beating run is
    left alone, the heartbeat being on a timer and not on progress.'''
    job = running(server, server_client, key, token, job_archive, me)
    if heartbeat:
        report(server, me, job, heartbeat=heartbeat)
    dispatcher.alive = True

    body = read(server_client, key, token, job["id"])

    assert body["state"] == state
    if state == "failed":
        assert body["error"]["type"].endswith("run-interrupted")


###########################
# Which scheduler job a node became
###########################

def count_node_jobs(dispatcher):
    asked = []
    real = dispatcher.node_jobs

    def counting(job_id, nodes):
        asked.append(sorted(nodes))
        return real(job_id, nodes)

    dispatcher.node_jobs = counting
    return asked


def test_a_nodes_scheduler_job_is_recorded_asking_once(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''*Which Slurm job was that* is a support thread's question: recorded for
    the portal and a cancel, never on the wire. Only nodes missing an id are
    looked up, keeping it inside the once-per-run poll.'''
    asked = count_node_jobs(dispatcher)
    job = running(server, server_client, key, token, job_archive, me)

    for _ in range(3):
        read(server_client, key, token, job["id"])

    assert asked == [[("stepone", "0"), ("steptwo", "0")]]
    rows = server.config["SC_STORE"].all(
        'SELECT scheduler_job_id FROM job_nodes WHERE job_id = ? ORDER BY step', (job["id"],))
    assert [row["scheduler_job_id"] for row in rows] == \
        [f"{job['id']}_stepone_0", f"{job['id']}_steptwo_0"]


def test_a_fast_poll_does_not_become_a_fast_squeue(server, server_client, key, token,
                                                   job_archive, dispatcher, me):
    '''A read is a SQLite read and a stat, a node lookup an RPC into
    slurmctld: without a floor, a shorter poll multiplies its load.'''
    asked = count_node_jobs(dispatcher)
    job = running(server, server_client, key, token, job_archive, me)

    # The store forgets the ids between polls, so every poll WOULD ask.
    for _ in range(5):
        server.config["SC_STORE"].execute(
            "UPDATE job_nodes SET scheduler_job_id = NULL WHERE job_id = ?", (job["id"],))
        read(server_client, key, token, job["id"])

    assert len(asked) == 1, f"asked the scheduler {len(asked)} times in five polls"


@pytest.mark.parametrize("polled,forgotten", [(True, False), (True, True), (False, False)])
def test_cancel_reaches_every_node_job_and_the_coordinator(
        server, server_client, key, token, job_archive, dispatcher, me, polled, forgotten):
    '''The nodes are jobs of their own; Slurm usually ends them with the
    coordinator, but a cancel names them. The ids are refreshed first, so a
    node dispatched since the last poll is reached, and the poll's floor
    never hands a cancel a stale answer.'''
    job = running(server, server_client, key, token, job_archive, me)
    store = server.config["SC_STORE"]
    if polled:
        read(server_client, key, token, job["id"])
    if forgotten:
        store.execute("UPDATE job_nodes SET scheduler_job_id = NULL WHERE job_id = ?",
                      (job["id"],))
    if not polled:
        assert not store.all("SELECT 1 FROM job_nodes WHERE job_id = ? "
                             "AND scheduler_job_id IS NOT NULL", (job["id"],))

    response = cancel(server_client, key, token, job["id"], reason="changed my mind")

    assert response.status_code == 202
    assert dispatcher.cancelled == ["fake:1"]
    assert sorted(dispatcher.cancelled_nodes) == \
        [f"{job['id']}_stepone_0", f"{job['id']}_steptwo_0"]


def test_a_deployment_with_no_cluster_has_no_node_jobs():
    '''Nodes are processes inside the run, and a cancel signals the process
    group: an empty answer is the truthful one, hence the nullable column.'''
    from siliconcompiler.remote.server.running.dispatch import LocalDispatcher

    assert LocalDispatcher().node_jobs("job", [("a", "0")]) == {}


@pytest.mark.parametrize("reported,still_running", [
    (False, set()), (True, {("stepone", "0")}), (True, set())])
def test_a_lost_run_is_reported_leaving_no_node_running(
        server, server_client, key, token, job_archive, dispatcher, me, reported,
        still_running):
    '''Gone, never having said how it ended: reported, not polled for ever.
    Marking a node `cancelled` cancels nothing (on the compose rig an OpenROAD
    route ran 55 minutes past its failed orchestrator), so a node still
    running is scancelled; a finished one is not, nor the orchestrator.'''
    job, _ = submitted(server_client, key, token, job_archive())
    if reported:
        report(server, me, job)
    dispatcher.still_running = still_running
    dispatcher.alive = False

    body = read(server_client, key, token, job["id"])

    assert body["state"] == "failed"
    assert body["error"]["type"].endswith("run-interrupted")
    assert "status" not in body["error"]
    if not reported:
        assert all(node["state"] == "cancelled" for node in body["nodes"])
    assert dispatcher.cancelled_nodes == [f"{job['id']}_{step}_{index}"
                                          for step, index in still_running]
    assert dispatcher.cancelled == []


###########################
# Why it failed, in the run's own words
###########################

def test_a_failed_run_publishes_the_reason_the_run_gave(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''`type` and `title` are frozen, so without `detail` the error says only
    what `state` did; the runner's exception reached no client before.'''
    job = running(server, server_client, key, token, job_archive, me)
    report(server, me, job, "failed", {"stepone/0": {"state": "cancelled"},
                                       "steptwo/0": {"state": "cancelled"}},
           error="RuntimeError: git is required to import GitPython")

    body = read(server_client, key, token, job["id"])

    assert body["state"] == "failed"
    assert body["error"]["type"].endswith("run-failed")
    assert body["error"]["detail"] == "RuntimeError: git is required to import GitPython"
    # A run can fail with no failed node, so "read the failing node's log" is wrong.
    assert body["progress"]["failed_count"] == 0


@pytest.mark.parametrize("code,said", [(1, "exited with status 1"), (None, "failed")])
def test_a_failed_node_carries_the_type_and_the_job_no_bare_slug(
        server, server_client, key, token, job_archive, dispatcher, me, code, said):
    '''A node's `error` was null on every node ever run, failed or not. The
    job's `detail` is prose about this occurrence, never the slug `type` is.'''
    job = running(server, server_client, key, token, job_archive, me)
    report(server, me, job, "failed", {"stepone/0": {"state": "failed", "exit_code": code},
                                       "steptwo/0": {"state": "cancelled"}})

    body = read(server_client, key, token, job["id"])

    assert body["error"]["type"].endswith("run-failed") and "detail" not in body["error"]
    nodes = {node["step"]: node for node in body["nodes"]}
    assert nodes["stepone"]["error"]["type"].endswith("run-failed")
    assert nodes["stepone"]["error"]["detail"] == f"the node's task {said}; its log says why"
    # Nothing on the node that never ran: the job ended before it started.
    assert nodes["steptwo"]["error"] is None


@pytest.mark.parametrize("node,published", [({"exit_code": -9, "limit": "time"}, 137),
                                            ({"exit_code": None, "limit": "time"}, None),
                                            ({"exit_code": 137, "limit": "memory"}, 137)])
def test_a_limit_is_run_failed_naming_it_on_the_job_and_the_node(
        server, server_client, key, token, job_archive, dispatcher, me, node, published):
    '''Surface §17, *A node's `error`*: the job's shape, `detail` included.'''
    job = running(server, server_client, key, token, job_archive, me)
    report(server, me, job, "failed", {"stepone/0": {"state": "failed", **node},
                                       "steptwo/0": {"state": "pending"}})

    body = read(server_client, key, token, job["id"])

    assert body["error"]["type"].endswith("/run-failed")
    assert f"stepone/0 exceeded its {node['limit']} limit" in body["error"]["detail"]
    nodes = {one["step"]: one for one in body["nodes"]}
    assert nodes["stepone"]["exit_code"] == published
    assert nodes["stepone"]["error"] == {
        "type": "https://siliconcompiler.com/server-errors/run-failed",
        "title": nodes["stepone"]["error"]["title"],
        "detail": f"the node exceeded its {node['limit']} limit"}
    assert nodes["steptwo"]["state"] == "cancelled"


@pytest.mark.parametrize("reported,published", [(0, 0), (1, 1), (-9, 137), (-15, 143),
                                                (137, 137), (None, None)])
def test_an_exit_code_is_0_to_255_and_a_signal_is_128_plus_n(reported, published):
    from siliconcompiler.remote.server.running import runspec

    assert runspec.exit_code(reported) == published


def test_an_image_that_would_not_pull_is_run_interrupted_naming_it(
        server, server_client, key, token, job_archive, dispatcher, me):
    job = running(server, server_client, key, token, job_archive, me)
    report(server, me, job, "failed", {
        "stepone/0": {"state": "failed", "exit_code": 125, "interrupted": {
            "image": "ghcr.io/x/sc@sha256:aa", "error": "pull access denied"}},
        "steptwo/0": {"state": "pending"}})

    body = read(server_client, key, token, job["id"])

    assert body["error"]["type"].endswith("/run-interrupted")
    assert "its image ghcr.io/x/sc@sha256:aa could not be pulled" in body["error"]["detail"]
    nodes = {node["step"]: node for node in body["nodes"]}
    assert nodes["stepone"]["error"]["type"].endswith("/run-interrupted")
    assert nodes["stepone"]["error"]["detail"] == \
        "the node could not start: its image ghcr.io/x/sc@sha256:aa could not be pulled"
    assert nodes["steptwo"]["error"] is None


def test_a_job_the_scheduler_would_not_take_is_staging_failed_and_listed_as_it_ends(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    '''This server's own failure: `failed`, `staging-failed` with the detail,
    never `rejected` and never `queued` before the scheduler holds it. Its
    `staging` record, never a run log it has none of, is listed by the
    transition itself rather than a later cleanup.'''
    import gzip

    from siliconcompiler.remote.server.running.dispatch import DispatchError

    def refuse(*args, **kwargs):
        raise DispatchError("slurmctld is not answering")

    dispatcher.submit = refuse
    monkeypatch.setattr(server.config["SC_JOBS"], "_keep_staging_record",
                        lambda job_id: None)

    job, response = submitted(server_client, key, token, job_archive())

    assert response.status_code == 202
    body = read(server_client, key, token, job["id"])
    error = body["error"]
    assert body["state"] == "failed"
    assert error["type"].endswith("staging-failed") and "status" not in error
    assert "slurmctld is not answering" in error["detail"]
    listed = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/artifacts",
                  token).get_json()["items"]
    assert not any(item["kind"] == "logs" for item in listed)
    item, = [item for item in listed if item["kind"] == "staging"]
    target = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/artifacts/{item['id']}",
                  token).headers["Location"]
    text = gzip.decompress(server_client.get(target.split("http://localhost", 1)[1]).data)
    assert b"staging failed: " in text and b"slurmctld is not answering" in text


###########################
# Terminal only once listed (surface D308, D310)
###########################

def _states_when_indexed(monkeypatch, server, method):
    '''Record, at each call of a JobService indexing method, the job's and its
    nodes' states as the store then holds them.'''
    jobs = server.config["SC_JOBS"]
    store = server.config["SC_STORE"]
    real = getattr(jobs, method)
    seen = []

    def wrapped(job, *args):
        seen.append((store.one("SELECT state FROM jobs WHERE id = ?", (job["id"],))["state"],
                     {(row["step"], row["index"]): row["state"] for row in store.all(
                         'SELECT step, "index", state FROM job_nodes WHERE job_id = ?',
                         (job["id"],))}, args))
        return real(job, *args)

    monkeypatch.setattr(jobs, method, wrapped)
    return seen


def run_logs(server_client, key, token, job):
    return [item["step"] for item in call(server_client, key, "GET",
                                          f"/v1/jobs/{job['id']}/artifacts",
                                          token).get_json()["items"] if item["kind"] == "logs"]


def test_a_node_turns_failed_only_after_its_log_is_listed(
        monkeypatch, server, server_client, key, token, job_archive, dispatcher, me):
    '''`failed` as well as `completed`: a client that sees a terminal node
    fetches what it left, so the listing has it first.'''
    job = running(server, server_client, key, token, job_archive, me)
    node = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0" / "stepone" / "0"
    node.mkdir(parents=True, exist_ok=True)
    (node / "sc_stepone_0.log").write_text("it went wrong\n")
    report(server, me, job, nodes={"stepone/0": {"state": "failed", "exit_code": 1},
                                   "steptwo/0": {"state": "pending"}})
    seen = _states_when_indexed(monkeypatch, server, "_index_node")

    body = read(server_client, key, token, job["id"])

    assert ("stepone", "failed") in {(n["step"], n["state"]) for n in body["nodes"]}
    _, nodes, named = seen[0]
    assert named == ("stepone", "0")
    assert nodes[("stepone", "0")] not in ("completed", "failed", "skipped", "cancelled")
    assert "stepone" in run_logs(server_client, key, token, job)


@pytest.mark.parametrize("cancelled", [False, True])
def test_a_lost_or_cancelled_run_ends_only_after_what_it_left_is_listed(
        monkeypatch, server, server_client, key, token, job_archive, dispatcher, me,
        cancelled):
    '''A cancel kills the run, so the next poll finds no scheduler job and a
    file still saying `running`: the shape of a lost job, and not one (the
    portal gate caught a browser cancel reported as `scheduler-lost`).'''
    job = running(server, server_client, key, token, job_archive, me)
    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    root.mkdir(parents=True, exist_ok=True)
    (root / "job.log").write_text("the run's own log\n")
    if cancelled:
        assert cancel(server_client, key, token, job["id"]).get_json()["state"] == "cancelling"
    dispatcher.alive = False
    seen = _states_when_indexed(monkeypatch, server, "_index")

    body = read(server_client, key, token, job["id"])

    state, nodes, _ = seen[0]
    if cancelled:
        assert (body["state"], body["terminal"], body.get("error")) == ("cancelled", True, None)
        assert all(node["state"] == "cancelled" for node in body["nodes"])
        assert state == "cancelling" and "cancelled" not in nodes.values()
    else:
        assert body["state"] == "failed"
        assert state not in ("failed", "cancelled")
        assert not set(nodes.values()) & {"failed", "cancelled"}
    assert None in run_logs(server_client, key, token, job)


###########################
# A job nobody ever uploaded to
###########################

def test_a_job_whose_upload_never_arrived_is_abandoned(server, server_client, key, token):
    '''`abandoned`, which nothing wrote: such a job held a `pending_uploads`
    slot for ever, its portal page reloading. A slow upload and a dead script
    look alike, so a job holding a good grant is left alone however old.'''
    created = create(server_client, key, token).get_json()
    granted = create(server_client, key, token, jobname="job1").get_json()
    grant(server_client, key, token, granted["id"], sized(4096))
    assert read(server_client, key, token, created["id"])["state"] == "created"

    server.config["SC_CONFIG"].limits["abandon_after_seconds"] = 0

    body = read(server_client, key, token, created["id"])
    assert (body["state"], body["terminal"]) == ("abandoned", True)
    assert body["finished_at"]
    assert read(server_client, key, token, granted["id"])["state"] == "awaiting_input"


def test_the_sweep_settles_the_jobs_nobody_opens(server, server_client, key, token):
    '''A job stuck in `created` is the one nobody opens, holding a slot.'''
    from siliconcompiler.remote.server.outputs import reaper

    created = create(server_client, key, token).get_json()
    server.config["SC_CONFIG"].limits["abandon_after_seconds"] = 0

    taken = reaper.sweep(server.config["SC_STORE"], server.config["SC_STORAGE"],
                         server.config["SC_CONFIG"], server.config["SC_DATADIR"])

    assert taken["abandoned"] == 1
    assert server.config["SC_STORE"].one(
        "SELECT state FROM jobs WHERE id = ?", (created["id"],))["state"] == "abandoned"


###########################
# Placing a job in a container
###########################

def digest(letter):
    return "sha256:" + letter * 64


def operator(store):
    return store.one("SELECT id FROM users WHERE issuer = 'operator'")["id"]


@pytest.fixture
def registry(runs_test_version):
    '''A curated registry, seeded before any server opens it: a container
    deployment with no live SiliconCompiler image does not start. One image,
    the framework only, is enough: `nopflow`'s `builtin` raises no requirement.'''
    import os

    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.state.store import Store

    os.makedirs("container-datadir", exist_ok=True)
    with open("container-datadir/config.json", "w") as f:
        json.dump({"containers": True}, f)

    with Store("container-datadir/server.db") as store:
        with store.transaction():
            actor = store.upsert_user("operator", "someone@host")["id"]

        images.register_software(store, "siliconcompiler", "SiliconCompiler", actor, "python")
        images.register_version(store, "siliconcompiler", "0.38.0", actor,
                                preference=10)
        # Its own Python, as the probe records every image's (surface D293).
        images.register_software(store, "python", "Python", actor, "interpreter")
        images.register_version(store, "python", "3.11.9", actor)
        images.register_image(store, "ghcr.io/x/sc:0.38.0", digest("a"),
                              [("siliconcompiler", "0.38.0"), ("python", "3.11.9")], actor)


@pytest.fixture
def container_server(registry):
    '''A deployment running its jobs in images it registered: its own server,
    since `containers` is read at startup and decides what `GET /v1` says.'''
    from siliconcompiler.remote.server.app import create_app

    return create_app("container-datadir", cluster="local")


@pytest.fixture
def container_client(container_server):
    return container_server.test_client()


@pytest.fixture
def container_token(container_client, key):
    return login(container_client, key).get_json()["access_token"]


@pytest.fixture
def container_me(container_client, key, container_token):
    return call(container_client, key, "GET", "/v1/me", container_token).get_json()["id"]


@pytest.fixture
def container_dispatcher(container_server):
    fake = FakeDispatcher()
    container_server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.mark.parametrize("held", [None, "99.0.0"])
def test_a_container_deployment_with_no_image_of_its_version_does_not_start(
        runs_test_version, held):
    '''Better learned at startup than at a first submit: with containers on,
    a live image must hold the server's own SiliconCompiler.'''
    import os

    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.state.store import Store

    os.makedirs("elsewhere", exist_ok=True)
    with open("elsewhere/config.json", "w") as f:
        json.dump({"containers": True}, f)
    if held:
        with Store("elsewhere/server.db") as store:
            with store.transaction():
                actor = store.upsert_user("operator", "someone@host")["id"]
            images.register_software(store, "siliconcompiler", "SiliconCompiler", actor,
                                     "python")
            images.register_version(store, "siliconcompiler", held, actor)
            images.register_image(store, "ghcr.io/x/future:99", digest("f"),
                                  [("siliconcompiler", held)], actor)

    with pytest.raises(RuntimeError, match=f"no live image holds siliconcompiler "
                                           f"{images.own_version()}"):
        create_app("elsewhere", cluster="local")


def test_submit_places_every_node_in_an_image_by_digest_and_publishes_it(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher):
    '''The node is told a digest, never a tag, so a rebuilt `sc:0.38.0` cannot
    change an accepted job; `resolved_versions` says what the server chose
    for a range, which the descriptor cannot.'''
    job, _ = submitted(container_client, key, container_token, job_archive(),
                       requested_versions=wants(">=0.38,<0.39"))

    store = container_server.config["SC_STORE"]
    placed = store.one("SELECT image_id FROM jobs WHERE id = ?", (job["id"],))["image_id"]
    assert placed
    assert [node["image_id"] for node in store.all(
        "SELECT image_id FROM job_nodes WHERE job_id = ?", (job["id"],))] == [placed] * 2
    scheduler = run_manifest(container_dispatcher.submitted[0][2]).option.scheduler
    assert scheduler.get_name(step="stepone", index="0") == "docker"
    assert scheduler.get_queue(step="stepone", index="0") == f"ghcr.io/x/sc@{digest('a')}"
    assert read(container_client, key, container_token, job["id"])["resolved_versions"] == \
        {"python": {"siliconcompiler": ["0.38.0"]}, "tools": {}}


def test_a_tool_with_no_image_fails_the_whole_submit(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher, monkeypatch):
    '''Before anything runs, not on node thirty-one with the cluster paid
    for. The operator curates OpenROAD and put it in no image.'''
    from siliconcompiler.remote import runflow
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    images.register_software(store, "openroad", "OpenROAD", operator(store), "tool")
    images.register_version(store, "openroad", "2.0", operator(store))
    # `nopflow` names only `builtin`, which raises no requirement.
    monkeypatch.setattr(runflow, "node_tools",
                        lambda flow, nodes: {node: "openroad" for node in nodes})

    job, response = submitted(container_client, key, container_token, job_archive())

    assert response.status_code == 202
    assert not container_dispatcher.submitted
    body = read(container_client, key, container_token, job["id"])
    assert body["state"] == "rejected"
    assert body["error"]["type"].endswith("software-unavailable")
    assert body["error"]["reason"] == "unavailable"
    assert body["error"]["unresolved"] == [
        {"kind": "tools", "name": "openroad", "requirement": [], "available": []}]


@pytest.mark.parametrize("versions,status", [
    (wants(">=0.38,<0.39"), 201),
    (wants("0.38.0"), 201),                  # a bare version is still an exact pin
    (wants("0.38.1"), 422),
    (wants(">=0.40"), 422),
    ({"python": {}, "tools": {}}, 201),      # no Python named, none held to
    ({"python": {}, "tools": {}, "interpreter": {"python": ["==3.11.*"]}}, 201),
    ({"interpreter": {"pypy": ["==3.10.*"]}}, 400),     # the bucket has one name
])
def test_requested_versions_are_resolved_at_create(container_client, key, container_token,
                                                   versions, status):
    '''Resolution needs the declared versions and the registry, not the
    upload, so it happens before the upload, where it is free.'''
    response = create(container_client, key, container_token, requested_versions=versions)

    assert response.status_code == status, response.get_json()
    if status == 422:
        assert slug(response) == "software-unavailable"
        assert response.get_json()["unresolved"][0]["name"] == "siliconcompiler"
    elif status == 400:
        assert slug(response) == "invalid-request"


def test_a_python_no_image_runs_is_refused_at_create_naming_what_there_is(
        container_client, key, container_token):
    '''Surface D293: a job running the user's Python names the one it was
    written for, and one no live image runs is refused naming those there are.'''
    response = create(container_client, key, container_token, requested_versions={
        "python": {}, "tools": {}, "interpreter": {"python": ["==3.12.*"]}})

    assert (response.status_code, slug(response)) == (422, "software-unavailable")
    body = response.get_json()
    assert body["unresolved"] == [{"kind": "interpreter", "name": "python",
                                   "requirement": ["==3.12.*"], "available": ["3.11.9"]}]
    assert "operator would have to add" in body["detail"]


def test_a_name_that_reports_no_version_is_told_so_and_not_told_no_match(
        container_server, container_client, key, container_token):
    '''`GET /v1` cannot carry the mark, so a client's preflight said yes; *no
    image matches* would send them after a version already installed.'''
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    images.register_software(store, "magic", "Magic", operator(store), "tool")
    images.register_version(store, "magic", "20260924", operator(store),
                            source="published_date")
    images.register_image(store, "ghcr.io/x/sc-magic:1", digest("c"),
                          [("siliconcompiler", "0.38.0"), ("magic", "20260924")],
                          operator(store))

    response = create(container_client, key, container_token,
                      requested_versions=wants(tools={"magic": ">=8.0"}))

    # Software no image holds, not `version-skew`, the client's own SiliconCompiler (§7).
    assert (response.status_code, slug(response)) == (422, "software-unavailable")
    assert "reports no version" in response.get_json()["detail"]
    assert response.get_json()["unresolved"] == [
        {"kind": "tools", "name": "magic", "requirement": [">=8.0"], "available": []}]


def test_the_job_identity_folds_in_what_the_server_chose(
        container_server, container_client, key, container_token, container_me,
        container_reuses):
    '''The client hashes the work and this server chooses what runs it, so a
    re-registered image, a new digest, is precisely *the code changed*.'''
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    existing = reuse_job(container_server.config["SC_JOBS"], store, container_me, "h-1",
                         "completed")

    again = create(container_client, key, container_token, run_hash="h-1")
    assert (again.status_code, again.get_json()["id"]) == (200, existing)

    # The same tag, rebuilt: the old row is superseded, the digest new.
    images.register_image(store, "ghcr.io/x/sc:0.38.0", digest("b"),
                          [("siliconcompiler", "0.38.0")], operator(store))

    after = create(container_client, key, container_token, run_hash="h-1")
    assert after.status_code == 201
    assert after.get_json()["id"] != existing
    # Both halves are recorded: what was sent, and what it is keyed on.
    row = store.one("SELECT run_hash, job_identity FROM jobs WHERE id = ?",
                    (after.get_json()["id"],))
    assert row["run_hash"] == "h-1"
    assert row["job_identity"] and row["job_identity"] != "h-1"


def test_a_hit_needs_the_python_its_own_modules_were_written_for(
        container_server, container_client, key, container_token, container_me,
        container_reuses):
    '''Job-reuse D23: one image serves a job naming no Python and one written
    for its 3.11 alike, so the requirement is part of what the job is.'''
    written_for = {"python": {}, "tools": {}, "interpreter": {"python": ["==3.11.*"]}}
    existing = reuse_job(container_server.config["SC_JOBS"],
                         container_server.config["SC_STORE"], container_me, "h-1",
                         "completed", declared=written_for)

    assert create(container_client, key, container_token,
                  run_hash="h-1").status_code == 201

    again = create(container_client, key, container_token, run_hash="h-1",
                   requested_versions=written_for)
    assert (again.status_code, again.get_json()["id"]) == (200, existing)


def test_a_hit_needs_the_same_packages_from_the_same_indexes(container_server,
                                                             container_reuses):
    '''Job-reuse D23: a swapped mirror, or source builds turned on, may install
    something else under the same names. A job listing none does not depend
    on the indexes.'''
    jobs = container_server.config["SC_JOBS"]
    config = container_server.config["SC_CONFIG"]
    requires = {"python": {}, "tools": {}, "interpreter": {}}
    listed = '{"requirements":["numpy==2.0.1"],"constraints":[]}'

    before = jobs._identity("h-1", requires, listed)
    nothing = jobs._identity("h-1", requires)
    assert before == jobs._identity("h-1", requires, listed)
    assert before != jobs._identity(
        "h-1", requires, '{"requirements":["numpy==2.0.2"],"constraints":[]}')
    assert before != nothing

    config._values["package_indexes"] = ["https://mirror.example/simple/"]
    mirrored = jobs._identity("h-1", requires, listed)
    config._values["python_source_builds"] = True
    built = jobs._identity("h-1", requires, listed)

    assert len({before, mirrored, built}) == 3
    assert jobs._identity("h-1", requires) == nothing


def test_a_candidate_whose_images_were_superseded_is_not_returned(
        container_server, container_client, key, container_token, container_me,
        container_reuses):
    '''The identity folds in only the DECLARED versions' digests, all there is
    at create, so a re-registered TOOL image leaves it unchanged; a finished
    job records what its nodes RAN IN, and those must still be live.'''
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    existing = reuse_job(container_server.config["SC_JOBS"], store, container_me, "h-1",
                         "completed")
    images.register_software(store, "openroad", "OpenROAD", operator(store), "tool")
    images.register_version(store, "openroad", "2.0", operator(store))
    tools = images.register_image(
        store, "ghcr.io/x/tools:1", digest("c"),
        [("siliconcompiler", "0.38.0"), ("openroad", "2.0")], operator(store))
    store.execute(
        'INSERT INTO job_nodes (job_id, step, "index", state, image_id) '
        "VALUES (?, 'place', '0', 'completed', ?)", (existing, tools))

    assert create(container_client, key, container_token,
                  run_hash="h-1").status_code == 200

    # Rebuilt at the same reference: the old row is superseded.
    images.register_image(
        store, "ghcr.io/x/tools:1", digest("d"),
        [("siliconcompiler", "0.38.0"), ("openroad", "2.0")], operator(store))

    again = create(container_client, key, container_token, run_hash="h-1")
    assert again.status_code == 201
    assert again.get_json()["id"] != existing


def test_a_version_with_no_image_is_never_advertised(container_server, container_client):
    '''So a client is refused before it uploads, not told yes and refused at submit.'''
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    images.register_version(store, "siliconcompiler", "0.38.1", operator(store),
                            preference=99)

    software = container_client.get("/v1").get_json()["software"]

    assert software["python"]["siliconcompiler"] == ["0.38.0"]


def test_an_image_of_another_siliconcompiler_is_neither_advertised_nor_used(
        registry, key):
    '''One version, the one this server runs (profile §5): an image holding
    another is registered but never advertised or run.'''
    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.state.store import Store

    with Store("container-datadir/server.db") as store:
        actor = operator(store)
        images.register_version(store, "siliconcompiler", "99.0.0", actor, preference=99)
        images.register_image(store, "ghcr.io/x/future:99", digest("f"),
                              [("siliconcompiler", "99.0.0")], actor)

    app = create_app("container-datadir", cluster="local")
    client = app.test_client()
    token = login(client, key).get_json()["access_token"]

    assert client.get("/v1").get_json()["software"]["python"]["siliconcompiler"] == \
        [images.own_version()]

    refused = create(client, key, token, requested_versions=wants("99.0.0"))
    assert (refused.status_code, slug(refused)) == (422, "software-unavailable")
    assert refused.get_json()["unresolved"][0]["name"] == "siliconcompiler"

    # A job asking for nothing in particular runs in this server's own version's image.
    job = create(client, key, token).get_json()
    held = app.config["SC_STORE"].one("SELECT image_id FROM jobs WHERE id = ?",
                                      (job["id"],))["image_id"]
    assert held == app.config["SC_STORE"].one(
        "SELECT id FROM images WHERE digest = ?", (digest("a"),))["id"]


def test_a_host_deployment_places_nothing_and_resolves_nothing(
        server, server_client, key, token, job_archive, dispatcher):
    '''NULL image ids, not a default: `image_id` is what a node ran in.
    `resolved_versions` absent, as `{}` would claim it ran nothing. No queue,
    which a deployment without a partition for this leaves to the cluster.'''
    job, _ = submitted(server_client, key, token, job_archive())

    store = server.config["SC_STORE"]
    assert store.one("SELECT image_id FROM jobs WHERE id = ?", (job["id"],))["image_id"] is None
    assert all(node["image_id"] is None for node in store.all(
        "SELECT image_id FROM job_nodes WHERE job_id = ?", (job["id"],)))
    assert "resolved_versions" not in read(server_client, key, token, job["id"])
    assert dispatcher.handed == {"image": None, "queue": None}


def fake_unpack(root, ref, digest, mounts=()):
    '''What `images.stage_bundle` leaves, without skopeo and umoci: a shared
    bundle whose configuration binds what it was staged with.'''
    from siliconcompiler.remote.server.software import images

    bundle = images.bundle_path(root, digest)
    (bundle / "rootfs").mkdir(parents=True, exist_ok=True)
    spec = {"root": {"path": "rootfs"}, "process": {"args": ["sh"]}, "mounts": [
        {"destination": "/proc", "type": "proc", "source": "proc"}]}
    images._add_mounts(spec, mounts)
    (bundle / "config.json").write_text(json.dumps(spec))
    return bundle


def visible(bundle, path):
    '''How a container started from ``bundle`` sees ``path``: `rw`, `ro`,
    or None where no bind mount reaches it.'''
    import os

    spec = json.loads((Path(bundle) / "config.json").read_text())
    path = os.path.realpath(str(path))
    seen = None
    for entry in spec.get("mounts") or []:
        source = os.path.realpath(entry.get("source") or "")
        options = entry.get("options") or []
        if entry.get("type") != "bind" and "rbind" not in options and "bind" not in options:
            continue
        if path == source or path.startswith(source + os.sep):
            seen = "ro" if "ro" in options else "rw"
    return seen


@pytest.fixture
def slurm(container_server, monkeypatch):
    '''A cluster dispatcher on the container deployment, the unpack (skopeo
    and umoci, the cluster's business) faked.'''
    from siliconcompiler.remote.server.software import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake
    monkeypatch.setattr(images, "stage_bundle", fake_unpack)
    return fake


def test_a_cluster_gets_a_bundle_and_never_a_partition(
        container_server, container_client, key, container_token, job_archive, slurm):
    '''On a cluster `scheduler,queue` is a PARTITION, so an image reference
    there would name a partition after a container. The orchestrator, which
    coordinates and computes nothing, goes to a queue of its own.'''
    from siliconcompiler.remote.server.running import runspec

    container_server.config["SC_CONFIG"]._values["batch_queue"] = "coordinator"
    job, _ = submitted(container_client, key, container_token, job_archive(),
                       requested_versions=wants("0.38.0"))

    manifest = slurm.submitted[0][2]
    scheduler = run_manifest(manifest).option.scheduler
    assert scheduler.get_name(step="stepone", index="0") == "slurm"
    assert scheduler.get_queue(step="stepone", index="0") is None

    options = scheduler.get_options(step="stepone", index="0")
    bundle = options[options.index("--container") + 1]
    # The job's own bundle, outside any user's tree so no node can rewrite it,
    # over a shared one: one digest is one root filesystem for everybody.
    assert bundle.endswith(digest("a").replace("sha256:", ""))
    assert f"/jobbundles/{job['id']}/" in bundle
    assert "/users/" not in bundle

    # Where to get the bytes, which the path cannot say, and what it mounts.
    state = runspec.state_dir(manifest) / runspec.IMAGES_FILENAME
    sources, mounts = runspec.read_images(state)
    shared, job_mounts = runspec.read_bundles(state)
    assert sources[bundle] == f"ghcr.io/x/sc@{digest('a')}"
    assert "/images/" in shared[bundle]
    # Never the data directory: the signing key, the store, every user's tree.
    datadir = str(Path("container-datadir").resolve())
    assert datadir not in [str(m) for m in mounts]
    assert [str(runspec.state_dir(manifest)), "rw"] in job_mounts

    # The batch job runs in the framework image, the job's own bundle too, so
    # the process INTERPRETING the manifest is the SiliconCompiler asked for.
    framework = Path(slurm.handed["image"])
    assert slurm.handed["queue"] == "coordinator"
    assert framework.parent == Path(bundle).parent
    assert visible(framework, f"{datadir}/server.db") is None
    assert visible(framework, f"{datadir}/token-signing-key") is None
    assert visible(framework, runspec.state_dir(manifest)) == "rw"


def test_a_container_job_cannot_read_the_signing_key_or_the_store(
        container_server, container_client, key, container_token, job_archive, slurm,
        monkeypatch):
    '''A node sees its job's tree and its user's cache read-write, the
    supplied roots read-only, and nothing else of the data directory
    (profile §0). The run writes the bundle from what the server recorded.'''
    from siliconcompiler.remote.server.running import runner, runspec

    job, _ = submitted(container_client, key, container_token, job_archive(),
                       requested_versions=wants("0.38.0"))

    manifest = slurm.submitted[0][2]
    state = runspec.state_dir(manifest) / runspec.IMAGES_FILENAME
    monkeypatch.setattr(runner, "_image_sources", runspec.read_images(state)[0])
    monkeypatch.setattr(runner, "_image_mounts", runspec.read_images(state)[1])
    shared, job_mounts = runspec.read_bundles(state)
    monkeypatch.setattr(runner, "_image_shared", shared)
    monkeypatch.setattr(runner, "_job_mounts", job_mounts)

    bundle, = set(runner._image_sources)
    runner._unpack_bundle(bundle)

    datadir = Path("container-datadir").resolve()
    jobs = container_server.config["SC_JOBS"]
    assert visible(bundle, datadir / "server.db") is None
    assert visible(bundle, datadir / "token-signing-key") is None
    assert visible(bundle, datadir / "users" / "somebody-else" / "builds") is None
    assert visible(bundle, datadir / "jobbundles" / job["id"]) is None
    assert visible(bundle, datadir / "images") is None
    assert visible(bundle, runspec.state_dir(manifest)) == "rw"
    assert visible(bundle, jobs.cache_dir(job["owner"]["id"])) == "rw"
    assert visible(bundle, datadir / "sources") == "ro"
    # Over the shared root filesystem, which it does not copy.
    spec = json.loads((Path(bundle) / "config.json").read_text())
    assert spec["root"]["path"] == str(Path(shared[bundle]).resolve() / "rootfs")


def test_every_directory_a_job_bundle_binds_exists(
        container_server, container_client, key, container_token, job_archive, slurm):
    '''A bind with no source stops the runtime starting the container, and a
    fresh data directory has no `sources/`; a missing private root is left out.'''
    import shutil

    container_server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"acme": {"acme": "/nonexistent/acme-pdk"}}}
    shutil.rmtree(Path("container-datadir/sources"), ignore_errors=True)

    submitted(container_client, key, container_token, job_archive(),
              requested_versions=wants("0.38.0"))

    spec = json.loads((Path(slurm.handed["image"]) / "config.json").read_text())
    sources = [entry["source"] for entry in spec["mounts"] if entry.get("type") == "none"]
    assert sources and all(Path(source).exists() for source in sources)
    assert "/nonexistent/acme-pdk" not in sources
