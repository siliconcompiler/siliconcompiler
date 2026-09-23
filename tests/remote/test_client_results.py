import io
import json
import os
import tarfile

import pytest
import responses

from siliconcompiler.remote import RemoteError
from siliconcompiler.remote.client.results import Results

from conftest import problem


# 🔴 The half the integration rig cannot reach. A working sc-server has no
# agreements, so it can never emit `blocked_by`; it cannot be made to serve a
# proxy's HTML 502; and every one of the five not-fetchable cases is a different
# sentence a person reads. These are the fixtures the phase's gate names.


def artifact(kind="manifest", step=None, index=None, fetchable=True, **extra):
    return {
        "id": f"art-{kind}-{step}-{index}",
        "step": step, "index": index, "kind": kind,
        "media_type": "application/json" if kind == "manifest" else "text/plain",
        "size_bytes": 12,
        "content_hash": "sha256:" + "0" * 64,
        "created_at": "2026-09-22T10:00:00.000Z",
        "expires_at": "2031-09-22T10:00:00.000Z",
        "deleted_at": None,
        "fetchable": fetchable,
        **extra,
    }


@pytest.fixture
def results(logged_in, nop_project):
    return Results(nop_project, logged_in)


def tarball(names):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name in names:
            info = tarfile.TarInfo(name)
            info.size = 2
            tar.addfile(info, io.BytesIO(b"{}"))
    return buffer.getvalue()


###########################
# A listing is the answer, even when the bytes are not
###########################

def test_a_manifest_and_nothing_else_is_a_successful_run(fake_v1, results,
                                                         nop_project, caplog):
    '''🔴 The manifest carries the record -- node states, metrics, tool
    versions -- so what happened is answerable with no outputs on disk.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("manifest")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None",
                  json.dumps({"schemaversion": "0.0.0"}))

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 1

    # Nothing is reported as wrong, because nothing is.
    assert "could not" not in caplog.text.lower()

    from siliconcompiler.utils.paths import jobdir
    assert os.path.isfile(os.path.join(jobdir(nop_project), "gcd.pkg.json"))


def test_an_empty_listing_is_legal(fake_v1, results, caplog):
    '''Three deployments reach it by different routes and none of them is an
    error: one indexes the manifest and stores no bulk output, one does not run
    the pipeline here at all, and one has had retention take everything.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": []})

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 0

    assert "kept nothing" in caplog.text
    assert "not an error" in caplog.text


def test_a_listing_with_no_manifest_says_so_without_calling_it_a_failure(
        fake_v1, results, caplog):
    '''A client that requires the manifest has the same bug one kind further
    along.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("logs", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0", "ran\n")

    with caplog.at_level("INFO"):
        assert results.fetch("j1") == 1

    assert "does not keep those" in caplog.text
    assert "nothing to retry" in caplog.text


###########################
# 🔴 Five states, five sentences
###########################

def test_deleted_is_never_reported_as_expired(fake_v1, results, caplog):
    '''🔴 Retention lapsing is the system doing what it said; a deleted_at is
    somebody deciding. Reported in that order, because a deleted object may
    also be past its retention.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-09-20T00:00:00.000Z",
                 expires_at="2020-01-01T00:00:00.000Z")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "deleted on 2026-09-20" in caplog.text
    assert "aged out" not in caplog.text


def test_expired_says_when_it_aged_out(fake_v1, results, caplog):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 expires_at="2026-01-05T00:00:00.000Z")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "aged out on 2026-01-05" in caplog.text
    assert "deleted" not in caplog.text


def test_blocked_by_an_agreement_names_it_and_where_to_ask(fake_v1, results,
                                                           caplog):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("final", "place", "0", fetchable=False, blocked_by="gf22-nda",
                 access_request_url="https://portal.test/request/1")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "gf22-nda" in caplog.text
    assert "https://portal.test/request/1" in caplog.text


def test_blocked_with_no_path_to_yes_does_not_invent_one(fake_v1, results,
                                                         caplog):
    '''An absent access_request_url is the honest answer, and the client must
    not offer a URL that was not given.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("final", "place", "0", fetchable=False, blocked_by="gf22-nda")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "gf22-nda" in caplog.text
    assert "http" not in caplog.text


def test_ungranted_with_no_agreement_says_asking_will_not_help(fake_v1, results,
                                                               caplog):
    '''The caller lacks the grant, or it is not grantable at all.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("issue", "place", "0", fetchable=False)]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "may not have this" in caplog.text
    assert "not something asking would change" in caplog.text


def test_the_five_are_five_different_sentences(results):
    '''Collapsing them answers "where did my results go" with the one sentence
    that fits none of the cases.'''
    said = {
        results._explain(artifact(fetchable=False,
                                  deleted_at="2026-09-20T00:00:00.000Z")),
        results._explain(artifact(fetchable=False,
                                  expires_at="2020-01-01T00:00:00.000Z")),
        results._explain(artifact(fetchable=False, blocked_by="nda")),
        results._explain(artifact(fetchable=False, blocked_by="nda",
                                  access_request_url="https://x.test")),
        results._explain(artifact(fetchable=False)),
    }
    assert len(said) == 5


###########################
# Putting it back
###########################

def test_an_archive_lands_in_the_nodes_own_directory(fake_v1, results,
                                                     nop_project):
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("outputs", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-outputs-stepone-0",
                  tarball(["outputs/gcd.pkg.json", "sc_stepone_0.log"]),
                  content_type="application/gzip")

    results.fetch("j1")

    from siliconcompiler.utils.paths import workdir
    into = workdir(nop_project, step="stepone", index="0")
    assert os.path.isfile(os.path.join(into, "outputs", "gcd.pkg.json"))
    assert os.path.isfile(os.path.join(into, "sc_stepone_0.log"))


def test_one_objects_failure_does_not_abort_the_others(fake_v1, results,
                                                       nop_project, caplog):
    '''B4: the pool went, and what may not go is that one node's failure costs
    the caller the rest of the run.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("logs", "stepone", "0"),
        artifact("logs", "steptwo", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0",
                  problem("not-found", 404), status=404,
                  content_type="application/problem+json")
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-steptwo-0", "ran\n")

    with caplog.at_level("ERROR"):
        assert results.fetch("j1") == 1

    from siliconcompiler.utils.paths import workdir
    assert os.path.isfile(os.path.join(
        workdir(nop_project, step="steptwo", index="0"), "sc_steptwo_0.log"))


def test_a_kind_this_client_has_no_home_for_is_left_alone(fake_v1, results):
    '''The set is closed and published, so an unrecognised kind means this
    client is older than the server -- not that the server is wrong.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("bundle", "stepone", "0")]})

    assert results.fetch("j1") == 0


###########################
# 🔴 The tolerance rule
###########################

def test_a_proxys_html_502_on_the_listing_is_rendered(fake_v1, results):
    '''problem+json is promised only for what a handler produced, so
    resp.json()["type"] throws on exactly the errors production serves most.'''
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  "<html><body><h1>502 Bad Gateway</h1></body></html>",
                  status=502, content_type="text/html")

    with pytest.raises(ServerProblem) as raised:
        results.fetch("j1")

    assert "502" in str(raised.value)
    assert raised.value.slug is None


def test_a_half_written_download_is_never_left_behind(fake_v1, logged_in,
                                                      tmp_path):
    '''The client's own build directory is the one place a half-file would be
    picked up by the next step as though it were real.'''
    class Breaks(io.BytesIO):
        def read(self, *a, **k):
            raise OSError("the connection went away")

    fake_v1.route(responses.GET, "jobs/j1/artifacts/a1", "x" * 100)

    target = tmp_path / "thing.json"
    import unittest.mock as mock
    with mock.patch("shutil.copyfileobj", side_effect=OSError("cut off")):
        with pytest.raises(OSError):
            logged_in.fetch_artifact("j1", "a1", target)

    assert not target.exists()
    assert not (tmp_path / "thing.json.part").exists()


def test_a_live_stream_is_recognised_and_refused_for_now(fake_v1, logged_in,
                                                         tmp_path):
    '''🔴 Branch on the Content-Type that was served, never on the 303: a node
    can finish between the redirect and the fetch.'''
    fake_v1.route(responses.GET, "jobs/j1/logs", "event: log\n\n",
                  content_type="text/event-stream")

    with pytest.raises(RemoteError) as raised:
        logged_in.node_log("j1", "stepone", "0", tmp_path / "node.log")

    assert "live stream" in str(raised.value)
