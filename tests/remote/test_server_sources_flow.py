import hashlib
import io
import json
import os
import tarfile
import time

import pytest

from conftest import call, outcome, read, run_manifest, slug
from test_owners import DATASHEET, _nop_asic, collected_path, private, resource
from test_server_jobs import create, put, stage, submit, submitted


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler import PDK                                        # noqa: E402
from siliconcompiler.remote.server.staging.sources import Permanent            # noqa: E402


# What the server cannot supply it asks for (D114). Create looks up and never
# fetches; the fetch runs while `staging`, after submit (D130); a source that
# fails for good sends the job back -- the one backwards edge -- asking for it.

LAMBDA = "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/"
LAMBDA_KEYPATH = ["library", "lambda", "dataroot", "lambda"]
TASK_RUN = ["tool", "acme_sim", "task", "run", "dataroot", "scripts"]
TASK_CHECK = ["tool", "acme_sim", "task", "check", "dataroot", "scripts"]
SECRET = "https+private://github.com/siliconcompiler/secret/archive/refs/tags/"
SECRET_KEYPATH = ["library", "secret", "dataroot", "secret"]


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


def gated(server):
    '''Fetches that wait on the gate returned.'''
    import threading

    gate = threading.Event()

    def slow(source, ref, into, timeout):
        gate.wait(5)
        (into / "datasheet.pdf").write_text("x")

    server.config["SC_JOBS"]._sources._resolve = slow
    return gate


def reaches(server_client, key, token, job, *states):
    return wait_for(lambda: read(server_client, key, token, job["id"])["state"] in states)


def transitions(server, job_id):
    return [(row["from_state"], row["to_state"]) for row in server.config["SC_STORE"].all(
        "SELECT from_state, to_state FROM job_state_transitions WHERE job_id = ? "
        "ORDER BY id", (job_id,))]


def follow_up(members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, body in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    data = buffer.getvalue()
    return data, "sha256:" + hashlib.sha256(data).hexdigest(), len(data)


def sent_back(server, server_client, key, token, job_archive, project,
              fail="the source answered 404"):
    '''Submitted with its one source failing for good: back in `awaiting_input`.'''
    fake_fetch(server, fail=Permanent(fail))
    job, _ = submitted(server_client, key, token, job_archive(project))
    assert reaches(server_client, key, token, job, "awaiting_input")
    return job


def send(server_client, key, token, job_id, members):
    data, digest, size = follow_up(members)
    grant = call(server_client, key, "POST", f"/v1/jobs/{job_id}/upload-grant",
                 token, json={"size_bytes": size, "digest": digest}).get_json()
    put(server_client, grant, data)
    return outcome(server_client, key, token,
                   submit(server_client, key, token, job_id, digest, size))


def staged(server_client, key, token, archive, digest, size):
    job = stage(server_client, key, token, archive, size)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


def collected(project, *keypath, n=None):
    '''The follow-up member answering ``keypath``'s datasheet.'''
    hashed = collected_path(project, (*keypath, *DATASHEET), **({} if n is None else {"n": n}))
    return {f"sc_collected_files/{hashed}": b"sent by the client\n"}


@pytest.mark.parametrize("sources,asked", [
    # Allowlisted and not held: assumed fetchable. Behind a key it lacks: asked for.
    ([{"keypath": LAMBDA_KEYPATH, "source": LAMBDA, "ref": "v0.2.22", "private": False},
      {"keypath": ["library", "acme_ip", "dataroot", "acme_ip"],
       "source": "git+ssh://github.com/acme/ip.git", "ref": "v1.2", "private": False}],
     [["library", "acme_ip", "dataroot", "acme_ip"]]),
    # A dataroot name is unique only within its owner, and many use `root` (§13; D282).
    ([{"keypath": ["library", "acme_ip", "dataroot", "root"],
       "source": "git+ssh://github.com/acme/ip.git", "ref": "v1", "private": False},
      {"keypath": ["library", "beta_ip", "dataroot", "root"],
       "source": "git+ssh://github.com/beta/ip.git", "ref": "v1", "private": False}],
     [["library", "acme_ip", "dataroot", "root"], ["library", "beta_ip", "dataroot", "root"]]),
    # Two tasks of one tool, and the library of its name, apart; `private` defaults false.
    ([{"keypath": TASK_RUN, "source": "https://example.com/acme/run/", "ref": "v1"},
      {"keypath": TASK_CHECK, "source": "https://example.com/acme/check/", "ref": "v1"},
      {"keypath": ["library", "acme_sim", "dataroot", "scripts"],
       "source": "https://example.com/acme/lib/", "ref": "v1"}],
     [TASK_RUN, TASK_CHECK, ["library", "acme_sim", "dataroot", "scripts"]]),
])
def test_create_asks_only_for_what_it_cannot_supply(server_client, key, token, sources, asked):
    job = create(server_client, key, token, sources=sources).get_json()

    assert job["upload_sources"] == [{"kind": "dataroot", "keypath": one} for one in asked]


def test_nothing_to_send_means_no_upload_sources(server_client, key, token):
    '''Absent means *nothing to send*: the member is never `[]`.'''
    assert "upload_sources" not in create(server_client, key, token).get_json()
    assert "upload_sources" not in create(server_client, key, token, jobname="job1",
                                          sources=[]).get_json()


@pytest.mark.parametrize("keypath,source,resource", [
    (["library", "secret", "dataroot", "secretroot"],
     "git+ssh://git.internal.example.com/secret.git", "secret"),
    (["library", "gf180", "dataroot", "gf180"], "file:///opt/pdks/gf180", "gf180"),
    (["library", "gf180", "dataroot", "gf180"], None, "gf180"),          # local: no source
    # The owner's name, the keypath saying which of its dataroots: a tool's
    # root would otherwise read as *the tool is unavailable*.
    (TASK_RUN, "git+ssh://git.internal.example.com/acme.git", "acme_sim"),
])
def test_a_private_source_no_route_supplies_is_refused_at_create(server_client, key, token,
                                                                 keypath, source, resource):
    '''Before a byte moves (D285, D299, D308): not the operator's, not held, not
    allowlisted. No kind, since names are unique across kinds; never asked for.'''
    entry = {"keypath": keypath, "private": True}
    if source:
        entry.update(source=source, ref="v1")

    response = create(server_client, key, token, sources=[entry])

    body = response.get_json()
    assert (response.status_code, slug(response)) == (422, "resource-unavailable")
    assert (body["resource"], body["keypath"]) == (resource, keypath)
    assert "resource_kind" not in body
    assert f"the private dataroot {','.join(keypath)} is not held by this server, and it " \
        "cannot fetch it either" in body["detail"]
    assert call(server_client, key, "GET", "/v1/jobs", token).get_json()["items"] == []


def test_a_private_source_the_operator_maps_or_the_allowlist_fetches_is_supplied(
        server, server_client, key, token, tmp_path):
    '''Never asked for: the operator's copy by keypath, the one route for a
    local one, or a fetch while staging.'''
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"secret": {"secretroot": str(tmp_path / "secret")}}}

    for n, entry in enumerate([
            {"keypath": ["library", "secret", "dataroot", "secretroot"], "private": True},
            {"keypath": ["library", "gf180", "dataroot", "gf180"], "private": True,
             "source": "https://github.com/siliconcompiler/gf180/archive/", "ref": "v1"}]):
        response = create(server_client, key, token, jobname=f"job{n}", sources=[entry])
        assert response.status_code == 201
        assert "upload_sources" not in response.get_json()


def test_one_tool_entry_supplies_every_task_and_a_task_entry_overrides(
        server, server_client, key, token, tmp_path):
    '''`private_dataroots`: `tool` covers all its tasks, `task` names one that
    differs, and a library of the tool's name is its own entry.'''
    every, check = tmp_path / "every", tmp_path / "check"
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"acme_sim": {"scripts": str(tmp_path / "library")}},
        "tool": {"acme_sim": {"scripts": str(every)}},
        "task": {"acme_sim": {"check": {"scripts": str(check)}}}}
    supply = server.config["SC_JOBS"]._supply

    assert supply.private_root(TASK_RUN) == str(every)
    assert supply.private_root(TASK_CHECK) == str(check)
    assert supply.private_root(["tool", "other", "task", "run", "dataroot", "scripts"]) is None
    assert supply.private_root(["library", "acme_sim", "dataroot", "scripts"]) == \
        str(tmp_path / "library")
    assert create(server_client, key, token, sources=[
        {"keypath": TASK_RUN, "private": True},
        {"keypath": TASK_CHECK, "private": True}]).status_code == 201


def test_a_query_value_in_a_source_is_never_stored(server, server_client, key, token):
    '''The client masks it, and the server again; userinfo is refused outright
    (test_server_jobs).'''
    job = create(server_client, key, token, sources=[
        {"keypath": ["library", "ip", "dataroot", "ip"],
         "source": "https://gitlab.com/acme/ip/archive/?private_token=ghp_secret",
         "ref": "v1", "private": False}]).get_json()

    stored = server.config["SC_STORE"].one(
        "SELECT descriptor FROM jobs WHERE id = ?", (job["id"],))["descriptor"]
    assert "ghp_secret" not in stored
    assert "gitlab.com/acme/ip/archive/?private_token=***" in stored


@pytest.mark.parametrize("private", [False, True])
def test_a_queried_source_is_asked_for_and_never_fetched(server, server_client, key, token,
                                                         private):
    '''Surface D308: a masked value says what the source is, not enough to
    fetch it, even from the allowlist. A public one is asked for; a private
    one, with no operator's or held copy, is refused.'''
    fetched = []
    store = server.config["SC_JOBS"]._sources
    store._resolve = lambda *args: fetched.append(args)
    source = f"{LAMBDA}?token=***"

    assert server.config["SC_JOBS"]._supply.allowlisted(LAMBDA, "v0.2.22")
    assert not server.config["SC_JOBS"]._supply.allowlisted(source, "v0.2.22")
    response = create(server_client, key, token, sources=[
        {"keypath": LAMBDA_KEYPATH, "source": source, "ref": "v0.2.22", "private": private}])

    if private:
        assert (response.status_code, slug(response)) == (422, "resource-unavailable")
    else:
        assert response.get_json()["upload_sources"] == [
            {"kind": "dataroot", "keypath": LAMBDA_KEYPATH}]
    with pytest.raises(Permanent):
        store.fetch(source, "v0.2.22", 5)
    assert not fetched


@pytest.mark.parametrize("entry", [
    {"keypath": ["library", "acme"]},
    {"keypath": ["tool", "acme_sim", "dataroot", "scripts"]},      # a tool's, no task
    {"keypath": ["option", "x", "dataroot", "y"]},
    {"keypath": "library,acme,dataroot,acme"},
    {"keypath": ["library", "acme", "dataroot", ""]},
    # The old spelling, alone or beside the new, is an unknown member.
    {"name": "acme", "dataroot": "acme"},
    {"keypath": ["library", "acme", "dataroot", "acme"], "dataroot": "acme"},
    # So is a `kind`: the server finds a name's kind (entitlements D75).
    {"keypath": LAMBDA_KEYPATH, "kind": "pdk"},
    "not an object",
])
def test_a_source_named_otherwise_than_by_its_keypath_is_refused(server_client, key,
                                                                 token, entry):
    if isinstance(entry, dict):
        entry = dict(entry, source=LAMBDA, ref="v1")

    response = create(server_client, key, token, sources=[entry])

    assert (response.status_code, slug(response)) == (400, "invalid-request")


def test_one_dataroot_named_twice_is_refused(server_client, key, token):
    response = create(server_client, key, token, sources=[
        {"keypath": TASK_RUN, "source": LAMBDA, "ref": "v1"},
        {"keypath": TASK_RUN, "source": LAMBDA, "ref": "v2"}])

    assert response.status_code == 400
    assert "twice" in response.get_json()["detail"]


def test_an_allowlisted_source_is_fetched_after_submit_then_dispatched(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''No request waits on the fetch, and it happens BEFORE `queued`, which
    only moves forward (D130). The run reads the server's held copy.'''
    fake_fetch(server)
    job, response = submitted(server_client, key, token, job_archive(remote_project))

    assert response.status_code == 202
    assert response.get_json()["state"] == "staging"
    assert wait_for(lambda: dispatcher.submitted)
    assert transitions(server, job["id"])[-2:] == [("awaiting_input", "staging"),
                                                   ("staging", "queued")]

    ran = run_manifest(dispatcher.submitted[0][2])
    held = server.config["SC_JOBS"]._sources.held(LAMBDA, "v1")
    pointed = json.dumps(ran.getdict()["library"]["lambda"]["dataroot"])
    assert held and held in pointed
    assert LAMBDA not in pointed


def test_a_source_that_fails_for_good_sends_the_job_back_saying_why(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''`staging -> awaiting_input`, naming what failed and nothing else. It
    frees its `concurrent_jobs` slot and takes a `pending_uploads` one, both
    counted by state, and the abandonment clock runs from the transition.'''
    job = sent_back(server, server_client, key, token, job_archive, remote_project)

    back = read(server_client, key, token, job["id"])
    assert back["upload_sources"] == [{"kind": "dataroot", "keypath": LAMBDA_KEYPATH}]
    assert back["terminal"] is False
    assert not dispatcher.submitted
    store = server.config["SC_STORE"]
    reason = store.one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? "
        "AND from_state = 'staging' AND to_state = 'awaiting_input'", (job["id"],))["reason"]
    assert "the dataroot library,lambda,dataroot,lambda: the source answered 404" in reason
    # `transitions` lists every state entered, the send-back included (§17; D278).
    assert [entry["state"] for entry in back["transitions"]] == \
        ["created", "awaiting_input", "staging", "awaiting_input"]
    assert "the source answered 404" in back["transitions"][-1]["reason"]

    user = store.one("SELECT user_id FROM jobs WHERE id = ?", (job["id"],))["user_id"]
    assert store.one("SELECT count(*) AS n FROM jobs WHERE user_id = ? AND state IN "
                     "('staging','queued','running','cancelling')", (user,))["n"] == 0
    row = store.one("SELECT created_at, state_changed_at FROM jobs WHERE id = ?", (job["id"],))
    assert row["state_changed_at"] >= row["created_at"]


@pytest.mark.threaded_staging
def test_a_staging_job_counts_against_concurrent_jobs(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''Fetches are work: a state no limit counted would let one account stage
    any number of jobs at once.'''
    gate = gated(server)
    server.config["SC_CONFIG"].limits["concurrent_jobs"] = 1
    try:
        first, _ = submitted(server_client, key, token, job_archive(remote_project))
        assert read(server_client, key, token, first["id"])["state"] == "staging"

        # Refused at create, before any upload.
        refused = create(server_client, key, token, jobname="job1")
        assert refused.status_code == 429
        assert refused.get_json()["limit"] == "concurrent_jobs"
        assert int(refused.headers["Retry-After"]) >= 1
    finally:
        gate.set()


def test_a_fetched_copy_missing_a_required_file_is_refused_from_staging(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher):
    '''`rejected` means refused before it ran, at submit or while staging.'''
    from test_required import carried, reading

    store = server.config["SC_JOBS"]._sources
    store._resolve = lambda source, ref, into, timeout: (into / "other.pdf").write_text("x")
    project = carried(reading(gcd_design, tmp_path, ("library", "lambda", *DATASHEET),
                              pdk=resource(PDK, "lambda", LAMBDA, create=False)))

    job, _ = submitted(server_client, key, token, job_archive(project))

    assert reaches(server_client, key, token, job, "rejected")
    assert transitions(server, job["id"])[-1] == ("staging", "rejected")
    assert not dispatcher.submitted


@pytest.mark.threaded_staging
def test_cancelling_a_job_still_fetching_stops_the_fetch(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''`cancelling`, work being in flight; the staging thread stops the fetch
    and writes `cancelled`, a staging job having no scheduler id.'''
    gate = gated(server)
    job, _ = submitted(server_client, key, token, job_archive(remote_project))

    cancelled = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                     json={}).get_json()
    gate.set()

    # No reason was given, so its entry carries none.
    assert cancelled["state"] == cancelled["transitions"][-1]["state"] == "cancelling"
    assert "reason" not in cancelled["transitions"][-1]
    assert reaches(server_client, key, token, job, "cancelled")
    assert not dispatcher.submitted
    assert transitions(server, job["id"])[-2:] == [("staging", "cancelling"),
                                                   ("cancelling", "cancelled")]


def test_a_held_copy_records_its_commit_and_holds_no_moving_ref(tmp_path, monkeypatch):
    '''The commit is recorded before `.git` goes, and a branch is held for one
    job's staging, never across jobs.'''
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
    with open(os.path.join(os.path.dirname(fetched), sources._COMPLETE)) as f:
        assert json.load(f)["commit"] == "a" * 40

    monkeypatch.setattr(sources, "MOVING_HOLD_SECONDS", -1)
    assert store.held("https://example.com/ip.git", "main") is None
    # Fetched again, beside -- never over -- the copy a job may be reading.
    again = store.fetch("https://example.com/ip.git", "main", 10)
    assert again != fetched and os.path.isdir(fetched)

    store._resolve = resolve(False)
    pinned = store.fetch("https://example.com/ip.git", "v1.0", 10)
    assert store.held("https://example.com/ip.git", "v1.0") == pinned


@pytest.mark.parametrize("member", ["manifest", "wheel"])
def test_a_follow_up_may_hold_only_what_was_asked_for(
        server, server_client, key, token, job_archive, remote_project, dispatcher, member):
    '''Anything else is `unrequested_member`: a second upload must not replace
    what the first carried after the check, and a wheel arrives in the first
    archive or answers a `python` entry, never beside a dataroot.'''
    from siliconcompiler.remote import environment

    job = sent_back(server, server_client, key, token, job_archive, remote_project)

    response = send(server_client, key, token, job["id"], {
        "gcd.pkg.json": b"{}"} if member == "manifest" else {
        f"{environment.wheels_path()}/scfake-1.0-py3-none-any.whl": b"PK"})

    assert (response.status_code, slug(response)) == (422, "archive-rejected")
    assert response.get_json()["reason"] == "unrequested_member"


def test_the_asked_for_sources_arrive_each_upload_kept_and_the_job_runs(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''Each upload is kept as its own input, in order, under the digest its
    submit checked, so what was sent can be inspected.'''
    job = sent_back(server, server_client, key, token, job_archive, remote_project)
    data, digest, size = follow_up(collected(remote_project, "library", "lambda"))
    grant = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/upload-grant",
                 token, json={"size_bytes": size, "digest": digest}).get_json()
    put(server_client, grant, data)

    response = outcome(server_client, key, token,
                       submit(server_client, key, token, job["id"], digest, size))

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    uploads = server.config["SC_STORE"].all(
        "SELECT digest, size_bytes FROM artifacts WHERE job_id = ? "
        "AND kind = 'input' AND step IS NULL ORDER BY created_at, id", (job["id"],))
    assert len(uploads) == 2
    assert (uploads[1]["digest"], uploads[1]["size_bytes"]) == (digest, size)


def test_the_staging_record_gains_a_section_each_pass_and_is_scrubbed(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''The job's `staging` artifact (D295): a section per pass, one artifact,
    scrubbed like `detail`, a credential in a fetch's error included.'''
    import gzip

    job = sent_back(server, server_client, key, token, job_archive, remote_project,
                    fail="the source answered 404 for https://ci:hunter2@example.test/pdk.tar.gz")
    assert send(server_client, key, token, job["id"],
                collected(remote_project, "library", "lambda")).status_code == 202
    store = server.config["SC_STORE"]

    def staging():
        rows = store.all("SELECT storage_key FROM artifacts WHERE job_id = ? "
                         "AND kind = 'staging'", (job["id"],))
        assert len(rows) == 1
        with gzip.open(server.config["SC_STORAGE"].artifact_path(rows[0]["storage_key"]),
                       "rt") as f:
            return f.read()

    # Indexed as each pass ends, so replaced, never added to.
    assert wait_for(lambda: "handed the job to the scheduler" in staging())
    text = staging()

    assert text.count("==> staging, pass ") == 2
    first_pass, second_pass = text.split("==> staging, pass 2")
    assert "sent back for" in first_pass
    assert "handed the job to the scheduler" in second_pass
    assert "hunter2" not in text


def test_staging_past_its_limit_ends_the_job_staging_timed_out(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''Surface D294: bounded as a whole by `max_staging_seconds`, whatever
    phase the time goes on, then `failed`, `staging-timed-out`, naming the
    limit: the job's own, not this server's failure.'''
    server.config["SC_CONFIG"].limits["max_staging_seconds"] = 1
    fake_fetch(server)._resolve = lambda source, ref, into, timeout: time.sleep(3)

    job, _ = submitted(server_client, key, token, job_archive(remote_project))

    assert reaches(server_client, key, token, job, "failed")
    error = read(server_client, key, token, job["id"])["error"]
    assert error["type"].endswith("/staging-timed-out")
    assert error["limit"] == "max_staging_seconds"
    assert "while fetching sources" in error["detail"]
    assert not dispatcher.submitted


def test_a_job_sent_back_gets_a_fresh_staging_limit(
        server, server_client, key, token, job_archive, remote_project, dispatcher,
        monkeypatch):
    '''The limit counts one pass, so two passes each taking most of it finish.'''
    from siliconcompiler.remote.server.jobs.pythonenv import PythonEnvMixin

    server.config["SC_CONFIG"].limits["max_staging_seconds"] = 2

    def slow_then_gone(source, ref, into, timeout):
        time.sleep(1.2)
        raise Permanent("the source answered 404")

    fake_fetch(server)._resolve = slow_then_gone
    job, _ = submitted(server_client, key, token, job_archive(remote_project))
    assert reaches(server_client, key, token, job, "awaiting_input")

    def slow_install(self, job, summary):
        time.sleep(1.2)
        return []

    monkeypatch.setattr(PythonEnvMixin, "_install_on_host", slow_install)
    assert send(server_client, key, token, job["id"],
                collected(remote_project, "library", "lambda")).status_code == 202

    assert wait_for(lambda: dispatcher.submitted)
    assert read(server_client, key, token, job["id"])["state"] != "failed"


@pytest.mark.parametrize("answer,accepted", [("there", True), ("here", False)])
def test_a_follow_up_holds_the_asked_value_and_no_other_of_its_parameter(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher,
        answer, accepted):
    '''Per value: asked for the dataroot `there`, the follow-up carries its
    value alone; the local value beside it went up already.'''
    from test_owners import two_sources

    project = _nop_asic(gcd_design, tmp_path, two_sources(tmp_path, LAMBDA))
    job = sent_back(server, server_client, key, token, job_archive, project)
    assert read(server_client, key, token, job["id"])["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "mixed", "dataroot", "there"]}]

    response = send(server_client, key, token, job["id"], collected(
        project, "library", "mixed", n=0 if answer == "here" else 1))

    if accepted:
        assert response.status_code == 202, response.get_json()
        assert wait_for(lambda: dispatcher.submitted)
    else:
        assert response.status_code == 422
        assert response.get_json()["reason"] == "unrequested_member"


@pytest.fixture
def acme_project(gcd_design, tmp_path):
    '''Two tasks of one tool, each reading a `scripts` dataroot from an
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


@pytest.mark.parametrize("task,accepted", [("run", True), ("check", False)])
def test_a_follow_up_answers_one_tasks_dataroot_by_its_keypath(
        server, server_client, key, token, job_archive, acme_project, dispatcher,
        task, accepted):
    '''Every source fetched but `run`'s, which fails for good, so the job asks
    for that one dataroot: `check`'s `scripts` is not `run`'s, whatever the tool.'''
    def resolve(source, ref, into, timeout):
        if "acme-run" in source:
            raise Permanent("the source answered 404")
        for name in ("datasheet.pdf", "tcl/check/check.tcl"):
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            (into / name).write_text("fetched\n")

    server.config["SC_JOBS"]._sources._resolve = resolve
    job, _ = submitted(server_client, key, token, job_archive(acme_project))
    assert reaches(server_client, key, token, job, "awaiting_input")
    assert read(server_client, key, token, job["id"])["upload_sources"] == [
        {"kind": "dataroot", "keypath": TASK_RUN}]
    refdir = collected_path(acme_project, ("tool", "acme_sim", "task", task, "refdir"))

    response = send(server_client, key, token, job["id"], {
        f"sc_collected_files/{refdir}/{task}.tcl": b"sent by the client\n"})

    if accepted:
        assert response.status_code == 202, response.get_json()
        assert wait_for(lambda: dispatcher.submitted)
    else:
        assert response.status_code == 422
        assert response.get_json()["reason"] == "unrequested_member"


def remote_private(source):
    '''A private PDK fetched from ``source`` at `v1`.'''
    pdk = PDK("secret")
    pdk.set_dataroot("secret", source, tag="v1")
    with pdk.active_dataroot("secret"):
        pdk.set(*DATASHEET, "datasheet.pdf")
    return pdk


@pytest.fixture
def private_project(gcd_design, tmp_path):
    '''A private PDK whose source, the manifest's and never the create
    body's, is on the allowlist.'''
    return _nop_asic(gcd_design, tmp_path, remote_private(SECRET))


def test_a_private_dataroot_on_the_allowlist_is_fetched_then_held(
        server, server_client, key, token, job_archive, private_project, dispatcher):
    '''Neither mapped nor held: fetched from the manifest's own source while
    staging, and the run reads that copy -- which a second job then uses
    without a fetch.'''
    fake_fetch(server)
    archive, digest, size = job_archive(private_project)
    _, response = staged(server_client, key, token, archive, digest, size)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    held = server.config["SC_JOBS"]._sources.held(
        "https://github.com/siliconcompiler/secret/archive/refs/tags/", "v1")
    assert held and held in json.dumps(
        run_manifest(dispatcher.submitted[0][2]).getdict()["library"]["secret"]["dataroot"])

    fake_fetch(server, fail=Permanent("a fetch was not needed"))
    archive, digest, size = job_archive(private_project)
    _, response = staged(server_client, key, token, archive, digest, size)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: len(dispatcher.submitted) == 2)


def test_the_operators_copy_wins_and_needs_no_source(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher):
    '''A `file+private` source is on the submitter's machine, where no server
    fetches: the operator's copy, by keypath, is the one way it arrives.'''
    root = tmp_path / "operator-copy"
    root.mkdir()
    (root / "datasheet.pdf").write_text("x")
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "library": {"secret": {"secret": str(root)}}}
    fake_fetch(server, fail=Permanent("nothing is fetched"))
    project = _nop_asic(gcd_design, tmp_path, private(PDK, "secret", tmp_path / "mine"))

    archive, digest, size = job_archive(project)
    _, response = staged(server_client, key, token, archive, digest, size)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)
    assert str(root) in run_manifest(dispatcher.submitted[0][2]).get(
        "library", "secret", "dataroot", "secret", "path")


@pytest.mark.parametrize("source,fails", [
    ("git+ssh+private://git.internal.example.com/secret.git", None),   # no route
    (SECRET, Permanent("the source answered 404")),          # allowlisted, failing for good
])
def test_a_private_dataroot_no_route_supplies_is_refused_and_never_asked_for(
        server, server_client, key, token, job_archive, gcd_design, tmp_path, dispatcher,
        source, fails):
    '''Never `awaiting_input`: nothing the client sends may stand in for a
    private dataroot, so `rejected`, `resource-unavailable`, with its keypath.'''
    fake_fetch(server, fail=fails)
    project = _nop_asic(gcd_design, tmp_path, remote_private(source))
    job, _ = submitted(server_client, key, token, job_archive(project))

    assert reaches(server_client, key, token, job, "rejected", "awaiting_input")
    job = read(server_client, key, token, job["id"])
    assert job["state"] == "rejected", job
    assert job["error"]["type"].endswith("/resource-unavailable")
    assert job["error"]["keypath"] == SECRET_KEYPATH
    assert not job.get("upload_sources")
    assert not dispatcher.submitted


def test_an_archive_carrying_a_private_value_is_refused_naming_it(
        server, server_client, key, token, job_archive, private_project, dispatcher,
        tmp_path):
    '''It must never have been sent, so it is not used in place of the
    server's own: `unrequested_member`, the dataroot as `keypath` and the
    member in `detail` -- and the upload is not kept (D308).'''
    import gzip

    fake_fetch(server)
    archive, _, _ = job_archive(private_project)
    member = "sc_collected_files/" + collected_path(
        private_project, ("library", "secret", *DATASHEET))
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

    assert (response.status_code, slug(response)) == (422, "archive-rejected")
    body = response.get_json()
    assert body["reason"] == "unrequested_member"
    assert member in body["detail"] and "library,secret,dataroot,secret" in body["detail"]
    assert body["keypath"] == SECRET_KEYPATH
    assert not dispatcher.submitted

    kinds = [row["kind"] for row in server.config["SC_STORE"].all(
        "SELECT kind FROM artifacts WHERE job_id = ?", (job["id"],))]
    assert "input" not in kinds and "staging" in kinds
    for where, _, files in os.walk("datadir"):
        for name in files:
            with open(os.path.join(where, name), "rb") as f:
                data = f.read()
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            assert b"the private datasheet, sent anyway" not in data, name


def test_an_archive_refused_for_another_reason_is_kept(
        server, server_client, key, token, job_archive, dispatcher):
    '''Only what it must not carry costs the upload: an ordinary stray member
    is refused, and kept as the job's `input`.'''
    archive, digest, size = job_archive(extra={"stray.txt": b"not asked for\n"})
    job, response = staged(server_client, key, token, archive, digest, size)

    assert response.get_json()["reason"] == "unrequested_member"
    assert "keypath" not in response.get_json()
    assert [row["kind"] for row in server.config["SC_STORE"].all(
        "SELECT kind FROM artifacts WHERE job_id = ? AND kind = 'input'",
        (job["id"],))] == ["input"]
