import hashlib
import io
import json
import os
import tarfile
import time

import pytest

from conftest import call, outcome, slug
from test_owners import DATASHEET, _nop_asic, collected_path, first, private, resource
from test_server_jobs import FakeDispatcher, create, put, stage, submit


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler import PDK                                        # noqa: E402
from siliconcompiler.remote.server.staging.sources import Permanent            # noqa: E402


# What the server cannot supply, it asks for (D114); create looks up and never
# fetches, and the fetch runs after submit while `staging` (D130). A source that
# fails for good sends the job back -- the one backwards edge -- asking for that
# source and nothing else.

LAMBDA = "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/"


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def remote_project(gcd_design, tmp_path):
    '''A run on an allowlisted remote PDK this server does not hold yet.'''
    return _nop_asic(gcd_design, tmp_path,
                     resource(PDK, "lambda", LAMBDA, create=False))


def fake_fetch(server, fail=None):
    '''Fetching writes the PDK's file into the held copy -- or raises.'''
    store = server.config["SC_JOBS"]._sources

    def resolve(source, ref, into, timeout):
        if fail:
            raise fail
        (into / "datasheet.pdf").write_text("from the release\n")

    store._resolve = resolve
    return store


def wait_for(predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def read(server_client, key, token, job_id):
    return call(server_client, key, "GET", f"/v1/jobs/{job_id}", token).get_json()


###########################
# Create: a lookup, never a fetch
###########################

def test_create_asks_only_for_what_it_cannot_supply(server_client, key, token):
    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "lambda", "dataroot", "lambda"],
         "source": LAMBDA, "ref": "v0.2.22", "private": False},
        {"keypath": ["library", "acme_ip", "dataroot", "acme_ip"],
         "source": "git+ssh://git@github.com/acme/ip.git", "ref": "v1.2",
         "private": False},
    ]).get_json()

    # Allowlisted and not held: assumed fetchable, not listed. Behind a key
    # this server has not got: asked for.
    assert job["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "acme_ip", "dataroot", "acme_ip"]}]


def test_nothing_to_send_means_no_upload_sources(server_client, key, token):
    '''🔴 Absent means *nothing to send*, whichever moment it is -- create
    answers with the job object, where the member is never `[]`.'''
    assert "upload_sources" not in create(server_client, key, token).get_json()
    assert "upload_sources" not in create(server_client, key, token, jobname="job1",
                                          sources=[]).get_json()


def test_a_private_source_none_of_the_three_can_supply_is_refused_at_create(
        server_client, key, token):
    '''🔴 Before a byte moves (surface D285, D299): not the operator's, not
    held, not on the allowlist. A source carries no kind and this server has
    no catalogue, so the refusal names the resource alone -- names are unique
    across kinds. Never asked for: a private source is never uploaded.'''
    response = create(server_client, key, token, sources=[
        {"keypath": ["library", "secret", "dataroot", "secretroot"], "private": True,
         "source": "git+ssh://git.internal.example.com/secret.git", "ref": "v1"}])

    assert response.status_code == 422
    body = response.get_json()
    assert slug(response) == "resource-unavailable"
    assert body["resource"] == "secret"
    assert "resource_kind" not in body
    assert "library,secret,dataroot,secretroot" in body["detail"]
    assert "cannot fetch it either" in body["detail"]
    listed = call(server_client, key, "GET", "/v1/jobs", token).get_json()
    assert listed["items"] == []


def test_a_private_source_without_its_source_is_decided_while_staging(
        server_client, key, token):
    '''The `sc-server` client sends a private entry no source -- the
    manifest carries it -- so create cannot tell a held or fetchable one from
    neither: it is left to staging, and never asked for.'''
    response = create(server_client, key, token, sources=[
        {"keypath": ["library", "secret", "dataroot", "secretroot"], "private": True}])

    assert response.status_code == 201
    assert not response.get_json().get("upload_sources")


def test_credentials_in_a_source_are_never_stored(server, server_client, key, token):
    '''🔴 The client strips them; the server strips them again.'''
    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "ip", "dataroot", "ip"],
         "source": "https://user:ghp_secret@gitlab.com/acme/ip/archive/",
         "ref": "v1", "private": False}]).get_json()

    stored = server.config["SC_STORE"].one(
        "SELECT descriptor FROM jobs WHERE id = ?", (job["id"],))["descriptor"]
    assert "ghp_secret" not in stored
    assert "gitlab.com/acme/ip" in stored


def test_a_token_in_a_sources_query_is_masked_here_too(server, server_client, key, token):
    '''A client that sent a query's token anyway: masked as the client masks
    it, before anything is stored or logged.'''
    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "ip", "dataroot", "ip"],
         "source": "https://gitlab.com/acme/ip/archive/v1.tar.gz?private_token=glpat-x",
         "ref": "v1", "private": False}]).get_json()

    stored = server.config["SC_STORE"].one(
        "SELECT descriptor FROM jobs WHERE id = ?", (job["id"],))["descriptor"]
    assert "glpat-x" not in stored and "private_token=***" in stored


def test_a_masked_source_is_asked_for_never_fetched(server_client, key, token):
    '''🔴 On the allowlist, and still never fetched: a masked query value
    says what the source is and not enough to fetch it from, so the client,
    which has the real one, is asked.'''
    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "lambda", "dataroot", "lambda"],
         "source": f"{LAMBDA}?lfs=***", "ref": "v0.2.22", "private": False}]).get_json()

    assert job["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "lambda", "dataroot", "lambda"]}]


###########################
# After submit: fetched while staging
###########################

def test_an_allowlisted_source_is_fetched_after_submit_then_dispatched(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    fake_fetch(server)
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, size)

    # No request waits on the fetch.
    assert response.status_code == 202
    # 🔴 Staging, not queued: `queued` only moves forward, and this job can
    # still be sent back or refused.
    assert response.get_json()["state"] == "staging"
    assert wait_for(lambda: dispatcher.submitted)

    # The run reads the server's held copy, and its manifest says so.
    from conftest import run_manifest

    ran = run_manifest(dispatcher.submitted[0][2])
    held = server.config["SC_JOBS"]._sources.held(LAMBDA, "v1")
    pointed = json.dumps(ran.getdict()["library"]["lambda"]["dataroot"])
    assert held and held in pointed
    assert LAMBDA not in pointed


def test_a_source_that_fails_for_good_sends_the_job_back_saying_why(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''🔴 The one backwards edge: `staging -> awaiting_input`, naming what
    failed and nothing else -- and the transition says why.'''
    fake_fetch(server, fail=Permanent("the source answered 404"))
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    back = read(server_client, key, token, job["id"])
    assert back["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "lambda", "dataroot", "lambda"]}]
    assert back["terminal"] is False
    assert not dispatcher.submitted

    reason = server.config["SC_STORE"].one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? "
        "AND from_state = 'staging' AND to_state = 'awaiting_input'",
        (job["id"],))["reason"]
    assert "the dataroot library,lambda,dataroot,lambda: the source answered 404" in reason

    # 🔴 `transitions` lists every state entered, the send-back included, and
    # the entry says why (surface §17; D278).
    assert [entry["state"] for entry in back["transitions"]] == \
        ["created", "awaiting_input", "staging", "awaiting_input"]
    assert "the source answered 404" in back["transitions"][-1]["reason"]


def test_two_owners_of_one_dataroot_name_are_told_apart(server_client, key, token):
    '''🔴 A dataroot's name is unique only within its owner, and many objects
    use SiliconCompiler's default, `root`: `upload_sources` names both
    (surface §13; D282).'''
    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "acme_ip", "dataroot", "root"],
         "source": "git+ssh://git@github.com/acme/ip.git", "ref": "v1", "private": False},
        {"keypath": ["library", "beta_ip", "dataroot", "root"],
         "source": "git+ssh://git@github.com/beta/ip.git", "ref": "v1", "private": False},
    ]).get_json()

    assert job["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "acme_ip", "dataroot", "root"]},
        {"kind": "dataroot", "keypath": ["library", "beta_ip", "dataroot", "root"]}]


def test_a_source_names_no_kind(server_client, key, token):
    '''The server finds a name's kind (entitlements D75): a `kind` is an
    unknown member, refused under the strict rule.'''
    response = create(server_client, key, token, sources=[
        {"kind": "pdk", "keypath": ["library", "lambda", "dataroot", "lambda"], "private": False}])

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_a_job_sent_back_counts_as_waiting_again(server, server_client, key, token,
                                                 job_archive, remote_project,
                                                 dispatcher):
    '''It frees its `concurrent_jobs` slot and holds a `pending_uploads` one --
    both count by state -- and the abandonment clock runs from the transition.'''
    fake_fetch(server, fail=Permanent("the source answered 404"))
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")

    store = server.config["SC_STORE"]
    user = store.one("SELECT user_id FROM jobs WHERE id = ?", (job["id"],))["user_id"]
    assert store.one("SELECT count(*) AS n FROM jobs WHERE user_id = ? AND state IN "
                     "('staging','queued','running','cancelling')", (user,))["n"] == 0
    row = store.one("SELECT created_at, state_changed_at FROM jobs WHERE id = ?",
                    (job["id"],))
    assert row["state_changed_at"] >= row["created_at"]


def transitions(server, job_id):
    return [(row["from_state"], row["to_state"]) for row in server.config["SC_STORE"].all(
        "SELECT from_state, to_state FROM job_state_transitions WHERE job_id = ? "
        "ORDER BY id", (job_id,))]


def test_a_job_stages_then_queues_and_queued_only_moves_forward(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''🔴 Surface D130: the fetch is where a job can still be sent back or
    refused, so it happens BEFORE `queued`.'''
    fake_fetch(server)
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    assert wait_for(lambda: dispatcher.submitted)

    assert transitions(server, job["id"])[-2:] == [("awaiting_input", "staging"),
                                                   ("staging", "queued")]


def test_every_job_stages_even_with_nothing_to_fetch(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 Submit only matches the digest; the archive is opened while
    staging, so every admitted job passes through it.'''
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    assert transitions(server, job["id"])[-2:] == [("awaiting_input", "staging"),
                                                   ("staging", "queued")]


@pytest.mark.threaded_staging
def test_a_staging_job_counts_against_concurrent_jobs(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''🔴 Fetches are work: a state no limit counted would let one account
    stage any number of jobs at once.'''
    import threading

    gate = threading.Event()
    store = server.config["SC_JOBS"]._sources

    def slow(source, ref, into, timeout):
        gate.wait(5)
        (into / "datasheet.pdf").write_text("x")

    store._resolve = slow
    server.config["SC_CONFIG"].limits["concurrent_jobs"] = 1
    try:
        archive, digest, size = job_archive(remote_project)
        first_job = stage(server_client, key, token, archive, size)
        submit(server_client, key, token, first_job["id"], digest, size)
        assert read(server_client, key, token, first_job["id"])["state"] == "staging"

        # Refused at create, before any upload.
        refused = create(server_client, key, token, jobname="job1")
        assert refused.status_code == 429
        assert refused.get_json()["limit"] == "concurrent_jobs"
        assert int(refused.headers["Retry-After"]) >= 1
    finally:
        gate.set()


def test_a_fetched_copy_missing_a_required_file_is_refused_from_staging(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher):
    '''`rejected` means refused before it ran -- at submit, or while staging.'''
    from test_required import carried, reading

    store = server.config["SC_JOBS"]._sources
    store._resolve = lambda source, ref, into, timeout: (into / "other.pdf").write_text("x")
    project = carried(reading(gcd_design, tmp_path, ("library", "lambda", *DATASHEET),
                              pdk=resource(PDK, "lambda", LAMBDA, create=False)))
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"] == "rejected")
    assert transitions(server, job["id"])[-1] == ("staging", "rejected")
    assert not dispatcher.submitted


###########################
# The follow-up archive
###########################

def follow_up(members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, body in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    data = buffer.getvalue()
    return data, "sha256:" + hashlib.sha256(data).hexdigest(), len(data)


def sent_back(server, server_client, key, token, job_archive, remote_project):
    fake_fetch(server, fail=Permanent("the source answered 404"))
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    return job


def send(server_client, key, token, job_id, members):
    data, digest, size = follow_up(members)
    grant = call(server_client, key, "POST", f"/v1/jobs/{job_id}/upload-grant",
                 token, json={"size_bytes": size, "digest": digest}).get_json()
    put(server_client, grant, data)
    return outcome(server_client, key, token,
                   submit(server_client, key, token, job_id, digest, size))


def test_a_follow_up_may_hold_only_what_was_asked_for(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''🔴 Anything else is `unrequested_member`: a second upload must not
    replace what the first carried after the server checked it.'''
    job = sent_back(server, server_client, key, token, job_archive, remote_project)

    response = send(server_client, key, token, job["id"], {
        "gcd.pkg.json": b"{}",           # the manifest, replaced
    })

    assert response.status_code == 422
    assert slug(response) == "archive-rejected"
    assert response.get_json()["reason"] == "unrequested_member"


def test_a_follow_up_carrying_a_wheel_nobody_asked_for_is_unrequested(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''A wheel arrives in the first archive, or answers a `python` entry --
    never beside a dataroot the server asked for.'''
    from siliconcompiler.remote import environment

    job = sent_back(server, server_client, key, token, job_archive, remote_project)

    response = send(server_client, key, token, job["id"], {
        f"{environment.wheels_path()}/scfake-1.0-py3-none-any.whl": b"PK"})

    assert response.get_json()["reason"] == "unrequested_member"


def test_the_asked_for_sources_arrive_and_the_job_runs(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    job = sent_back(server, server_client, key, token, job_archive, remote_project)
    hashed = collected_path(first(remote_project, ("library", "lambda", *DATASHEET)))

    response = send(server_client, key, token, job["id"], {
        f"sc_collected_files/{hashed}": b"sent by the client\n"})

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)


def test_the_staging_record_gains_a_section_each_pass_and_is_scrubbed(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''The job's `staging` artifact is the server's record for its submitter
    (surface D295): what each pass did, a section per pass, one artifact for
    the job, and scrubbed like `detail`, since everyone who reads the job reads
    it -- a credential in a fetch's error included.'''
    import gzip

    fake_fetch(server, fail=Permanent("the source answered 404 for "
                                      "https://ci:hunter2@example.test/pdk.tar.gz"))
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    hashed = collected_path(first(remote_project, ("library", "lambda", *DATASHEET)))
    assert send(server_client, key, token, job["id"], {
        f"sc_collected_files/{hashed}": b"sent by the client\n"}).status_code == 202
    store = server.config["SC_STORE"]

    def staging():
        rows = store.all("SELECT storage_key FROM artifacts WHERE job_id = ? "
                         "AND kind = 'staging'", (job["id"],))
        assert len(rows) == 1
        with gzip.open(server.config["SC_STORAGE"].artifact_path(rows[0]["storage_key"]),
                       "rt") as f:
            return f.read()

    # Indexed as each pass ends, so it is replaced, never added to.
    assert wait_for(lambda: "handed the job to the scheduler" in staging())
    text = staging()

    assert text.count("==> staging, pass ") == 2
    first_pass, second_pass = text.split("==> staging, pass 2")
    assert "sent back for" in first_pass
    assert "handed the job to the scheduler" in second_pass
    assert "hunter2" not in text


def test_staging_past_its_limit_ends_the_job_staging_timed_out(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''surface D294: staging is bounded as a whole by the caller's
    `max_staging_seconds`, whatever phase the time goes on -- a fetch here --
    and past it the job ends `failed`, `staging-timed-out`, naming the limit:
    the job's own, not this server's failure.'''
    server.config["SC_CONFIG"].limits["max_staging_seconds"] = 1
    store = fake_fetch(server)

    def slow(source, ref, into, timeout):
        time.sleep(3)

    store._resolve = slow
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"] == "failed")
    error = read(server_client, key, token, job["id"])["error"]
    assert error["type"].endswith("/staging-timed-out")
    assert error["limit"] == "max_staging_seconds"
    assert "while fetching sources" in error["detail"]
    assert not dispatcher.submitted


def test_a_job_sent_back_gets_a_fresh_staging_limit(
        server, server_client, key, token, job_archive, remote_project, dispatcher,
        monkeypatch):
    '''The limit counts one pass: a job sent back and submitted again stages
    with all of it again, so two passes that each take most of it both
    finish.'''
    from siliconcompiler.remote.server.jobs.pythonenv import PythonEnvMixin

    server.config["SC_CONFIG"].limits["max_staging_seconds"] = 2
    store = fake_fetch(server)

    def slow_then_gone(source, ref, into, timeout):
        time.sleep(1.2)
        raise Permanent("the source answered 404")

    store._resolve = slow_then_gone
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")

    def slow_install(self, job, summary):
        time.sleep(1.2)
        return []

    monkeypatch.setattr(PythonEnvMixin, "_install_on_host", slow_install)
    hashed = collected_path(first(remote_project, ("library", "lambda", *DATASHEET)))
    assert send(server_client, key, token, job["id"], {
        f"sc_collected_files/{hashed}": b"sent by the client\n"}).status_code == 202

    assert wait_for(lambda: dispatcher.submitted)
    assert read(server_client, key, token, job["id"])["state"] != "failed"


def test_each_upload_is_kept_as_its_own_input(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''The first archive and the follow-up, separately and in order, each
    under the digest its submit checked -- so what was sent can be inspected.'''
    job = sent_back(server, server_client, key, token, job_archive, remote_project)
    hashed = collected_path(first(remote_project, ("library", "lambda", *DATASHEET)))
    data, digest, size = follow_up({f"sc_collected_files/{hashed}": b"sent by the client\n"})

    grant = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                 token, json={"size_bytes": size, "digest": digest}).get_json()
    put(server_client, grant, data)
    submit(server_client, key, token, job["id"], digest, size)

    uploads = server.config["SC_STORE"].all(
        "SELECT digest, size_bytes FROM artifacts WHERE job_id = ? "
        "AND kind = 'input' AND step IS NULL ORDER BY created_at, id", (job["id"],))
    assert len(uploads) == 2
    assert (uploads[1]["digest"], uploads[1]["size_bytes"]) == (digest, size)


###########################
# Nothing to wait for
###########################

@pytest.mark.threaded_staging
def test_cancelling_a_job_still_fetching_stops_the_fetch(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''Nothing was dispatched, so there is nothing to wind down.'''
    import threading

    gate = threading.Event()
    store = server.config["SC_JOBS"]._sources

    def slow(source, ref, into, timeout):
        gate.wait(5)
        (into / "datasheet.pdf").write_text("x")

    store._resolve = slow
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    cancelled = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                     json={}).get_json()
    gate.set()

    # 🔴 `cancelling`, with the cancel's reason: work was in flight. The
    # staging thread stops the fetch and writes `cancelled` -- the API's, as a
    # staging job has no scheduler id.
    assert cancelled["state"] == "cancelling"
    # No reason was given, so its entry carries none.
    assert cancelled["transitions"][-1]["state"] == "cancelling"
    assert "reason" not in cancelled["transitions"][-1]
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "cancelled")
    assert not dispatcher.submitted
    assert transitions(server, job["id"])[-2:] == [("staging", "cancelling"),
                                                   ("cancelling", "cancelled")]


def test_a_private_source_mapped_here_is_supplied_at_create(server, server_client,
                                                            key, token, tmp_path):
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"secret": {"secret": str(tmp_path)}}}

    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "secret", "dataroot", "secret"], "private": True}])

    assert job.status_code == 201
    assert "upload_sources" not in job.get_json()


def test_private_and_local_resources_are_told_apart_at_create(server_client, key,
                                                              token, tmp_path):
    '''`private` is REQUIRED, and a descriptor source that is not a dict is a
    malformed request, not a missing file.'''
    response = create(server_client, key, token, sources=["not an object"])

    assert response.status_code == 400
    assert slug(response) == "invalid-request"
    _ = private  # the shared helper, for completeness of the imports


def test_a_held_copy_records_its_commit_and_holds_no_moving_ref(tmp_path, monkeypatch):
    '''🔴 The commit is recorded before `.git` goes, and a branch is held for
    one job's staging, never across jobs.'''
    from siliconcompiler.remote.server.staging import sources

    store = sources.SourceStore(tmp_path, [])
    monkeypatch.setattr(store, "allowlisted", lambda source, ref: True)

    def resolve(moving):
        def into(source, ref, data, timeout):
            (data / "f").write_text(ref)
            return "a" * 40, moving
        return into

    store._resolve = resolve(True)
    fetched = store.fetch("https://example.com/ip.git", "main", 10)
    assert store.held("https://example.com/ip.git", "main") == fetched
    assert store.commit("https://example.com/ip.git", "main") == "a" * 40

    monkeypatch.setattr(sources, "MOVING_HOLD_SECONDS", -1)
    assert store.held("https://example.com/ip.git", "main") is None
    # Fetched again, beside -- never over -- the copy a job may be reading.
    again = store.fetch("https://example.com/ip.git", "main", 10)
    assert again != fetched and os.path.isdir(fetched)

    store._resolve = resolve(False)
    pinned = store.fetch("https://example.com/ip.git", "v1.0", 10)
    assert store.held("https://example.com/ip.git", "v1.0") == pinned


###########################
# A dataroot is named by its keypath (surface D298)
###########################

TASK_RUN = ["tool", "acme_sim", "task", "run", "dataroot", "scripts"]
TASK_CHECK = ["tool", "acme_sim", "task", "check", "dataroot", "scripts"]


@pytest.mark.parametrize("entry", [
    {"keypath": ["library", "acme"]},
    {"keypath": ["tool", "acme_sim", "dataroot", "scripts"]},      # a tool's, no task
    {"keypath": ["option", "x", "dataroot", "y"]},
    {"keypath": "library,acme,dataroot,acme"},
    {"keypath": ["library", "acme", "dataroot", ""]},
    # The old spelling, alone or beside the new: refused as any unknown member.
    {"name": "acme", "dataroot": "acme"},
    {"keypath": ["library", "acme", "dataroot", "acme"], "dataroot": "acme"},
])
def test_a_source_named_otherwise_than_by_its_keypath_is_refused(server_client, key,
                                                                 token, entry):
    response = create(server_client, key, token,
                      sources=[dict(entry, source=LAMBDA, ref="v1")])

    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_a_private_task_root_this_server_lacks_is_refused_with_its_keypath(
        server_client, key, token):
    '''The owner's name as `resource`, and which of its dataroots as
    `keypath`: a tool's `root` would otherwise read as *the tool is
    unavailable*.'''
    response = create(server_client, key, token, sources=[
        {"keypath": TASK_RUN, "private": True,
         "source": "git+ssh://git.internal.example.com/acme.git", "ref": "v1"}])

    assert response.status_code == 422
    body = response.get_json()
    assert slug(response) == "resource-unavailable"
    assert (body["resource"], body["keypath"]) == ("acme_sim", TASK_RUN)
    assert "resource_kind" not in body
    assert "the private dataroot tool,acme_sim,task,run,dataroot,scripts is not held by " \
        "this server" in body["detail"]


def test_one_tool_entry_supplies_every_task_and_a_task_entry_overrides(
        server, server_client, key, token, tmp_path):
    '''`private_dataroots`: a tool's private root is normally the same for all
    its tasks, so `tool` covers them, and `task` names one that differs.'''
    every, check = tmp_path / "every", tmp_path / "check"
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"acme_sim": {"scripts": str(tmp_path / "library")}},
        "tool": {"acme_sim": {"scripts": str(every)}},
        "task": {"acme_sim": {"check": {"scripts": str(check)}}}}
    supply = server.config["SC_JOBS"]._supply

    assert supply.private_root(TASK_RUN) == str(every)
    assert supply.private_root(TASK_CHECK) == str(check)
    assert supply.private_root(["tool", "other", "task", "run", "dataroot", "scripts"]) is None
    # The library of the tool's name is its own entry, never the tool's.
    assert supply.private_root(["library", "acme_sim", "dataroot", "scripts"]) == \
        str(tmp_path / "library")
    assert create(server_client, key, token, sources=[
        {"keypath": TASK_RUN, "private": True},
        {"keypath": TASK_CHECK, "private": True}]).status_code == 201


def test_two_tasks_of_one_tool_are_asked_for_separately(server_client, key, token):
    job = create(server_client, key, token, sources=[
        {"keypath": TASK_RUN, "source": "https://example.com/acme/run/", "ref": "v1"},
        {"keypath": TASK_CHECK, "source": "https://example.com/acme/check/", "ref": "v1"},
        {"keypath": ["library", "acme_sim", "dataroot", "scripts"],
         "source": "https://example.com/acme/lib/", "ref": "v1"}]).get_json()

    assert job["upload_sources"] == [
        {"kind": "dataroot", "keypath": TASK_RUN},
        {"kind": "dataroot", "keypath": TASK_CHECK},
        {"kind": "dataroot", "keypath": ["library", "acme_sim", "dataroot", "scripts"]}]


def test_one_dataroot_named_twice_is_refused(server_client, key, token):
    response = create(server_client, key, token, sources=[
        {"keypath": TASK_RUN, "source": LAMBDA, "ref": "v1"},
        {"keypath": TASK_RUN, "source": LAMBDA, "ref": "v2"}])

    assert response.status_code == 400
    assert "twice" in response.get_json()["detail"]


@pytest.fixture
def acme_project(gcd_design, tmp_path):
    '''A run whose two tasks of one tool each read a `scripts` dataroot from an
    allowlisted source of its own.'''
    from siliconcompiler import Flowgraph
    from pytasks import AcmeCheck, AcmeRun

    project = _nop_asic(gcd_design, tmp_path, resource(PDK, "lambda", LAMBDA, create=False))
    flow = Flowgraph("acmeflow")
    flow.node("run", AcmeRun())
    flow.node("check", AcmeCheck())
    flow.edge("run", "check")
    project.set_flow(flow)
    return project


def sent_back_for_run(server, server_client, key, token, job_archive, acme_project):
    '''Staged with every source fetched but `run`'s, which fails for good: the
    job goes back asking for that one dataroot.'''
    store = server.config["SC_JOBS"]._sources

    def resolve(source, ref, into, timeout):
        if "acme-run" in source:
            raise Permanent("the source answered 404")
        for name in ("datasheet.pdf", "tcl/check/check.tcl"):
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            (into / name).write_text("fetched\n")

    store._resolve = resolve
    archive, digest, size = job_archive(acme_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    assert read(server_client, key, token, job["id"])["upload_sources"] == [
        {"kind": "dataroot", "keypath": TASK_RUN}]
    return job


def test_a_follow_up_answers_one_tasks_dataroot_by_its_keypath(
        server, server_client, key, token, job_archive, acme_project, dispatcher):
    job = sent_back_for_run(server, server_client, key, token, job_archive, acme_project)
    run = collected_path(first(acme_project, ("tool", "acme_sim", "task", "run", "refdir")))

    response = send(server_client, key, token, job["id"], {
        f"sc_collected_files/{run}/run.tcl": b"sent by the client\n"})

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)


def test_a_member_under_another_tasks_dataroot_of_that_name_was_not_asked_for(
        server, server_client, key, token, job_archive, acme_project, dispatcher):
    '''🔴 By keypath: `check`'s `scripts` is not `run`'s, whatever the tool.'''
    job = sent_back_for_run(server, server_client, key, token, job_archive, acme_project)
    check = collected_path(first(acme_project,
                                 ("tool", "acme_sim", "task", "check", "refdir")))

    response = send(server_client, key, token, job["id"], {
        f"sc_collected_files/{check}/check.tcl": b"not asked for\n"})

    assert response.status_code == 422
    assert response.get_json()["reason"] == "unrequested_member"


###########################
# A private dataroot may be fetched, never uploaded or asked for (surface D299)
###########################

SECRET = "https+private://github.com/siliconcompiler/secret/archive/refs/tags/"
SECRET_KEYPATH = ["library", "secret", "dataroot", "secret"]


def remote_private(source):
    '''A private PDK fetched from ``source`` at `v1`.'''
    pdk = PDK("secret")
    pdk.set_dataroot("secret", source, tag="v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    return pdk


@pytest.fixture
def private_project(gcd_design, tmp_path):
    '''A run on a private PDK whose source is on the allowlist: the source the
    manifest carries, and never the create body.'''
    return _nop_asic(gcd_design, tmp_path, remote_private(SECRET))


def staged(server_client, key, token, archive, digest, size):
    job = stage(server_client, key, token, archive, size)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


def test_a_private_dataroot_on_the_allowlist_is_fetched_and_the_job_runs(
        server, server_client, key, token, job_archive, private_project, dispatcher):
    '''Neither in the operator's map nor held: fetched from the manifest's own
    source while the job stages -- and the run reads that copy.'''
    from conftest import run_manifest

    fake_fetch(server)
    archive, digest, size = job_archive(private_project)
    job, response = staged(server_client, key, token, archive, digest, size)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    held = server.config["SC_JOBS"]._sources.held(
        "https://github.com/siliconcompiler/secret/archive/refs/tags/", "v1")
    assert held and held in json.dumps(
        run_manifest(dispatcher.submitted[0][2]).getdict()["library"]["secret"]["dataroot"])


def test_a_private_dataroot_already_held_is_supplied_without_a_fetch(
        server, server_client, key, token, job_archive, private_project, dispatcher):
    fake_fetch(server)
    first_archive, digest, size = job_archive(private_project)
    staged(server_client, key, token, first_archive, digest, size)
    assert wait_for(lambda: dispatcher.submitted)

    # A second job, and any fetch now would fail for good.
    fake_fetch(server, fail=Permanent("a fetch was not needed"))
    archive, digest, size = job_archive(private_project)
    job, response = staged(server_client, key, token, archive, digest, size)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: len(dispatcher.submitted) == 2)


def test_the_operators_copy_wins_and_needs_no_source(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher):
    '''A `file+private` source is on the submitter's machine, where no server
    fetches: the operator's copy, by keypath, is the one way it arrives.'''
    from conftest import run_manifest

    root = tmp_path / "operator-copy"
    root.mkdir()
    (root / "datasheet.pdf").write_text("x")
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"secret": {"secret": str(root)}}}
    fake_fetch(server, fail=Permanent("nothing is fetched"))
    project = _nop_asic(gcd_design, tmp_path, private(PDK, "secret", tmp_path / "mine"))

    archive, digest, size = job_archive(project)
    job, response = staged(server_client, key, token, archive, digest, size)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    assert str(root) in run_manifest(dispatcher.submitted[0][2]).get(
        "library", "secret", "dataroot", "secret", "path")


@pytest.mark.parametrize("source,fails", [
    # Not on the allowlist, and not held: no route.
    ("git+ssh+private://git.internal.example.com/secret.git", None),
    # On it, and its fetch fails for good.
    (SECRET, Permanent("the source answered 404")),
])
def test_a_private_dataroot_no_route_supplies_is_refused_and_never_asked_for(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher,
        source, fails):
    '''🔴 Never `awaiting_input`: nothing the client can send may stand in for a
    private dataroot, so the job ends `rejected`, `resource-unavailable` with
    its keypath.'''
    fake_fetch(server, fail=fails)
    project = _nop_asic(gcd_design, tmp_path, remote_private(source))
    archive, digest, size = job_archive(project)
    job, response = staged(server_client, key, token, archive, digest, size)

    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    in ("rejected", "awaiting_input"))
    job = read(server_client, key, token, job["id"])
    assert job["state"] == "rejected", job
    assert job["error"]["type"].endswith("/resource-unavailable")
    assert job["error"]["keypath"] == SECRET_KEYPATH
    assert not job.get("upload_sources")
    assert not dispatcher.submitted


def test_an_archive_carrying_a_private_value_is_refused_naming_it(
        server, server_client, key, token, job_archive, private_project, dispatcher,
        tmp_path):
    '''It must never have been sent, so it is not used in place of the server's
    own: `archive-rejected`, `unrequested_member`, naming the dataroot and the
    member.'''
    fake_fetch(server)
    archive, _, _ = job_archive(private_project)
    member = "sc_collected_files/" + collected_path(
        first(private_project, ("library", "secret", *DATASHEET)))
    carrying = tmp_path / "carrying.tar.gz"
    with tarfile.open(archive) as source, tarfile.open(carrying, "w:gz") as out:
        for item in source.getmembers():
            out.addfile(item, source.extractfile(item) if item.isfile() else None)
        info = tarfile.TarInfo(member)
        body = b"the private datasheet, sent anyway\n"
        info.size = len(body)
        out.addfile(info, io.BytesIO(body))
    data = carrying.read_bytes()

    job, response = staged(server_client, key, token, str(carrying),
                           "sha256:" + hashlib.sha256(data).hexdigest(), len(data))

    assert response.status_code == 422
    assert slug(response) == "archive-rejected"
    assert response.get_json()["reason"] == "unrequested_member"
    assert member in response.get_json()["detail"]
    assert "library,secret,dataroot,secret" in response.get_json()["detail"]
    assert not dispatcher.submitted
