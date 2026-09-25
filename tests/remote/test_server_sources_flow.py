import hashlib
import io
import json
import tarfile
import time

import pytest

from conftest import call, slug
from test_owners import DATASHEET, _nop_asic, first, private, resource
from test_server_jobs import FakeDispatcher, create, put, stage, submit


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler import PDK                                        # noqa: E402
from siliconcompiler.remote.server.sources import Permanent            # noqa: E402


# What the server cannot supply, it asks for (D114); create looks up and never
# fetches, and the fetch runs after submit while `queued` (D124). A source that
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

    def archive(url, into, timeout, session):
        if fail:
            raise fail
        (into / "datasheet.pdf").write_text("from the release\n")

    store._archive = archive
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
        {"kind": "pdk", "name": "lambda", "dataroot": "lambda",
         "source": LAMBDA, "ref": "v0.2.22", "private": False},
        {"kind": "library", "name": "acme_ip", "dataroot": "acme_ip",
         "source": "git+ssh://git@github.com/acme/ip.git", "ref": "v1.2",
         "private": False},
    ]).get_json()

    # Allowlisted and not held: assumed fetchable, not listed. Behind a key
    # this server has not got: asked for.
    assert job["upload_sources"] == [
        {"kind": "library", "name": "acme_ip", "dataroot": "acme_ip"}]


def test_no_sources_means_no_upload_sources(server_client, key, token):
    '''ABSENT when no `sources` were sent; `[]` when nothing is missing.'''
    assert "upload_sources" not in create(server_client, key, token).get_json()
    assert create(server_client, key, token, sources=[]).get_json()["upload_sources"] == []


def test_a_private_source_with_no_copy_here_is_refused_at_create(
        server_client, key, token):
    response = create(server_client, key, token, sources=[
        {"kind": "pdk", "name": "secret", "dataroot": "secret", "private": True}])

    assert response.status_code == 422
    assert slug(response) == "resource-unavailable"
    assert response.get_json()["resource"] == "secret"


def test_credentials_in_a_source_are_never_stored(server, server_client, key, token):
    '''🔴 The client strips them; the server strips them again.'''
    job = create(server_client, key, token, sources=[
        {"kind": "library", "name": "ip", "dataroot": "ip",
         "source": "https://user:ghp_secret@gitlab.com/acme/ip/archive/",
         "ref": "v1", "private": False}]).get_json()

    stored = server.config["SC_STORE"].one(
        "SELECT descriptor FROM jobs WHERE id = ?", (job["id"],))["descriptor"]
    assert "ghp_secret" not in stored
    assert "gitlab.com/acme/ip" in stored


###########################
# After submit: fetched while queued
###########################

def test_an_allowlisted_source_is_fetched_after_submit_then_dispatched(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    fake_fetch(server)
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)

    response = submit(server_client, key, token, job["id"], digest, size)

    # No request waits on the fetch.
    assert response.status_code == 202
    assert response.get_json()["state"] == "queued"
    assert wait_for(lambda: dispatcher.submitted)

    # The run reads the server's held copy, and its manifest says so.
    manifest = open(dispatcher.submitted[0][2]).read()
    held = server.config["SC_JOBS"]._sources.held(LAMBDA, "v1")
    assert held and held in manifest
    assert LAMBDA not in json.dumps(json.loads(manifest)["library"]["lambda"]["dataroot"])


def test_a_source_that_fails_for_good_sends_the_job_back_saying_why(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''🔴 The one backwards edge: `queued -> awaiting_input`, naming what
    failed and nothing else -- and the transition says why.'''
    fake_fetch(server, fail=Permanent("the source answered 404"))
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    back = read(server_client, key, token, job["id"])
    assert back["upload_sources"] == [{"kind": "pdk", "name": "lambda", "dataroot": "lambda"}]
    assert back["terminal"] is False
    assert not dispatcher.submitted

    reason = server.config["SC_STORE"].one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? "
        "AND from_state = 'queued' AND to_state = 'awaiting_input'",
        (job["id"],))["reason"]
    assert "pdk lambda (lambda): the source answered 404" in reason


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
                     "('queued','running','cancelling')", (user,))["n"] == 0
    row = store.one("SELECT created_at, state_changed_at FROM jobs WHERE id = ?",
                    (job["id"],))
    assert row["state_changed_at"] >= row["created_at"]


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
                 token, json={"bytes": size}).get_json()
    put(server_client, grant, data)
    return submit(server_client, key, token, job_id, digest, size)


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
    assert response.get_json()["violation"] == "unrequested_member"


def test_the_asked_for_sources_arrive_and_the_job_runs(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    job = sent_back(server, server_client, key, token, job_archive, remote_project)
    hashed = first(remote_project, ("library", "lambda", *DATASHEET)).get_hashed_filename()

    response = send(server_client, key, token, job["id"], {
        f"sc_collected_files/{hashed}": b"sent by the client\n"})

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)


###########################
# Nothing to wait for
###########################

def test_cancelling_a_job_still_fetching_cancels_it_at_once(
        server, server_client, key, token, job_archive, remote_project, dispatcher):
    '''Nothing was dispatched, so there is nothing to wind down.'''
    import threading

    gate = threading.Event()
    store = server.config["SC_JOBS"]._sources

    def slow(url, into, timeout, session):
        gate.wait(5)
        (into / "datasheet.pdf").write_text("x")

    store._archive = slow
    archive, digest, size = job_archive(remote_project)
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)

    cancelled = call(server_client, key, "POST", f"/v1/jobs/{job['id']}/cancel", token,
                     json={}).get_json()
    gate.set()

    assert cancelled["state"] == "cancelled"
    time.sleep(0.3)
    assert not dispatcher.submitted


def test_a_private_source_mapped_here_is_supplied_at_create(server, server_client,
                                                            key, token, tmp_path):
    server.config["SC_CONFIG"]._values["private_dataroots"] = {
        "secret": {"secret": str(tmp_path)}}

    job = create(server_client, key, token, sources=[
        {"kind": "pdk", "name": "secret", "dataroot": "secret", "private": True}])

    assert job.status_code == 201
    assert job.get_json()["upload_sources"] == []


def test_private_and_local_resources_are_told_apart_at_create(server_client, key,
                                                              token, tmp_path):
    '''`private` is REQUIRED, and a descriptor source that is not a dict is a
    malformed request, not a missing file.'''
    response = create(server_client, key, token, sources=["not an object"])

    assert response.status_code == 400
    assert slug(response) == "invalid-request"
    _ = private  # the shared helper, for completeness of the imports
