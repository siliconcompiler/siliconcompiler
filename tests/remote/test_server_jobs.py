
from pathlib import Path

import pytest

from conftest import call, job_after, login, run_manifest, slug


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.state.store import now                  # noqa: E402


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
        self.cancelled_nodes = []
        self.still_running = set()
        self.handed = {}
        self.alive = True

    def submit(self, job_id, jobroot, manifest, image=None, queue=None):
        self.submitted.append((job_id, jobroot, manifest))
        self.handed = {"image": image, "queue": queue}
        return f"fake:{len(self.submitted)}"

    def is_alive(self, scheduler_job_id):
        return self.alive

    def cancel(self, scheduler_job_id, node_job_ids=()):
        # None means "only the orphans": the run itself is already gone, and
        # the real dispatcher skips it rather than scancelling a finished job.
        if scheduler_job_id:
            self.cancelled.append(scheduler_job_id)
        self.cancelled_nodes = list(node_job_ids)

    def node_jobs(self, job_id, nodes):
        # What a real cluster answers: one scheduler id per node, addressed by
        # the name the server can derive without being told anything.
        return {node: f"{job_id}_{node[0]}_{node[1]}" for node in nodes}

    def running_nodes(self, job_id, nodes):
        return [f"{job_id}_{step}_{index}" for step, index in nodes
                if (step, index) in self.still_running]

    def describe(self, scheduler_job_id):
        return f"the scheduler's record of {scheduler_job_id}"


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def jobs(server):
    return server.config["SC_JOBS"]


def wants(sc=None, tools=None):
    """A bucketed `requested_versions`, as the descriptor carries it: every value a list.

    🔴 Two buckets because they resolve differently: the whole python set has
    to be held by ONE image, and a tool is satisfied per node.
    """
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
    '''The ids of ``count`` jobs, each created a few milliseconds after the
    last. The listing orders by `created_at`, which holds milliseconds, and
    breaks a tie by the id, which is a UUIDv4 and sorts at random.'''
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


def stage(client, key, token, archive, size, **body):
    '''A job with its bytes uploaded, ready to submit.'''
    job = create(client, key, token, **body).get_json()
    grant = call(client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token,
                 json=dict(grant_for(archive), size_bytes=size)).get_json()
    put(client, grant, open(archive, "rb").read())
    return job


def submit(client, key, token, job_id, digest=None, size=None, **extra):
    '''``digest`` and ``size`` are taken for the callers' symmetry with
    `stage` and never sent: submit takes no body, and the upload is checked
    against the digest the grant bound (surface §15). ``extra`` is sent, to
    test the refusal of a body with a member.'''
    headers = {}
    if "idempotency_key" in extra:
        headers["Idempotency-Key"] = extra.pop("idempotency_key")
    return call(client, key, "POST", f"/v1/jobs/{job_id}/submit", token,
                json=extra, headers=headers)


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


def test_the_listing_is_ordered_by_creation_never_by_id(
        server_client, key, token, monkeypatch):
    '''A collection is ordered by `created_at`, and the id only breaks a tie
    (surface §6), so no id need sort by when it was minted: here each job's
    id sorts below the one before it.'''
    import types
    import uuid

    from siliconcompiler.remote.server.jobs import create as creating

    minted = iter([uuid.UUID(int=n << 64) for n in (3, 2, 1)])
    monkeypatch.setattr(creating, "uuid", types.SimpleNamespace(uuid4=lambda: next(minted)))

    ids = created_in_order(server_client, key, token, 3)
    assert ids == sorted(ids, reverse=True)

    body = call(server_client, key, "GET", "/v1/jobs", token).get_json()
    assert [item["id"] for item in body["items"]] == list(reversed(ids))


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
    response = create(server_client, key, token, flow="asicflow", node_count=10 ** 9)

    assert response.status_code == 403
    assert slug(response) == "node-limit-exceeded"
    assert response.get_json()["limit"] == "max_job_nodes"


def test_an_upload_larger_than_the_ceiling_is_refused_at_the_grant(
        server_client, key, token):
    '''🔴 At the grant, which fixes the size -- `resources.upload_bytes` is
    gone from create, and this call still comes before any byte moves.'''
    job = create(server_client, key, token).get_json()
    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                    token, json=sized(1 << 40))

    assert response.status_code == 413
    assert slug(response) == "upload-too-large"
    assert response.get_json()["limit"] == "max_upload_bytes"


@pytest.mark.parametrize("member", [
    {"versions": {"python": {}}},                      # gone: `requested_versions` pins
    {"resources": {"upload_bytes": 10}},               # gone: the grant's `bytes`
    {"descriptor": {"resources": {"upload_bytes": 10}}},
    {"descriptor": {"flow": {"name": "f", "tools": ["yosys"]}}},   # gone: a flow object
    # The names before the consistency pass (surface D289): no old name is taken
    # beside its new one, since that would be a second spelling kept for ever.
    {"descriptor": {"requires": {"python": {}}}},      # now `requested_versions`
    {"descriptor": {"flow": {"name": "asicflow", "nodes": 3}}},   # now `flow`, `node_count`
    {"descriptor": {"node_count": "3"}},
    {"extra": 1},
])
def test_an_unknown_member_is_refused_never_ignored(server_client, key, token, member):
    '''🔴 Strict on requests: a misspelled optional member would otherwise be
    a check the caller believes they asked for, and a member of the wrong shape
    one it cannot have.'''
    response = create(server_client, key, token, **member)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_run_hash_is_a_top_level_member_and_not_a_descriptor_one(
        server_client, key, token):
    '''Beside `design` and `jobname` (surface D160, job-reuse D15): the
    descriptor holds what submit re-derives, and nothing recomputes this.'''
    top = call(server_client, key, "POST", "/v1/jobs", token,
               json={"design": "gcd", "jobname": "job0", "run_hash": "abc"})
    inside = call(server_client, key, "POST", "/v1/jobs", token,
                  json={"design": "gcd", "jobname": "job1",
                        "descriptor": {"run_hash": "abc"}})

    assert top.status_code == 201 and inside.status_code == 400


@pytest.mark.parametrize("value", ["", "x" * 129, "ok\u2713", "tab\there", 7])
def test_run_hash_is_1_to_128_printable_ascii(server_client, key, token, value):
    response = create(server_client, key, token, run_hash=value)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_without_jobs_reuse_a_hash_is_validated_and_ignored(
        server, server_client, key, token, me):
    '''This deployment does not advertise `jobs.reuse`, so create is always a
    201 -- even for the hash of a job it has finished.'''
    assert "jobs.reuse" not in server.config["SC_CONFIG"]["features"]
    existing = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"],
                         me, "hash-1", "completed")

    response = create(server_client, key, token, run_hash="hash-1")

    assert response.status_code == 201
    assert response.get_json()["id"] != existing
    stored = server.config["SC_STORE"].one(
        "SELECT run_hash, job_identity FROM jobs WHERE id = ?", (response.get_json()["id"],))
    assert (stored["run_hash"], stored["job_identity"]) == ("hash-1", None)


def test_a_requirement_is_always_a_list(server_client, key, token):
    '''A bare string is refused: SiliconCompiler's own requirement is a list
    of alternatives, one per task.'''
    bare = create(server_client, key, token,
                  requested_versions={"python": {"siliconcompiler": "==0.38.0"}, "tools": {}})
    listed = create(server_client, key, token, jobname="job1",
                    requested_versions={"python": {}, "tools": {"yosys": []}})

    assert bare.status_code == 400 and "list" in bare.get_json()["detail"]
    assert listed.status_code == 201


def test_a_private_source_carries_no_source_and_no_ref(server_client, key, token):
    '''`private` defaults to false; when true, its path never leaves the
    client, so a `source` or `ref` beside it is refused rather than trusted.'''
    defaulted = create(server_client, key, token, sources=[
        {"name": "ip", "dataroot": "ip",
         "source": "git+ssh://git@example.com/ip.git", "ref": "v1"}])
    leaked = create(server_client, key, token, jobname="job1", sources=[
        {"name": "gf180", "dataroot": "gf180", "private": True,
         "source": "file:///opt/pdks/gf180"}])

    assert defaulted.status_code == 201
    assert leaked.status_code == 400


def test_a_need_the_server_lacks_is_refused_at_create_naming_it(server_client, key, token):
    '''Before the upload, rather than at submit after it -- and a string the
    server does not know is refused the same way.'''
    lacking = create(server_client, key, token, needs=["python.env"])
    known = create(server_client, key, token, jobname="job1", needs=["logs.stream"])

    assert lacking.status_code == 501
    assert (slug(lacking), lacking.get_json()["feature"]) == \
        ("feature-unsupported", "python.env")
    assert known.status_code == 201


def test_create_answers_with_the_job_object(server_client, key, token):
    '''🔴 The separate create shape is gone: `upload_sources` is the job
    object's own member, absent where there is nothing to send.'''
    body = create(server_client, key, token, sources=[]).get_json()

    assert body["terminal"] is False and body["state"] == "created"
    assert "upload_sources" not in body


def test_submit_takes_the_digest_and_nothing_else(server_client, key, token, job_archive):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, bytes=size)

    assert response.status_code == 400 and slug(response) == "invalid-request"


def test_a_sparse_descriptor_is_never_refused_for_being_sparse(server_client, key, token):
    '''No field is required. The server checks whatever is present and skips
    the check a missing field would have answered.'''
    assert create(server_client, key, token, descriptor={}).status_code == 201


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
    # A replayed create is `201`, with the original body.
    assert second.status_code == 201
    assert first.get_json() == second.get_json()


def test_the_same_key_with_a_different_body_is_refused(server_client, key, token):
    '''Returning the first job would answer a question the caller did not
    ask.'''
    create(server_client, key, token, idempotency_key="k1")
    response = create(server_client, key, token, jobname="other", idempotency_key="k1")

    assert response.status_code == 422
    assert slug(response) == "idempotency-key-reuse"


def test_a_refused_create_binds_no_key(server, server_client, key, token):
    '''A refused create has no side effect, so a retry with the same key and
    body is evaluated afresh: once the cause is gone, it is `201` (surface §6,
    *Idempotency*; database D144).'''
    server.config["SC_CONFIG"].limits["pending_uploads"] = 1
    held = create(server_client, key, token, jobname="held").get_json()

    refused = create(server_client, key, token, idempotency_key="k1")
    assert (refused.status_code, slug(refused)) == (429, "limit-exceeded")

    call(server_client, key, "POST", f"/v1/jobs/{held['id']}/cancel", token, json={})
    again = create(server_client, key, token, idempotency_key="k1")

    assert again.status_code == 201, again.get_json()


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

@pytest.fixture
def reuses(server):
    '''A deployment advertising `jobs.reuse`, which this one does not by
    default: reuse's server half, proven here rather than left as dead code.'''
    config = server.config["SC_CONFIG"]
    config._values["features"] = list(config["features"]) + ["jobs.reuse"]


@pytest.fixture
def container_reuses(container_server):
    config = container_server.config["SC_CONFIG"]
    config._values["features"] = list(config["features"]) + ["jobs.reuse"]


def reuse_job(jobs, store, user_id, run_hash, state, declared=None, **columns):
    '''A finished job with a hash, written straight into the store.

    ⚠️ It writes `job_identity` as well, through the service, because that is
    what the lookup is keyed on: the client's hash is only half of it and the
    server's resolved digests are the other half.
    '''
    import uuid

    job_id = str(uuid.uuid4())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "                  run_hash, job_identity, manifest_pdk) "
        "VALUES (?, ?, ?, 'gcd', 'old', '{}', ?, ?, 'none')",
        (job_id, user_id, state, run_hash,
         jobs._identity(run_hash, declared or {})))
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
                                        state, returned, reuses):
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


def test_an_archived_job_is_never_returned(server, server_client, key, token, me, reuses):
    '''The one thing ever added to archived_at's "and NOTHING else". It is how a
    person says stop handing me that result, with no endpoint for it.'''
    store = server.config["SC_STORE"]
    existing = reuse_job(server.config["SC_JOBS"], store, me, "hash-1", "completed",
                         archived_at="2026-01-01T00:00:00.000Z", archived_by=me)

    response = create(server_client, key, token, run_hash="hash-1")

    assert response.status_code == 201
    assert response.get_json()["id"] != existing


def test_the_lookup_is_owner_scoped(server, server_client, key, token, reuses):
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
                 f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(4096))
    second = call(server_client, key, "POST",
                  f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(4096))

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
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant", token,
         json=sized(4096))

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "awaiting_input"
    assert read["terminal"] is False


def test_the_first_grant_fixes_the_size_and_a_re_issue_repeats_it(
        server_client, key, token):
    '''🔴 D125: the size is the grant's -- the
    create response can ask for more than the client planned to send, so a
    size fixed at create made the PUT fail its signature. A re-issue cannot
    widen what the first grant bound.'''
    job = create(server_client, key, token).get_json()
    path = f"/v1/jobs/{job['id']}/upload-grant"

    grant = call(server_client, key, "POST", path, token, json=sized(4096)).get_json()
    assert grant["headers"]["content-length"] == "4096"

    again = call(server_client, key, "POST", path, token, json=sized(4096))
    assert again.status_code == 200

    widened = call(server_client, key, "POST", path, token, json=sized(8192))
    assert widened.status_code == 409
    assert slug(widened) == "job-state-conflict"


def test_a_grant_without_its_size_is_refused(server_client, key, token):
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "POST",
                    f"/v1/jobs/{job['id']}/upload-grant", token)

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_the_uploads_of_one_job_are_bounded_together(
        server, server_client, key, token):
    server.config["SC_CONFIG"].limits["max_upload_bytes"] = 1000
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "POST",
                    f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(1001))

    assert response.status_code == 413
    assert response.get_json()["limit"] == "max_upload_bytes"


def test_no_grant_for_a_job_that_is_past_it(server, server_client, key, token, me):
    existing = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"],
                         me, None, "completed")

    response = call(server_client, key, "POST",
                    f"/v1/jobs/{existing}/upload-grant", token, json=sized(4096))

    assert response.status_code == 409
    assert slug(response) == "job-state-conflict"


###########################
# The signed PUT
###########################

def test_the_signature_is_the_credential(server_client, key, token, job_archive):
    '''No Authorization header and no proof: that is what a presigned URL is.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(size, digest)).get_json()

    response = put(server_client, grant, open(archive, "rb").read())

    assert response.status_code == 200
    assert response.get_json()["size_bytes"] == size


def test_an_altered_url_is_refused(server_client, key, token, job_archive):
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(size, digest)).get_json()

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
    # 🔴 `staging`, always: the request only matched the digest.
    assert response.get_json()["state"] == "staging"
    assert response.get_json()["state_reason"] == "unpacking the upload"

    body = job_after(server_client, key, token, response)
    assert body["state"] == "queued"
    assert "state_reason" not in body
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
    opened. The upload is checked against the digest its grant bound, before
    anything is extracted.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                 token, json=sized(size, digest)).get_json()
    put(server_client, grant, b"\0" * size)

    response = submit(server_client, key, token, job["id"])

    assert response.status_code == 422
    assert slug(response) == "upload-digest-mismatch"
    assert "the grant bound" in response.get_json()["detail"]

    root = server.config["SC_JOBS"].job_root(
        call(server_client, key, "GET", "/v1/me", token).get_json()["id"], job["id"])
    assert not root.exists()

    # 🔴 A refusal of the request, not of the archive: the job still waits,
    # and the bytes the grant was issued for, sent to it, submit it.
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "awaiting_input"
    assert read["error"] is None

    put(server_client, grant, open(archive, "rb").read())
    again = submit(server_client, key, token, job["id"])
    assert again.status_code == 202
    assert job_after(server_client, key, token, again)["state"] == "queued"


def test_bytes_short_of_the_grant_are_a_digest_mismatch(server_client, key, token,
                                                        job_archive, dispatcher):
    '''No `bytes` at submit: the digest is what says the bytes are the ones
    the client meant, and a short upload has a different one.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                 token, json=sized(size, digest)).get_json()
    put(server_client, grant, open(archive, "rb").read()[: size // 2])

    response = submit(server_client, key, token, job["id"], digest)

    assert response.status_code == 422
    assert slug(response) == "upload-digest-mismatch"


def test_a_submit_body_with_a_member_is_refused(server_client, key, token,
                                                job_archive, dispatcher):
    '''Submit takes no body (surface §15; D277), and nothing is ignored: a
    member -- the digest a client used to send included -- is refused under
    the strict rule.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest=digest)
    assert response.status_code == 202

    other = stage(server_client, key, token, archive, size, jobname="job1")
    refused = call(server_client, key, "POST", f"/v1/jobs/{other['id']}/submit", token,
                   json={"digest": digest})
    assert (refused.status_code, slug(refused)) == (400, "invalid-request")


def test_an_archive_violation_names_which_rule(server_client, key, token,
                                               job_archive, dispatcher):
    archive, digest, size = job_archive(
        extra={"../escape": b"owned"})
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 202
    read = job_after(server_client, key, token, response)
    assert read["state"] == "rejected"
    assert read["error"]["type"].endswith("archive-rejected")
    assert read["error"]["status"] == 422
    assert read["error"]["reason"] == "traversal"


def test_a_manifest_that_is_not_where_it_was_declared(server_client, key, token,
                                                      nop_project, job_archive,
                                                      dispatcher):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size, jobname="somethingelse")

    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 202
    read = job_after(server_client, key, token, response)
    assert read["error"]["type"].endswith("declared-mismatch")


def test_submitting_with_nothing_uploaded(server_client, key, token):
    job = create(server_client, key, token).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant", token,
         json=sized(4096))

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

    for member in ("id", "state", "terminal", "transitions", "design",
                   "jobname", "flow", "owner", "project", "created_at",
                   "submitted_at", "started_at", "finished_at", "archived_at",
                   "deleted_at", "deleted_reason", "error", "nodes", "progress"):
        assert member in body, member
    # 🔴 `transitions` in place of `state_changed_at` (D278), never empty, and
    # no `deleted_cause`: every job deletion is a person's (D279).
    assert "state_changed_at" not in body and "deleted_cause" not in body
    assert [entry["state"] for entry in body["transitions"]] == ["created"]
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
    ids = created_in_order(server_client, key, token, 3)

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
    ids = created_in_order(server_client, key, token, 5)

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


@pytest.mark.parametrize("reason", ["x" * 301, "x" * 5000, "two\nlines", "a\x07bell"])
def test_a_cancel_reason_over_its_bound_is_refused_never_cut(
        server_client, key, token, reason):
    '''User-controlled text that the portal renders and a CLI prints: at most
    300 characters of one line (surface D288), refused rather than repaired,
    and never echoed.'''
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                    json={"reason": reason})

    assert response.status_code == 400
    assert slug(response) == "invalid-request"
    assert "300" in response.get_json()["detail"]
    assert reason not in response.get_json()["detail"]


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
    assert read["error"]["type"].endswith("run-interrupted")
    assert "status" not in read["error"]
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
    '''A sparse descriptor is legal: the size is the grant's (D125), and the
    digest at submit is what settles what the bytes actually are.'''
    archive, digest, size = job_archive()
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(size, digest)).get_json()

    assert int(grant["headers"]["content-length"]) == size

    assert put(server_client, grant, open(archive, "rb").read()).status_code == 200
    assert submit(server_client, key, token, job["id"], digest,
                  size).status_code == 202


def test_an_upload_past_the_ceiling_is_refused_as_it_arrives(
        server_client, key, token):
    '''Enforced on what has been written rather than on Content-Length, which is
    a claim the sender makes about a body it is still sending.'''
    job = create(server_client, key, token).get_json()
    grant = call(server_client, key, "POST",
                 f"/v1/jobs/{job['id']}/upload-grant", token, json=sized(16)).get_json()

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
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = (server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0")
    progress = root.parents[1] / runspec.PROGRESS_FILENAME

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
    # 🔴 And its nodes as the settled file has them. The first reading had
    # stepone running and no steptwo, and a job that ends settles what it
    # never finished as `cancelled`: both nodes, which had completed, went
    # that way.
    assert {node["step"]: node["state"] for node in read["nodes"]} == \
        {"stepone": "completed", "steptwo": "completed"}


def test_a_cancel_still_wins_when_the_run_finished_while_we_looked(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''A run that finished between the two readings, of a job being
    cancelled, ends `cancelled`, as it does when the first reading already
    had the result: what it managed before it died does not change what was
    asked for.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = (server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0")
    progress = root.parents[1] / runspec.PROGRESS_FILENAME
    runspec.write_progress(progress, {
        "state": "running", "started_at": "2026-09-22T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"}}})
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token, json={})

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

    assert read["state"] == "cancelled"


def test_a_job_that_really_is_gone_is_still_reported_lost(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''Reading the file twice must not turn a lost job into a hung one.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = (server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0")
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-22T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"}}})

    dispatcher.alive = False

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("run-interrupted")


###########################
# Placing a job in a container
###########################

def digest(letter):
    return "sha256:" + letter * 64


def operator(store):
    return store.one("SELECT id FROM users WHERE issuer = 'operator'")["id"]


@pytest.fixture
def registry(runs_test_version):
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

    with pytest.raises(RuntimeError, match="no live image holds siliconcompiler"):
        create_app("empty-registry", cluster="local")


def test_submit_records_the_image_each_node_ran_in(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher):
    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants("0.38.0"))

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

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    manifest = container_dispatcher.submitted[0][2]
    project = run_manifest(manifest)

    assert project.option.scheduler.get_name(step="stepone", index="0") == "docker"
    assert project.option.scheduler.get_queue(step="stepone", index="0") == \
        f"ghcr.io/x/sc@{digest('a')}"


def test_a_tool_with_no_image_fails_the_whole_submit(
        container_server, container_client, key, container_token,
        job_archive, container_dispatcher, monkeypatch):
    """🔴 Before anything runs, which is the correct direction: the alternative
    is a job that queues, dispatches and dies on node thirty-one with the
    cluster already paid for."""
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]

    # The operator takes the claim on and never puts it in an image, which is
    # the whole condition: this deployment now says it curates OpenROAD and
    # cannot place a node that needs it.
    images.register_software(store, "openroad", "OpenROAD", operator(store), "tool")
    images.register_version(store, "openroad", "2.0", operator(store))

    # `nopflow` names only `builtin`, which is not a tool anybody installs and
    # raises no requirement. This is the one thing the test needs it to be.
    from siliconcompiler.remote import runflow

    monkeypatch.setattr(runflow, "node_tools",
                        lambda flow, nodes: {node: "openroad" for node in nodes})

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size)

    response = submit(container_client, key, container_token, job["id"],
                      upload_digest, size)

    assert response.status_code == 202
    assert not container_dispatcher.submitted

    read = call(container_client, key, "GET", f"/v1/jobs/{job['id']}",
                container_token).get_json()
    assert read["state"] == "rejected"
    assert read["error"]["type"].endswith("software-unavailable")
    assert read["error"]["reason"] == "unavailable"
    assert read["error"]["unresolved"] == [
        {"name": "openroad", "requirement": [], "available": []}]


def test_the_job_publishes_the_versions_the_server_resolved(
        container_server, container_client, key, container_token, job_archive,
        container_dispatcher):
    """🔴 Once a request can carry a range, nothing else answers *what did this
    job run*: the descriptor says what was asked for and this says what the
    server chose."""
    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants(">=0.38,<0.39"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    read = call(container_client, key, "GET", f"/v1/jobs/{job['id']}",
                container_token).get_json()

    assert read["resolved_versions"] == {"python": {"siliconcompiler": ["0.38.0"]},
                                         "tools": {}}


def test_a_job_that_resolved_nothing_says_nothing(server, server_client, key,
                                                  token, job_archive, dispatcher):
    """⚠️ Absent and not empty. On a deployment that runs jobs on the host
    there is no image and no answer, and `{}` would claim this job ran
    nothing at all."""
    archive, upload_digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], upload_digest, size)

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}",
                token).get_json()

    assert "resolved_versions" not in read


def test_a_range_no_image_satisfies_is_refused_at_create(
        container_server, container_client, key, container_token):
    """✅ Resolution needs the declared versions and the registry, not the
    uploaded bytes -- so it happens before the upload, where it is free."""
    response = create(container_client, key, container_token,
                      requested_versions=wants(">=0.40"))

    assert response.status_code == 422
    assert slug(response) == "software-unavailable"
    assert response.get_json()["unresolved"][0]["name"] == "siliconcompiler"


def test_a_range_the_registry_can_serve_is_accepted_at_create(
        container_server, container_client, key, container_token):
    assert create(container_client, key, container_token,
                  requested_versions=wants(">=0.38,<0.39")).status_code == 201


def test_a_bare_version_is_still_an_exact_pin(container_server,
                                              container_client, key,
                                              container_token):
    """⚠️ It is what every client sent before the wire carried ranges."""
    assert create(container_client, key, container_token,
                  requested_versions=wants("0.38.0")).status_code == 201
    assert create(container_client, key, container_token,
                  requested_versions=wants("0.38.1")).status_code == 422


def test_a_name_that_reports_no_version_is_told_so_and_not_told_no_match(
        container_server, container_client, key, container_token):
    """🔴 `GET /v1`'s `software` has nowhere to carry the mark, so a client's
    own preflight said yes. *No image matches* would send them looking for a
    version of a tool that is already installed; the true answer is that
    nothing here can be matched against a range."""
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

    # 🔴 Software no image holds, not skew: `version-skew` is the client's own
    # SiliconCompiler, which cannot run here (surface §7).
    assert response.status_code == 422
    assert slug(response) == "software-unavailable"
    assert "reports no version" in response.get_json()["detail"]
    assert response.get_json()["unresolved"] == [
        {"name": "magic", "requirement": [">=8.0"], "available": []}]


def test_the_job_identity_folds_in_what_the_server_chose(
        container_server, container_client, key, container_token, container_reuses):
    """🔴 The client's hash alone is not the job's identity. It hashes the
    work; this server chooses what runs it -- so re-registering an image
    invalidates reuse exactly when it should, because a new digest is
    precisely *the code changed*."""
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    jobs = container_server.config["SC_JOBS"]
    mine = call(container_client, key, "GET", "/v1/me",
                container_token).get_json()["id"]

    existing = reuse_job(jobs, store, mine, "h-1", "completed")

    # 200 and the old job: same work, same image.
    again = create(container_client, key, container_token, run_hash="h-1")
    assert again.status_code == 200
    assert again.get_json()["id"] == existing

    # The same tag, rebuilt. The old row is superseded and the digest is new,
    # which is precisely "the code changed".
    images.register_image(store, "ghcr.io/x/sc:0.38.0", digest("b"),
                          [("siliconcompiler", "0.38.0")], operator(store))

    after = create(container_client, key, container_token, run_hash="h-1")
    assert after.status_code == 201
    assert after.get_json()["id"] != existing


def test_a_candidate_whose_images_were_superseded_is_not_returned(
        container_server, container_client, key, container_token, container_reuses):
    """🔴 What the identity cannot catch. It folds in the digests the DECLARED
    versions resolve to, because that is all there is at create -- the per-node
    tool images need the flow, which needs the manifest, which needs the upload
    the check exists to avoid. So re-registering an image that only ever served
    a TOOL leaves the identity unchanged.

    ✅ A finished job records what its nodes RAN IN, so the question is asked
    the other way round: are those images still live?
    """
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    jobs = container_server.config["SC_JOBS"]
    mine = call(container_client, key, "GET", "/v1/me",
                container_token).get_json()["id"]

    existing = reuse_job(jobs, store, mine, "h-1", "completed")

    # It ran one node in a tool image, which nothing about the declared
    # versions mentions.
    images.register_software(store, "openroad", "OpenROAD", operator(store),
                             "tool")
    images.register_version(store, "openroad", "2.0", operator(store))
    tools = images.register_image(
        store, "ghcr.io/x/tools:1", digest("c"),
        [("siliconcompiler", "0.38.0"), ("openroad", "2.0")], operator(store))
    store.execute(
        'INSERT INTO job_nodes (job_id, step, "index", state, image_id) '
        "VALUES (?, 'place', '0', 'completed', ?)", (existing, tools))

    # Still live, so the candidate stands.
    assert create(container_client, key, container_token,
                  run_hash="h-1").status_code == 200

    # Rebuilt at the same reference: the old row is superseded.
    images.register_image(
        store, "ghcr.io/x/tools:1", digest("d"),
        [("siliconcompiler", "0.38.0"), ("openroad", "2.0")], operator(store))

    again = create(container_client, key, container_token, run_hash="h-1")
    assert again.status_code == 201
    assert again.get_json()["id"] != existing


def test_a_job_that_ran_in_no_image_stays_reusable(server, server_client, key,
                                                   token, me, reuses):
    """A deployment that runs jobs on the host has nothing to check."""
    existing = reuse_job(server.config["SC_JOBS"], server.config["SC_STORE"],
                         me, "h-1", "completed")

    response = create(server_client, key, token, run_hash="h-1")

    assert response.status_code == 200
    assert response.get_json()["id"] == existing


def test_the_stored_identity_is_not_the_clients_own_hash(
        container_server, container_client, key, container_token, container_reuses):
    """The client keeps computing its own hash and tracks nothing extra, and
    the server records both halves: what was sent, and what it is keyed on."""
    create(container_client, key, container_token, run_hash="h-1")

    row = container_server.config["SC_STORE"].one(
        "SELECT run_hash, job_identity FROM jobs WHERE run_hash = 'h-1'")

    assert row["run_hash"] == "h-1"
    assert row["job_identity"] and row["job_identity"] != "h-1"


def test_a_version_with_no_image_is_never_advertised(container_server, container_client):
    """So a client is refused before it uploads, rather than told yes and
    refused at submit."""
    from siliconcompiler.remote.server.software import images

    store = container_server.config["SC_STORE"]
    images.register_version(store, "siliconcompiler", "0.38.1", operator(store),
                            preference=99)

    software = container_client.get("/v1").get_json()["software"]

    assert software["python"]["siliconcompiler"] == ["0.38.0"]


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


def fake_unpack(root, ref, digest, mounts=()):
    '''What `images.stage_bundle` leaves, without skopeo and umoci: a
    shared bundle whose configuration binds what it was staged with -- and,
    as one staged before per-job bundles did, the whole data directory.'''
    import json

    from siliconcompiler.remote.server.software import images

    bundle = images.bundle_path(root, digest)
    (bundle / "rootfs").mkdir(parents=True, exist_ok=True)
    datadir = str(Path(root).resolve().parent)
    spec = {"root": {"path": "rootfs"}, "process": {"args": ["sh"]}, "mounts": [
        {"destination": "/proc", "type": "proc", "source": "proc"},
        {"destination": datadir, "source": datadir, "type": "none",
         "options": ["rbind", "rw"]}]}
    images._add_mounts(spec, mounts)
    (bundle / "config.json").write_text(json.dumps(spec))
    return bundle


def visible(bundle, path):
    '''How a container started from ``bundle`` sees ``path``: `rw`, `ro`,
    or None where no bind mount reaches it.'''
    import json
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


def test_a_cluster_gets_a_bundle_and_never_a_partition(
        container_server, container_client, key, container_token, job_archive,
        monkeypatch):
    '''🔴 On a cluster Slurm places the container, and `scheduler,queue` is its
    PARTITION -- so an image reference there would submit every node to a
    partition named after a container.'''
    from siliconcompiler.remote.server.running import runspec

    from siliconcompiler.remote.server.software import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake

    # The unpack itself needs skopeo and umoci, which are the cluster's
    # business and not this test's: what is under test is where the bundle is
    # and what the dispatcher is handed.
    monkeypatch.setattr(images, "stage_bundle", fake_unpack)

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    manifest = fake.submitted[0][2]
    project = run_manifest(manifest)
    scheduler = project.option.scheduler

    assert scheduler.get_name(step="stepone", index="0") == "slurm"
    assert scheduler.get_queue(step="stepone", index="0") is None

    options = scheduler.get_options(step="stepone", index="0")
    bundle = options[options.index("--container") + 1]
    # The job's own bundle, outside any user's tree so that no node can
    # rewrite it, over a shared one: the same digest is the same root
    # filesystem for everybody who runs it.
    assert bundle.endswith(digest("a").replace("sha256:", ""))
    assert f"/jobbundles/{job['id']}/" in bundle
    assert "/users/" not in bundle

    # And the run is told where to get the bytes, which the bundle path alone
    # cannot say, and what the job's own bundle mounts.
    state = runspec.state_dir(manifest) / runspec.IMAGES_FILENAME
    sources, mounts = runspec.read_images(state)
    shared, job_mounts, drop = runspec.read_bundles(state)
    assert sources[bundle] == f"ghcr.io/x/sc@{digest('a')}"
    assert "/images/" in shared[bundle]
    # 🔴 Never the data directory, in the shared bundle or the job's: it holds
    # the signing key, the store and every user's tree.
    datadir = str(Path("container-datadir").resolve())
    assert datadir not in [str(m) for m in mounts]
    assert [str(runspec.state_dir(manifest)), "rw"] in job_mounts
    assert drop == [datadir]

    # 🔴 And the batch job itself runs in the framework image, which is what
    # makes version matching real: the process that INTERPRETS the manifest is
    # the SiliconCompiler the job asked for rather than the cluster's own.
    # Its bundle is this job's too.
    framework = Path(fake.handed["image"])
    assert framework.parent == Path(bundle).parent
    assert visible(framework, f"{datadir}/server.db") is None
    assert visible(framework, f"{datadir}/token-signing-key") is None
    assert visible(framework, runspec.state_dir(manifest)) == "rw"


def test_the_orchestrator_goes_to_its_own_queue(
        container_server, container_client, key, container_token, job_archive,
        monkeypatch):
    '''🔴 The batch job coordinates; it does not compute.

    Every node is submitted from it as a job of its own, so it holds one core
    for the length of the flow and uses almost none of it. On a compute
    partition that is a node slot doing nothing.
    '''
    from siliconcompiler.remote.server.software import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake
    container_server.config["SC_CONFIG"]._values["batch_queue"] = "coordinator"
    monkeypatch.setattr(images, "stage_bundle", fake_unpack)

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size)
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    assert fake.handed["queue"] == "coordinator"


def test_a_container_job_cannot_read_the_signing_key_or_the_store(
        container_server, container_client, key, container_token, job_archive,
        monkeypatch):
    '''🔴 A node's container sees its own job's tree and its user's cache
    read-write, the supplied roots read-only, and nothing else of the data
    directory: not the token signing key, not `server.db`, and not another
    user's work (profile §0). The node's bundle is what the run writes when it
    unpacks the image, from what the server recorded beside the manifest.'''
    from siliconcompiler.remote.server.running import runner, runspec
    from siliconcompiler.remote.server.software import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake
    monkeypatch.setattr(images, "stage_bundle", fake_unpack)

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    manifest = fake.submitted[0][2]
    state = runspec.state_dir(manifest) / runspec.IMAGES_FILENAME
    monkeypatch.setattr(runner, "_image_sources", runspec.read_images(state)[0])
    monkeypatch.setattr(runner, "_image_mounts", runspec.read_images(state)[1])
    shared, job_mounts, drop = runspec.read_bundles(state)
    monkeypatch.setattr(runner, "_image_shared", shared)
    monkeypatch.setattr(runner, "_job_mounts", job_mounts)
    monkeypatch.setattr(runner, "_image_drop", drop)

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
    import json
    spec = json.loads((Path(bundle) / "config.json").read_text())
    assert spec["root"]["path"] == str(Path(shared[bundle]).resolve() / "rootfs")


def test_every_directory_a_job_bundle_binds_exists(
        container_server, container_client, key, container_token, job_archive,
        monkeypatch):
    '''🔴 A bind whose source is missing stops the runtime starting the
    container at all -- a fresh data directory has no `sources/` until the
    first fetch -- and an operator's private root that is not there is left
    out rather than bound.'''
    import shutil

    from siliconcompiler.remote.server.software import images

    fake = FakeDispatcher()
    fake.name = "slurm"
    container_server.config["SC_JOBS"]._dispatcher = fake
    container_server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "acme": {"acme": "/nonexistent/acme-pdk"}}
    monkeypatch.setattr(images, "stage_bundle", fake_unpack)
    shutil.rmtree(Path("container-datadir/sources"), ignore_errors=True)

    archive, upload_digest, size = job_archive()
    job = stage(container_client, key, container_token, archive, size,
                requested_versions=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], upload_digest, size)

    import json
    spec = json.loads((Path(fake.handed["image"]) / "config.json").read_text())
    sources = [entry["source"] for entry in spec["mounts"] if entry.get("type") == "none"]
    assert sources and all(Path(source).exists() for source in sources)
    assert "/nonexistent/acme-pdk" not in sources


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

    # The builder writes the real manifest itself, so the manifest from the
    # future replaces it in the archive: a second member of one name is
    # refused as `traversal`.
    import hashlib
    import io
    import tarfile

    built, _, _ = job_archive()
    archive = os.path.abspath("future.tar.gz")
    with tarfile.open(built) as source, tarfile.open(archive, "w:gz") as out:
        for member in source.getmembers():
            data = source.extractfile(member) if member.isfile() else None
            if member.name.lstrip("./") == f"{nop_project.name}.pkg.json":
                encoded = json.dumps(body).encode()
                member.size, data = len(encoded), io.BytesIO(encoded)
            out.addfile(member, data)
    blob = open(archive, "rb").read()
    upload_digest, size = "sha256:" + hashlib.sha256(blob).hexdigest(), len(blob)
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], upload_digest, size)

    assert response.status_code == 202
    assert not dispatcher.submitted

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}",
                token).get_json()
    assert read["state"] == "rejected"
    assert read["error"]["type"].endswith("declared-mismatch")
    assert "only backwards compatible" in read["error"]["detail"]


def test_an_image_of_another_siliconcompiler_is_neither_advertised_nor_used(
        registry, key):
    '''🔴 One version: the one this server runs (profile §5). The manifest's
    read is this server's own SiliconCompiler, so a job resolves to no other,
    and an image holding another is registered but never advertised or run.'''
    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.app import create_app
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

    # A job asking for nothing in particular runs in the image holding this
    # server's own version, picked at create.
    job = create(client, key, token).get_json()
    held = app.config["SC_STORE"].one("SELECT image_id FROM jobs WHERE id = ?",
                                      (job["id"],))["image_id"]
    assert held == app.config["SC_STORE"].one(
        "SELECT id FROM images WHERE digest = ?", (digest("a"),))["id"]


def test_a_container_deployment_whose_images_hold_another_version_does_not_start(
        runs_test_version):
    '''With containers on, a live image must hold the server's own
    SiliconCompiler, or nothing could be dispatched.'''
    import json
    import os

    from siliconcompiler.remote.server.software import images
    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.state.store import Store

    os.makedirs("elsewhere", exist_ok=True)
    with open("elsewhere/config.json", "w") as f:
        json.dump({"containers": True}, f)
    with Store("elsewhere/server.db") as store:
        with store.transaction():
            actor = store.upsert_user("operator", "someone@host")["id"]
        images.register_software(store, "siliconcompiler", "SiliconCompiler", actor,
                                 "python")
        images.register_version(store, "siliconcompiler", "99.0.0", actor)
        images.register_image(store, "ghcr.io/x/future:99", digest("f"),
                              [("siliconcompiler", "99.0.0")], actor)

    with pytest.raises(RuntimeError, match=f"no live image holds siliconcompiler "
                                           f"{images.own_version()}"):
        create_app("elsewhere", cluster="local")


###########################
# Which scheduler job a node became
###########################

def running(server, server_client, key, token, job_archive, me):
    '''A submitted job whose run has reported its nodes as started.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-23T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"},
                  "steptwo/0": {"state": "pending"}}})
    return job


def test_a_nodes_scheduler_job_is_written_down(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 *Which Slurm job was that* is the question a person brings to a
    support thread, and nothing else can answer it.

    Not published on the wire -- a registry path and a scheduler id are
    deployment detail -- but recorded, because the portal reads these rows
    directly and a cancel needs them.
    '''
    job = running(server, server_client, key, token, job_archive, me)
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    rows = server.config["SC_STORE"].all(
        'SELECT step, scheduler_job_id FROM job_nodes WHERE job_id = ? '
        'ORDER BY step', (job["id"],))

    assert [row["scheduler_job_id"] for row in rows] == \
        [f"{job['id']}_stepone_0", f"{job['id']}_steptwo_0"]


def test_it_is_asked_for_once_and_then_never_again(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''⚠️ Only the nodes still missing an id are looked up, which is what keeps
    this inside the once-per-run poll instead of turning it into per-node
    polling.'''
    job = running(server, server_client, key, token, job_archive, me)

    asked = []
    original = dispatcher.node_jobs

    def counting(job_id, nodes):
        asked.append(list(nodes))
        return original(job_id, nodes)

    dispatcher.node_jobs = counting

    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    # Once, for the two nodes that had no id. Then nothing to ask about.
    assert len(asked) == 1
    assert sorted(asked[0]) == [("stepone", "0"), ("steptwo", "0")]


def test_cancel_stops_the_work_and_not_only_the_coordinator(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 The nodes are jobs of their own now.

    Cancelling the orchestrator alone leaves them to Slurm's own cleanup --
    which usually does end them, because a job dies with the `srun` that
    allocated it, but "usually" is not what a cancel should rest on when the
    alternative is naming them.
    '''
    job = running(server, server_client, key, token, job_archive, me)
    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel",
                    token, json={})

    assert response.status_code == 202
    assert dispatcher.cancelled == ["fake:1"]
    assert sorted(dispatcher.cancelled_nodes) == \
        [f"{job['id']}_stepone_0", f"{job['id']}_steptwo_0"]


def test_a_node_dispatched_since_the_last_poll_is_still_reached(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''The one a cancel most needs to reach is the one that started a moment
    ago, so the ids are refreshed before they are used rather than read out of
    whatever the last poll happened to see.'''
    job = running(server, server_client, key, token, job_archive, me)

    # No poll at all: nothing has been recorded yet.
    assert not server.config["SC_STORE"].all(
        "SELECT 1 FROM job_nodes WHERE job_id = ? AND scheduler_job_id IS NOT NULL",
        (job["id"],))

    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token, json={})

    assert len(dispatcher.cancelled_nodes) == 2


def test_a_deployment_with_no_cluster_has_no_node_jobs(server):
    '''🔴 An empty answer is the truthful one rather than a gap. Nodes are
    processes inside the run, and the process group is what a cancel signals --
    which is why the column is nullable.'''
    from siliconcompiler.remote.server.running.dispatch import LocalDispatcher

    assert LocalDispatcher().node_jobs("job", [("a", "0")]) == {}


def test_a_run_that_went_away_does_not_leave_its_nodes_running(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 Marking a node `cancelled` in the store does not cancel anything.

    Seen for real on the compose rig: an orchestrator failed and its OpenROAD
    detailed route went on running for another fifty-five minutes, while the
    record said the node was cancelled.
    '''
    job = running(server, server_client, key, token, job_archive, me)

    dispatcher.still_running = {("stepone", "0")}
    dispatcher.alive = False

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("run-interrupted")
    assert dispatcher.cancelled_nodes == [f"{job['id']}_stepone_0"]
    # 🔴 And the orchestrator is NOT scancelled: it is already gone, and
    # scancel answers an error for a job that has finished.
    assert dispatcher.cancelled == []


def test_a_node_that_already_finished_is_not_scancelled(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''⚠️ A warning per finished node is how an operator learns to ignore
    warnings.'''
    job = running(server, server_client, key, token, job_archive, me)

    dispatcher.still_running = set()
    dispatcher.alive = False

    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    assert dispatcher.cancelled_nodes == []


def test_a_cancelled_run_is_cancelled_and_not_lost(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 A cancel kills the run, so the very next poll finds a scheduler with
    no job and a progress file still saying `running`.

    That is exactly the shape of a lost job and is not one. Caught by the
    portal gate: cancelling from the browser reported `scheduler-lost` to the
    waiting CLI, which tells a person their cluster ate the run they just
    stopped.
    '''
    job = running(server, server_client, key, token, job_archive, me)

    cancelled = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel",
                     token, json={}).get_json()
    assert cancelled["state"] == "cancelling"

    # The scheduler has let go of it, and the run never got to write a
    # terminal progress file.
    dispatcher.alive = False

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "cancelled"
    assert read["terminal"] is True
    # Nothing went wrong, so there is no error to report.
    assert read.get("error") is None
    assert all(node["state"] == "cancelled" for node in read["nodes"])


###########################
# Why it failed, in the run's own words
###########################

def test_a_failed_run_publishes_the_reason_the_run_gave(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 `type` and `title` are frozen and identical on every occurrence --
    *The run failed* is true of every failed run there has ever been -- so
    without `detail` the error object says only what `state` already said. The
    runner records the exception that ended the run and it was being stored on
    the transition and published nowhere, which is why a person on the CLI
    could not reach it at all.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "failed",
        "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:00:10.000Z",
        "error": "RuntimeError: git is required to import GitPython",
        "nodes": {"stepone/0": {"state": "cancelled"},
                  "steptwo/0": {"state": "cancelled"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("run-failed")
    assert read["error"]["detail"] == "RuntimeError: git is required to import GitPython"
    # And the shape a client reads it from: a run can fail with no failed node,
    # which is what makes "read the failing node's log" the wrong advice.
    assert read["progress"]["failed_count"] == 0


def test_a_refusal_publishes_which_one_on_the_job(server_client, key, token,
                                                  job_archive, dispatcher):
    '''The detail was computed one line from where the job was recorded and
    thrown away: the submitter saw it in the response and nobody who read the
    job afterwards ever could.'''
    archive, digest, size = job_archive(extra={"../escape": b"owned"})
    job = stage(server_client, key, token, archive, size)

    submit(server_client, key, token, job["id"], digest, size)

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["error"]["type"].endswith("archive-rejected")
    assert read["error"]["reason"] == "traversal"
    assert read["error"]["detail"]


def test_a_reason_that_only_repeats_the_slug_is_not_published(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''`detail` is prose about this occurrence. The slug is already `type`, and
    a client branches on that.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:00:10.000Z",
        "nodes": {"stepone/0": {"state": "failed"},
                  "steptwo/0": {"state": "cancelled"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["error"]["type"].endswith("run-failed")
    assert "detail" not in read["error"]


def test_a_job_the_scheduler_would_not_take_records_what_the_caller_was_told(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 This server's own failure while staging is `failed`,
    `staging-failed`, with the detail -- never `rejected`, and never `queued`
    before the scheduler holds the job.'''
    from siliconcompiler.remote.server.running.dispatch import DispatchError

    def refuse(*args, **kwargs):
        raise DispatchError("slurmctld is not answering")

    dispatcher.submit = refuse

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    response = submit(server_client, key, token, job["id"], digest, size)

    assert response.status_code == 202

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("staging-failed")
    assert "status" not in read["error"]
    assert "slurmctld is not answering" in read["error"]["detail"]

    # And the job's `staging` record says so, for a job that never ran: never
    # the run's own log, which it has none of.
    listed = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/artifacts",
                  token).get_json()["items"]
    assert any(item["kind"] == "staging" for item in listed)
    assert not any(item["kind"] == "logs" for item in listed)


def test_a_failed_node_carries_the_type_that_says_so(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 A node's `error` is published on every node and was null on every
    node this server had ever run, the failed ones included -- so a client could not
    tell *this node is why* from *this node is fine* except by re-deriving it
    from the state it already had.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:00:10.000Z",
        "nodes": {"stepone/0": {"state": "failed", "exit_code": 1},
                  "steptwo/0": {"state": "cancelled"}}})

    nodes = {(n["step"], n["index"]): n for n in call(
        server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()["nodes"]}

    error = nodes[("stepone", "0")]["error"]
    assert error["type"].endswith("run-failed")
    # The job's shape, `detail` included: what a plain failure can say is its
    # exit status, and where the tool said why.
    assert error["detail"] == "the node's task exited with status 1; its log says why"
    # And nothing on the node that never ran: it did not fail, the job ended
    # before it started.
    assert nodes[("steptwo", "0")]["error"] is None


###########################
# A run that stops saying anything
###########################

def test_a_silent_run_is_lost_even_while_the_scheduler_says_running(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 The backstop for a scheduler that is wrong, which is not
    hypothetical: a dynamic node killed without deleting itself leaves Slurm
    reporting its jobs RUNNING for ever on a machine that is gone. Observed for
    thirteen minutes on a container that no longer existed -- and every other
    check here asks the scheduler, so every other check believed it.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-24T10:00:00.000Z",
        "heartbeat": "2026-09-24T10:00:00.000Z",     # long ago
        "nodes": {"stepone/0": {"state": "running"},
                  "steptwo/0": {"state": "pending"}}})

    # The scheduler insists, and is not believed.
    dispatcher.alive = True
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()

    assert read["state"] == "failed"
    assert read["error"]["type"].endswith("run-interrupted")


def test_a_beating_run_is_left_alone(server, server_client, key, token,
                                     job_archive, dispatcher, me):
    '''A node can run for half an hour without a transition, which is why the
    heartbeat is on a timer and not on progress.'''
    from siliconcompiler.remote.server.running import runspec
    from siliconcompiler.remote.server.state.store import now

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-24T10:00:00.000Z",
        "heartbeat": now(),
        "nodes": {"stepone/0": {"state": "running"},
                  "steptwo/0": {"state": "pending"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "running"


def test_no_heartbeat_means_no_opinion(server, server_client, key, token,
                                       job_archive, dispatcher, me):
    '''⚠️ A run started by a runner older than this writes none, and the honest
    answer for it is the one this server always gave -- ask the scheduler.
    Treating a missing field as silence would declare every in-flight job of an
    upgrade dead.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-24T10:00:00.000Z",
        "nodes": {"stepone/0": {"state": "running"},
                  "steptwo/0": {"state": "pending"}}})

    dispatcher.alive = True
    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "running"


###########################
# The job's page for a person
###########################

def test_a_deployment_with_no_web_ui_omits_web_url(server_client, key, token):
    '''🔴 ABSENT and never null. A null would claim there IS a portal and that
    this job has no page on it, which is never true.'''
    created = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0"}).get_json()

    assert "web_url" not in created

    read = call(server_client, key, "GET", f"/v1/jobs/{created['id']}",
                token).get_json()
    assert "web_url" not in read


def test_a_deployment_with_a_portal_publishes_the_page(server, server_client,
                                                       key, token):
    '''Followed, never constructed: the portal's route shape may change without
    a version bump, so a client that builds this itself breaks quietly.'''
    server.config["SC_CONFIG"]._values["web_url_base"] = "https://sc.example/"

    created = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0"}).get_json()

    assert created["web_url"] == f"https://sc.example/portal/jobs/{created['id']}"
    # Both places: the create response is what a CLI has in hand at submit
    # time, and the job object is what anything reading it later sees.
    read = call(server_client, key, "GET", f"/v1/jobs/{created['id']}",
                token).get_json()
    assert read["web_url"] == created["web_url"]


def test_the_page_origin_never_comes_from_a_request_header(server, server_client,
                                                           key, token):
    '''⚠️ The same trusted-proxy trap as a forwarded client address, with a
    worse payoff: the output is a link somebody pastes into a ticket.'''
    server.config["SC_CONFIG"]._values["web_url_base"] = "https://sc.example"

    # 🔴 Only the forwarded headers, and that is not a weaker test -- it is
    # the realistic one. `Host` cannot be moved here at all: DPoP binds the
    # proof to the request URL, so changing it fails authentication long before
    # any link is built. What a proxy forwards is the header that actually
    # reaches an application unchallenged.
    created = call(server_client, key, "POST", "/v1/jobs", token,
                   json={"design": "gcd", "jobname": "job0"},
                   headers={"X-Forwarded-Host": "evil.example",
                            "X-Forwarded-Proto": "https"}).get_json()

    assert created["web_url"].startswith("https://sc.example/")
    assert "evil.example" not in created["web_url"]


###########################
# A job nobody ever uploaded to
###########################

def test_a_job_whose_upload_never_arrived_is_abandoned(server, server_client,
                                                       key, token):
    '''🔴 `abandoned` is the tenth state and nothing wrote it. A job created
    and never uploaded to sat in `created` for ever: holding a
    `pending_uploads` slot, on every listing, and -- because the portal
    refreshes until a job is terminal -- reloading its own page indefinitely
    for a run that was never going to happen.'''
    created = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0"}).get_json()

    # Still within the window: left alone.
    read = call(server_client, key, "GET", f"/v1/jobs/{created['id']}",
                token).get_json()
    assert read["state"] == "created"

    server.config["SC_CONFIG"].limits["abandon_after_seconds"] = 0

    read = call(server_client, key, "GET", f"/v1/jobs/{created['id']}",
                token).get_json()
    assert read["state"] == "abandoned"
    assert read["terminal"] is True
    assert read["finished_at"]


def test_a_live_upload_grant_is_never_abandoned(server, server_client, key,
                                                token):
    '''⚠️ The window is the floor and not the whole answer. A slow link
    uploading a gigabyte and a script that died between create and PUT look
    identical from here, so a job still holding a good grant is left alone
    however old it is -- otherwise setting the window below the grant's own
    lifetime would abandon uploads that were legitimately in flight.'''
    created = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0"}).get_json()
    call(server_client, key, "POST", f"/v1/jobs/{created['id']}/upload-grant",
         token, json=sized(4096))

    server.config["SC_CONFIG"].limits["abandon_after_seconds"] = 0

    read = call(server_client, key, "GET", f"/v1/jobs/{created['id']}",
                token).get_json()
    assert read["state"] == "awaiting_input"


def test_the_sweep_settles_the_jobs_nobody_opens(server, server_client, key,
                                                 token):
    '''🔴 A job stuck in `created` is exactly the job nobody opens, and while
    it sits there it holds a slot against its owner's allowance. The ceiling
    gets reached by jobs that no longer exist in any meaningful sense.'''
    from siliconcompiler.remote.server.outputs import reaper

    created = call(server_client, key, "POST", "/v1/jobs", token, json={
        "design": "gcd", "jobname": "job0"}).get_json()
    server.config["SC_CONFIG"].limits["abandon_after_seconds"] = 0

    taken = reaper.sweep(server.config["SC_STORE"], server.config["SC_STORAGE"],
                         server.config["SC_CONFIG"], server.config["SC_DATADIR"])

    assert taken["abandoned"] == 1
    assert server.config["SC_STORE"].one(
        "SELECT state FROM jobs WHERE id = ?", (created["id"],))["state"] == "abandoned"


###########################
# Polling fast without asking the scheduler fast
###########################

def test_a_fast_poll_does_not_become_a_fast_squeue(server, server_client, key,
                                                   token, job_archive,
                                                   dispatcher, me):
    '''🔴 Reading a job is a local SQLite read and a stat; asking Slurm which
    job each node became is one or more RPCs into slurmctld. Without a floor,
    shortening the poll interval multiplies scheduler load by the same factor
    -- which is the load `--max-connections` exists to throttle.'''
    from siliconcompiler.remote.server.running import runspec

    asked = []
    real = dispatcher.node_jobs

    def counted(job_id, nodes):
        asked.append(job_id)
        return real(job_id, nodes)

    dispatcher.node_jobs = counted

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-24T10:00:00.000Z",
        "heartbeat": now(), "nodes": {"stepone/0": {"state": "running"},
                                      "steptwo/0": {"state": "pending"}}})

    # The store forgets the ids between polls so every poll WOULD ask.
    for _ in range(5):
        server.config["SC_STORE"].execute(
            "UPDATE job_nodes SET scheduler_job_id = NULL WHERE job_id = ?",
            (job["id"],))
        call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    assert len(asked) == 1, f"asked the scheduler {len(asked)} times in five polls"


def test_a_cancel_never_takes_a_stale_answer(server, server_client, key, token,
                                             job_archive, dispatcher, me):
    '''⚠️ The floor is a rate limit on watching, not on acting. A cancel needs
    the ids to reach the work, so it asks whatever the clock says.'''
    from siliconcompiler.remote.server.running import runspec

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    root = server.config["SC_JOBS"].job_root(me, job["id"]) / "gcd" / "job0"
    runspec.write_progress(root.parents[1] / runspec.PROGRESS_FILENAME, {
        "state": "running", "started_at": "2026-09-24T10:00:00.000Z",
        "heartbeat": now(), "nodes": {"stepone/0": {"state": "running"},
                                      "steptwo/0": {"state": "pending"}}})

    call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET scheduler_job_id = NULL WHERE job_id = ?",
        (job["id"],))

    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
         json={"reason": "changed my mind"})

    assert dispatcher.cancelled_nodes, "a cancel reached no node jobs"


###########################
# Submit answers early, and staging checks the upload
###########################

def test_a_replayed_submit_answers_the_original_202(server_client, key, token,
                                                    job_archive, dispatcher):
    '''The original body, `staging` and all, whatever the job has done since:
    a replay returns the original response (surface §6).'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)

    first = submit(server_client, key, token, job["id"], digest, idempotency_key="s1")
    again = submit(server_client, key, token, job["id"], digest, idempotency_key="s1")

    assert (first.status_code, again.status_code) == (202, 202)
    assert again.get_json() == first.get_json()
    assert again.get_json()["state"] == "staging"
    assert len(dispatcher.submitted) == 1


@pytest.mark.parametrize("what", ["create", "submit"])
def test_a_retry_while_the_original_is_handled_is_in_progress(
        server, server_client, key, token, job_archive, dispatcher, what):
    '''Only a final answer binds a key: a retry meanwhile is `409`,
    `in_progress`, with `Retry-After`, and binds nothing.'''
    jobs = server.config["SC_JOBS"]
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    jobs._in_flight.add((me, what, "k-busy"))

    if what == "create":
        response = create(server_client, key, token, idempotency_key="k-busy")
    else:
        archive, digest, size = job_archive()
        job = stage(server_client, key, token, archive, size)
        response = submit(server_client, key, token, job["id"], digest,
                          idempotency_key="k-busy")

    assert response.status_code == 409
    assert slug(response) == "job-state-conflict"
    assert response.get_json()["reason"] == "in_progress"
    assert int(response.headers["Retry-After"]) >= 1


def test_a_key_older_than_a_day_is_forgotten(server, server_client, key, token):
    first = create(server_client, key, token, idempotency_key="old").get_json()
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET created_at = '2020-01-01T00:00:00.000Z' WHERE id = ?",
        (first["id"],))

    again = create(server_client, key, token, idempotency_key="old")

    assert again.status_code == 201
    assert again.get_json()["id"] != first["id"]


@pytest.mark.parametrize("member,named", [
    ("sc-server-progress.json", "sc-server-progress.json"),
    ("sc_configs/sc_slurm_stepone_0.sh", "sc_configs"),
])
def test_a_member_the_first_archive_does_not_carry_is_unrequested(
        server_client, key, token, job_archive, dispatcher, member, named):
    '''🔴 A planted `sc-server-progress.json` is one, and so is the old
    client's `sc_configs/`, where SiliconCompiler's Slurm scheduler writes a
    job's scripts: the server's own files live above the tree an upload
    expands into.'''
    archive, digest, size = job_archive(extra={
        member: b'{"state": "completed", "nodes": {}}'})
    job = stage(server_client, key, token, archive, size)

    read = job_after(server_client, key, token,
                     submit(server_client, key, token, job["id"], digest, size))

    assert read["state"] == "rejected"
    assert read["error"]["reason"] == "unrequested_member"
    assert named in read["error"]["detail"]
    assert not dispatcher.submitted


def test_the_pending_uploads_refusal_names_the_jobs_holding_the_slots(
        server, server_client, key, token):
    server.config["SC_CONFIG"].limits["pending_uploads"] = 1
    held = create(server_client, key, token).get_json()

    refused = create(server_client, key, token, jobname="job1")

    assert refused.status_code == 429
    assert refused.get_json()["limit"] == "pending_uploads"
    assert refused.get_json()["job_ids"] == [held["id"]]


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


def test_an_asic_project_with_no_pdk_is_unresolved(server_client, key, token,
                                                   job_archive, dispatcher, gcd_design):
    '''The PDK fails closed where the class has a PDK setting; a class with
    none resolves to 'none' (every nopflow job here is one).'''
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
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)

    read = job_after(server_client, key, token,
                     submit(server_client, key, token, job["id"], digest, size))

    assert read["state"] == "rejected"
    assert read["error"]["type"].endswith("resource-unresolved")
    assert read["error"]["resource_kind"] == "pdk"


###########################
# The edges, the nodes, and why it is where it is
###########################

def test_a_cancel_of_a_job_the_scheduler_already_ended_leaves_it(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''🔴 Conditional on the state it moves from: the `202` carries the job as
    the scheduler left it.'''
    job = running(server, server_client, key, token, job_archive, me)
    jobs = server.config["SC_JOBS"]
    original = jobs._transition_if

    def ended_first(job_id, from_state, to_state, **kwargs):
        # The scheduler side got there between the read and the write.
        jobs._transition(job_id, from_state, "completed")
        return original(job_id, from_state, to_state, **kwargs)

    jobs._transition_if = ended_first
    response = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                    json={})

    assert response.status_code == 202
    assert response.get_json()["state"] == "completed"
    assert not dispatcher.cancelled


def test_a_cancelling_job_ends_cancelled_even_if_its_run_finished(
        server, server_client, key, token, job_archive, dispatcher, me):
    from siliconcompiler.remote.server.running import runspec

    job = running(server, server_client, key, token, job_archive, me)
    cancelled = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                     json={"reason": "wrong corner"}).get_json()
    assert cancelled["state"] == "cancelling"
    # A cancel's reason is on its entry of `transitions`, never the job's
    # `state_reason`, which carries only a live staging phase (D278).
    assert "state_reason" not in cancelled
    assert (cancelled["transitions"][-1]["state"],
            cancelled["transitions"][-1]["reason"]) == ("cancelling", "wrong corner")

    root = server.config["SC_JOBS"].job_root(me, job["id"])
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "completed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:01:00.000Z",
        "nodes": {"stepone/0": {"state": "completed", "exit_code": 0},
                  "steptwo/0": {"state": "running"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "cancelled"
    assert [entry["state"] for entry in read["transitions"]][-2:] == \
        ["cancelling", "cancelled"]
    assert read["transitions"][-2]["reason"] == "wrong corner"
    nodes = {node["step"]: node for node in read["nodes"]}
    # A terminal job has only terminal nodes, and one a cancel stopped has no
    # exit code and says why.
    assert all(node["terminal"] for node in read["nodes"])
    assert nodes["steptwo"]["state"] == "cancelled"
    assert nodes["steptwo"]["exit_code"] is None
    assert nodes["steptwo"]["state_reason"] == "wrong corner"


# 300 characters, and two spaces a `detail`'s bound would fold into one.
LONG_REASON = ("stopped by hand:  " + "the corner was wrong and the run is repeated " * 7)[:300]


def test_a_300_character_reason_is_served_whole(
        server, server_client, key, token, job_archive, dispatcher, me, monkeypatch):
    '''🔴 What is accepted is what everyone reads (surface D288): whole, on
    the job's `cancelling` and `cancelled` transitions and on each node the
    cancel stopped -- even where a deployment bounds its own text shorter.'''
    from siliconcompiler.remote.server import errors
    from siliconcompiler.remote.server.running import runspec

    assert len(LONG_REASON) == 300
    monkeypatch.setattr(errors, "DETAIL_MAX", 100)
    job = running(server, server_client, key, token, job_archive, me)
    cancelled = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                     json={"reason": LONG_REASON}).get_json()
    assert cancelled["transitions"][-1] == {**cancelled["transitions"][-1],
                                            "state": "cancelling", "reason": LONG_REASON}

    root = server.config["SC_JOBS"].job_root(me, job["id"])
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "completed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:01:00.000Z", "error": "the run's own words",
        "nodes": {"stepone/0": {"state": "completed", "exit_code": 0},
                  "steptwo/0": {"state": "running"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "cancelled"
    assert [(entry["state"], entry.get("reason")) for entry in read["transitions"]][-2:] == \
        [("cancelling", LONG_REASON), ("cancelled", LONG_REASON)]
    nodes = {node["step"]: node for node in read["nodes"]}
    assert nodes["steptwo"]["state_reason"] == LONG_REASON
    # 🔴 Never the job's own member: that carries only a live staging phase.
    assert "state_reason" not in read


def test_a_cancel_that_lands_while_staging_carries_its_reason_to_cancelled(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''The staging thread writes `cancelled` when it stops, with the cancel's
    reason -- not a word of its own.'''
    job = running(server, server_client, key, token, job_archive, me)
    call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
         json={"reason": LONG_REASON})
    jobs = server.config["SC_JOBS"]

    jobs._settle_cancelled(jobs._row(job["id"]))

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert (read["transitions"][-1]["state"], read["transitions"][-1]["reason"]) == \
        ("cancelled", LONG_REASON)
    assert all(node["state_reason"] == LONG_REASON for node in read["nodes"]
               if node["state"] == "cancelled")


def test_the_servers_own_reasons_keep_their_bound(
        server, server_client, key, token, monkeypatch):
    '''Only a cancel's reason is served whole: every other is this server's,
    bounded like a `detail`.'''
    from siliconcompiler.remote.server import errors

    monkeypatch.setattr(errors, "DETAIL_MAX", 100)
    job = create(server_client, key, token).get_json()
    jobs = server.config["SC_JOBS"]
    with server.config["SC_STORE"].transaction():
        jobs._transition(job["id"], "created", "awaiting_input", reason="y " * 200)

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    served = read["transitions"][-1]["reason"]
    assert served.endswith("...") and len(served) < 110


@pytest.mark.parametrize("reported,published", [(0, 0), (1, 1), (-9, 137), (-15, 143),
                                                (137, 137), (None, None)])
def test_an_exit_code_is_0_to_255_and_a_signal_is_128_plus_n(reported, published):
    from siliconcompiler.remote.server.running import runspec

    assert runspec.exit_code(reported) == published


def test_a_time_limit_is_run_failed_naming_it(server, server_client, key, token,
                                              job_archive, dispatcher, me):
    from siliconcompiler.remote.server.running import runspec

    job = running(server, server_client, key, token, job_archive, me)
    root = server.config["SC_JOBS"].job_root(me, job["id"])
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:01:00.000Z",
        "nodes": {"stepone/0": {"state": "failed", "exit_code": -9, "limit": "time"},
                  "steptwo/0": {"state": "pending"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["error"]["type"].endswith("/run-failed")
    assert "stepone/0 exceeded its time limit" in read["error"]["detail"]
    nodes = {node["step"]: node for node in read["nodes"]}
    assert nodes["stepone"]["exit_code"] == 137
    assert nodes["stepone"]["error"]["type"].startswith("https://")
    assert nodes["stepone"]["error"]["detail"]
    assert nodes["steptwo"]["state"] == "cancelled"


def test_an_image_that_would_not_pull_is_run_interrupted_naming_it(
        server, server_client, key, token, job_archive, dispatcher, me):
    from siliconcompiler.remote.server.running import runspec

    job = running(server, server_client, key, token, job_archive, me)
    root = server.config["SC_JOBS"].job_root(me, job["id"])
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:01:00.000Z",
        "nodes": {"stepone/0": {"state": "failed", "exit_code": 125, "interrupted": {
            "image": "ghcr.io/x/sc@sha256:aa", "error": "pull access denied"}},
            "steptwo/0": {"state": "pending"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["error"]["type"].endswith("/run-interrupted")
    assert "its image ghcr.io/x/sc@sha256:aa could not be pulled" in read["error"]["detail"]
    nodes = {node["step"]: node for node in read["nodes"]}
    # The node's own error says the same of it, as the job's shape.
    assert nodes["stepone"]["error"]["type"].endswith("/run-interrupted")
    assert nodes["stepone"]["error"]["detail"] == \
        "the node could not start: its image ghcr.io/x/sc@sha256:aa could not be pulled"
    assert nodes["steptwo"]["error"] is None


def test_a_memory_limit_is_run_failed_naming_it(server, server_client, key, token,
                                                job_archive, dispatcher, me):
    from siliconcompiler.remote.server.running import runspec

    job = running(server, server_client, key, token, job_archive, me)
    root = server.config["SC_JOBS"].job_root(me, job["id"])
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:01:00.000Z",
        "nodes": {"stepone/0": {"state": "failed", "exit_code": 137, "limit": "memory"},
                  "steptwo/0": {"state": "pending"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["error"]["type"].endswith("/run-failed")
    assert "stepone/0 exceeded its memory limit" in read["error"]["detail"]
    node = {node["step"]: node for node in read["nodes"]}["stepone"]
    assert node["error"]["type"].endswith("/run-failed")
    assert node["error"]["detail"] == "the node exceeded its memory limit"


def test_a_time_limit_is_run_failed_and_the_node_names_it(
        server, server_client, key, token, job_archive, dispatcher, me):
    '''A `run-failed` names its time or memory limit in `detail`, on the job and
    on the node that ran into it (surface §17, *A node's `error`*).'''
    from siliconcompiler.remote.server.running import runspec

    job = running(server, server_client, key, token, job_archive, me)
    root = server.config["SC_JOBS"].job_root(me, job["id"])
    runspec.write_progress(root / runspec.PROGRESS_FILENAME, {
        "state": "failed", "started_at": "2026-09-23T10:00:00.000Z",
        "finished_at": "2026-09-23T10:01:00.000Z",
        "nodes": {"stepone/0": {"state": "failed", "exit_code": None, "limit": "time"},
                  "steptwo/0": {"state": "pending"}}})

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["error"]["type"].endswith("/run-failed")
    assert "stepone/0 exceeded its time limit" in read["error"]["detail"]
    node = {node["step"]: node for node in read["nodes"]}["stepone"]
    assert node["error"] == {
        "type": "https://siliconcompiler.com/server-errors/run-failed",
        "title": node["error"]["title"],
        "detail": "the node exceeded its time limit"}


def test_repeated_filters_or_within_a_key_and_terminal_filters(
        server, server_client, key, token):
    '''`?archived=true&archived=false` is both views; `?terminal=` is the
    published flag.'''
    kept = create(server_client, key, token).get_json()
    gone = create(server_client, key, token, jobname="job1").get_json()
    call(server_client, key, "POST", f"/v1/jobs/{gone['id']}/cancel", token, json={})
    call(server_client, key, "POST", f"/v1/jobs/{gone['id']}/archive", token, json={})
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET archived_at = ?, archived_by = user_id WHERE id = ?",
        (now(), gone["id"]))

    def ids(query):
        return {item["id"] for item in call(server_client, key, "GET", f"/v1/jobs?{query}",
                                            token).get_json()["items"]}

    assert ids("") == {kept["id"]}
    assert ids("archived=true&archived=false") == {kept["id"], gone["id"]}
    assert ids("archived=true&archived=false&terminal=true") == {gone["id"]}
    assert ids("terminal=false") == {kept["id"]}
    assert ids("jobname=job0&jobname=job1&archived=true&archived=false") == \
        {kept["id"], gone["id"]}


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


def test_a_job_still_going_says_when_to_ask_again(server_client, key, token):
    job = create(server_client, key, token).get_json()

    response = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token)

    assert int(response.headers["Retry-After"]) >= 1
