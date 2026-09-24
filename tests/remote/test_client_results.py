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


def test_asking_for_a_file_and_being_served_a_stream_says_where_to_go(
        fake_v1, logged_in, tmp_path):
    '''🔴 Branch on the Content-Type that was served, never on the 303: a node
    can finish between the redirect and the fetch, so `node_log` can be asked
    for a file and handed a tail. It names the call that reads one rather than
    writing event frames into a .log.'''
    fake_v1.route(responses.GET, "jobs/j1/logs", "event: log\n\n",
                  content_type="text/event-stream")

    with pytest.raises(RemoteError) as raised:
        logged_in.node_log("j1", "stepone", "0", tmp_path / "node.log")

    assert "tail_log" in str(raised.value)
    assert not (tmp_path / "node.log").exists()


###########################
# A bundle is the rest of the run
###########################

def test_a_bundle_displaces_what_it_contains(fake_v1, results, nop_project):
    '''🔴 A bundle IS the rest of the run, so fetching it and then fetching the
    objects inside it downloads everything twice. On a real flow that is two
    requests instead of sixty-two.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("manifest"),
        artifact("bundle", "stepone", "0"),
        artifact("bundle", "steptwo", "0"),
        artifact("logs", "stepone", "0"),
        artifact("logs", "steptwo", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None",
                  json.dumps({"schemaversion": "0.0.0"}))
    for step in ("stepone", "steptwo"):
        fake_v1.route(responses.GET, f"jobs/j1/artifacts/art-bundle-{step}-0",
                      tarball(["outputs/gcd.pkg.json", f"sc_{step}_0.log"]),
                      content_type="application/gzip")

    assert results.fetch("j1") == 3

    fetched = sorted(c.request.path_url for c in fake_v1.calls
                     if "/artifacts/" in c.request.path_url)
    # The two logs are inside the two bundles, so they are not asked for.
    assert fetched == ["/v1/jobs/j1/artifacts/art-bundle-stepone-0",
                       "/v1/jobs/j1/artifacts/art-bundle-steptwo-0",
                       "/v1/jobs/j1/artifacts/art-manifest-None-None"]


def test_a_bundle_expands_in_its_own_nodes_directory(fake_v1, results,
                                                     nop_project):
    '''Stored relative to the node's working directory, which is why the
    contract has no per-artifact path: step, index and kind are enough.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("bundle", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-bundle-stepone-0",
                  tarball(["outputs/gcd.pkg.json", "reports/metrics.json"]),
                  content_type="application/gzip")

    results.fetch("j1")

    from siliconcompiler.utils.paths import workdir
    into = workdir(nop_project, step="stepone", index="0")
    assert os.path.isfile(os.path.join(into, "outputs", "gcd.pkg.json"))
    assert os.path.isfile(os.path.join(into, "reports", "metrics.json"))


def test_the_manifest_is_fetched_even_beside_a_bundle(fake_v1, results):
    '''It is small, it is what the record is replayed from, and a client that
    relied on finding one inside the bundle would break on the deployment that
    indexes a manifest and no bulk output at all.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("manifest"), artifact("bundle", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None",
                  json.dumps({"schemaversion": "0.0.0"}))
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-bundle-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    assert results.fetch("j1") == 2


def test_a_bundle_that_is_refused_displaces_nothing(fake_v1, results, caplog):
    '''🔴 A bundle is never grantable, so present-and-refused is the ordinary
    case on a deployment with approvals. Everything else must still be
    fetched, and the caller told why it could not have the bundle.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("bundle", "stepone", "0", fetchable=False),
        artifact("logs", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0", "ran\n")

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 1

    assert "may not have this" in caplog.text


###########################
# Taking results as the run goes
###########################

def test_a_nodes_results_are_taken_when_that_node_finishes(fake_v1, results,
                                                           nop_project):
    '''🔴 Not at the end of the run. A node's bundle carries its manifest, so
    taking it as it appears is what keeps the local record -- metrics, tool
    versions, node states -- current while the rest of the flow runs on.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("bundle", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-bundle-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    taken = results.take("j1", {"nodes": [
        {"step": "stepone", "index": "0", "state": "completed", "terminal": True},
        {"step": "steptwo", "index": "0", "state": "running", "terminal": False}]})

    assert taken == 1

    from siliconcompiler.utils.paths import workdir
    assert os.path.isfile(os.path.join(
        workdir(nop_project, step="stepone", index="0"), "outputs", "gcd.pkg.json"))


def test_a_node_is_only_taken_once(fake_v1, results):
    '''The poll repeats every few seconds; the download must not.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("bundle", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-bundle-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    job = {"nodes": [{"step": "stepone", "index": "0", "state": "completed",
                      "terminal": True}]}

    assert results.take("j1", job) == 1
    assert results.take("j1", job) == 0

    fetches = [c for c in fake_v1.calls if "/artifacts/art-" in c.request.path_url]
    assert len(fetches) == 1


def test_nothing_is_listed_until_something_finishes(fake_v1, results):
    '''One listing per poll in which something finished, not one per poll.'''
    assert results.take("j1", {"nodes": [
        {"step": "stepone", "index": "0", "state": "running", "terminal": False}]}) == 0

    assert not [c for c in fake_v1.calls if "artifacts" in c.request.path_url]


def test_the_final_sweep_does_not_fetch_what_the_run_already_took(
        fake_v1, results, nop_project):
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("bundle", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-bundle-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    results.take("j1", {"nodes": [{"step": "stepone", "index": "0",
                                   "state": "completed", "terminal": True}]})

    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("bundle", "stepone", "0")]})
    assert results.fetch("j1") == 0

    fetches = [c for c in fake_v1.calls if "/artifacts/art-" in c.request.path_url]
    assert len(fetches) == 1


def test_a_listing_that_fails_mid_run_is_not_fatal(fake_v1, results):
    '''Nothing is lost: the sweep at the end of the run asks again.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", "<html>502</html>",
                  status=502, content_type="text/html")

    assert results.take("j1", {"nodes": [{"step": "stepone", "index": "0",
                                          "state": "completed",
                                          "terminal": True}]}) == 0


def test_a_node_with_no_bundle_is_not_asked_about_again(fake_v1, results):
    '''🔴 A node the run skipped produces no working directory, so there is
    nothing to archive and its bundle never appears. Recording only the nodes
    whose bundles were FOUND left it outstanding for ever, and this listing
    then happened on every single poll for the length of the run -- per client.
    On a server with a few hundred of them that is the whole cost of watching
    a job.
    '''
    job = {"nodes": [{"step": "stepone", "index": "0", "state": "skipped",
                      "terminal": True}]}

    # The listing is empty: a skipped node archives nothing.
    for _ in range(4):
        fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": []})
        results.take("j1", job)

    listings = [c for c in fake_v1.calls
                if c.request.path_url.startswith("/v1/jobs/j1/artifacts?")
                or c.request.path_url == "/v1/jobs/j1/artifacts"]
    assert len(listings) == 1


def test_one_listing_per_batch_of_finished_nodes(fake_v1, results):
    '''Not one per poll, and not one per node: a wide flow finishes several
    nodes between two polls, and a quiet poll asks nothing at all.'''
    def bundle_for(step):
        return artifact("bundle", step, "0")

    def node(step, terminal):
        return {"step": step, "index": "0", "terminal": terminal,
                "state": "completed" if terminal else "running"}

    # Poll 1: nothing has finished -> no listing at all.
    results.take("j1", {"nodes": [node("stepone", False)]})

    # Poll 2: two finished together -> one listing, two fetches.
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [bundle_for("stepone"), bundle_for("steptwo")]})
    for step in ("stepone", "steptwo"):
        fake_v1.route(responses.GET, f"jobs/j1/artifacts/art-bundle-{step}-0",
                      tarball(["outputs/gcd.pkg.json"]),
                      content_type="application/gzip")

    assert results.take("j1", {"nodes": [node("stepone", True),
                                         node("steptwo", True)]}) == 2

    # Poll 3: nothing new -> no listing.
    results.take("j1", {"nodes": [node("stepone", True), node("steptwo", True)]})

    listings = [c for c in fake_v1.calls
                if "artifacts" in c.request.path_url
                and "/artifacts/" not in c.request.path_url]
    assert len(listings) == 1


###########################
# The run's own log
###########################

def test_the_job_level_log_lands_beside_the_nodes_not_on_top_of_job_log(
        fake_v1, results, nop_project):
    '''🔴 A remote run is still a `Scheduler` run -- which is what makes a flow
    that does not resolve fail here rather than on somebody else's machine --
    so the local `job.log` has an open handler appending to it for the whole
    run. Downloading onto it truncates a file this process is still writing.'''
    from siliconcompiler.utils.paths import jobdir

    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("logs", media_type="text/plain")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-None-None",
                  body="RuntimeError: git is required\n",
                  content_type="text/plain")

    here = jobdir(nop_project)
    os.makedirs(here, exist_ok=True)
    with open(os.path.join(here, "job.log"), "w") as local:
        local.write("what this process logged\n")

    assert results.fetch("j1") == 1

    assert open(os.path.join(here, "job.log")).read() == "what this process logged\n"
    landed = os.path.join(here, "remote-job.log")
    assert "git is required" in open(landed).read()


def test_the_advice_names_the_file_the_client_actually_writes():
    """The two live in different modules -- the message is rendered where
    problems are and the file is written where results are -- so nothing but
    this stops them drifting apart."""
    from siliconcompiler.remote.client.errors import NO_NODE_FAILED
    from siliconcompiler.remote.client.results import REMOTE_JOB_LOG

    assert REMOTE_JOB_LOG in NO_NODE_FAILED
