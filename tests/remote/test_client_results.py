import io
import json
import os
import tarfile

import pytest
import responses

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
        "created_at": "2026-09-22T10:00:00.000Z",
        "retained_until": "2031-09-22T10:00:00.000Z",
        "deleted_at": None,
        "deleted_cause": None,
        "deleted_reason": None,
        "fetchable": fetchable,
        **extra,
    }


@pytest.fixture
def fake_v1(fake_v1):
    '''The fake server, serving each artifact the way the contract stores
    it: gzipped, and a node's `logs` as a gzip tar of its log files. A test
    routes the plain bytes it means. Its listings name no digest unless a test
    is about the check.'''
    import gzip
    import re

    route = fake_v1.route

    def served(method, path, body, *args, **kwargs):
        found = re.search(r"/artifacts/art-(\w+)-(\w+)-(\w+)$", path)
        if found and isinstance(body, (str, bytes)) and kwargs.get("status", 200) < 300:
            kind, step, index = found.groups()
            data = body.encode() if isinstance(body, str) else body
            if kind == "logs" and step != "None":
                buffer = io.BytesIO()
                with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
                    info = tarfile.TarInfo(f"sc_{step}_{index}.log")
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
                data = buffer.getvalue()
            elif kind in ("manifest", "logs"):
                data = gzip.compress(data)
            body = data
            kwargs.setdefault("content_type", "application/gzip")
        return route(method, path, body, *args, **kwargs)

    fake_v1.route = served
    return fake_v1


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
    '''🔴 Reported before the expiry, because an object whose bytes are gone
    is usually also past its retention, and the useful sentence is the one that
    says why they went.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-09-20T00:00:00.000Z",
                 deleted_cause="removed", deleted_reason=None,
                 expires_at="2020-01-01T00:00:00.000Z")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "deleted on 2026-09-20" in caplog.text
    assert "aged out" not in caplog.text


def test_the_reaper_taking_it_is_aged_out_and_not_deleted(fake_v1, results,
                                                          caplog):
    '''🔴 `deleted_cause` is the only member that says so: retention lapsing
    ends in `deleted_at` too. Reading the old `deleted_reason` spelling, this
    client told a person *deleted* for bytes the system had reclaimed as it
    said it would.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-09-20T00:00:00.000Z",
                 deleted_cause="expired", deleted_reason=None)]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "aged out on 2026-09-20" in caplog.text
    assert "deleted" not in caplog.text


def test_a_cause_this_client_does_not_know_is_somebody_deciding(
        fake_v1, results, caplog):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-09-20T00:00:00.000Z",
                 deleted_cause="legal", deleted_reason=None)]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "deleted on 2026-09-20" in caplog.text


def test_the_reason_is_repeated_rather_than_interpreted(fake_v1, results,
                                                        caplog):
    '''🔴 A reaper sets `deleted_at` when retention lapses -- it has to,
    because `fetchable` asks first whether the bytes are there -- so the column
    alone no longer separates *the system did what it said* from *somebody
    removed this*. `deleted_cause` is what does, and `deleted_reason` is the
    prose that says why.

    Repeated verbatim and never matched against a vocabulary this client
    holds: a deployment that grows a new reason is understood by a client that
    shipped before it.
    '''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-09-20T00:00:00.000Z",
                 deleted_cause="removed",
                 deleted_reason="superseded by the rerun")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "deleted on 2026-09-20 -- superseded by the rerun" in caplog.text


def test_a_server_that_gives_no_reason_still_gets_a_sentence(fake_v1, results,
                                                             caplog):
    '''`deleted_reason` may be null, and a missing one is not a blank line.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-09-20T00:00:00.000Z",
                 deleted_cause="removed", deleted_reason=None)]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "deleted on 2026-09-20" in caplog.text


def test_expired_says_when_it_aged_out(fake_v1, results, caplog):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "stepone", "0", fetchable=False,
                 deleted_at="2026-01-05T00:00:00.000Z", deleted_cause="expired",
                 retained_until="2026-01-05T00:00:00.000Z")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "aged out on 2026-01-05" in caplog.text
    assert "deleted" not in caplog.text


def test_blocked_by_names_each_document_with_its_own_link(fake_v1, results, caplog):
    '''*Sign*: each document in the map, with the link its entry carries.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("final", "stepone", "0", fetchable=False, blocked_by={
            "gf22-nda": {"url": "https://portal.test/terms/gf22-nda"},
            "gf22-export": {"url": "https://portal.test/terms/gf22-export"}})]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "sign gf22-nda: https://portal.test/terms/gf22-nda" in caplog.text
    assert "sign gf22-export: https://portal.test/terms/gf22-export" in caplog.text


def test_a_document_with_no_link_is_named_by_its_title(fake_v1, results, caplog):
    '''An entry that is `{}` has no link, and the client names the document by
    its title in GET /v1/me's `terms` -- without inventing one.'''
    fake_v1.route(responses.GET, "me", {"id": "u1", "terms": [
        {"id": "gf22-nda", "title": "GF22 non-disclosure agreement"}]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("final", "stepone", "0", fetchable=False, blocked_by={"gf22-nda": {}})]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "GF22 non-disclosure agreement" in caplog.text
    assert "http" not in caplog.text


def test_an_approval_is_asked_for_and_a_request_shows_when(fake_v1, results, caplog):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("final", "stepone", "0", fetchable=False,
                 access_request_url="https://portal.test/request/1"),
        artifact("final", "steptwo", "0", fetchable=False,
                 access_request_url="https://portal.test/request/2",
                 access_requested_at="2026-09-21T10:00:00.000Z")]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "Ask for access at https://portal.test/request/1" in caplog.text
    assert "requested on 2026-09-21" in caplog.text


def test_ungranted_with_no_agreement_says_asking_will_not_help(fake_v1, results,
                                                               caplog):
    '''The caller lacks the grant, or it is not grantable at all.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("issue", "stepone", "0", fetchable=False)]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    assert "may not have this" in caplog.text
    assert "not something asking would change" in caplog.text


def test_the_cases_are_different_sentences(results):
    '''Collapsing them answers "where did my results go" with the one sentence
    that fits none of the cases.'''
    said = {
        results._explain(artifact(fetchable=False, deleted_cause="removed",
                                  deleted_at="2026-09-20T00:00:00.000Z")),
        results._explain(artifact(fetchable=False, deleted_cause="expired",
                                  deleted_at="2020-01-01T00:00:00.000Z")),
        results._explain(artifact(fetchable=False,
                                  blocked_by={"nda": {"url": "https://x.test/nda"}})),
        results._explain(artifact(fetchable=False, access_request_url="https://x.test")),
        results._explain(artifact(fetchable=False, access_request_url="https://x.test",
                                  access_requested_at="2026-09-20T00:00:00.000Z")),
        results._explain(artifact(fetchable=False)),
    }
    assert len(said) == 6


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
                  {"items": [artifact("node", "stepone", "0")]})

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


def test_a_finished_nodes_log_comes_from_its_logs_artifact(fake_v1, logged_in, tmp_path):
    '''🔴 `/logs` is live output only: a finished node's log is its `logs`
    artifact, a gzip tar of its log files.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("logs", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0", "ran\n")

    logged_in.node_log("j1", "stepone", "0", tmp_path / "node.log")

    assert (tmp_path / "node.log").read_text() == "ran\n"
    assert not any("/logs" in call.request.path_url for call in fake_v1.calls)


###########################
# A node archive is the rest of the run
###########################

def test_a_node_archive_displaces_what_it_contains(fake_v1, results, nop_project):
    '''🔴 A node archive IS the rest of the run, so fetching it and then fetching the
    objects inside it downloads everything twice. On a real flow that is two
    requests instead of sixty-two.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("manifest"),
        artifact("node", "stepone", "0"),
        artifact("node", "steptwo", "0"),
        artifact("logs", "stepone", "0"),
        artifact("logs", "steptwo", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None",
                  json.dumps({"schemaversion": "0.0.0"}))
    for step in ("stepone", "steptwo"):
        fake_v1.route(responses.GET, f"jobs/j1/artifacts/art-node-{step}-0",
                      tarball(["outputs/gcd.pkg.json", f"sc_{step}_0.log"]),
                      content_type="application/gzip")

    assert results.fetch("j1") == 3

    fetched = sorted(c.request.path_url for c in fake_v1.calls
                     if "/artifacts/" in c.request.path_url)
    # The two logs are inside the two node archives, so they are not asked for.
    assert fetched == ["/v1/jobs/j1/artifacts/art-manifest-None-None",
                       "/v1/jobs/j1/artifacts/art-node-stepone-0",
                       "/v1/jobs/j1/artifacts/art-node-steptwo-0"]


def test_a_node_archive_expands_in_its_own_nodes_directory(
        fake_v1, results, nop_project):
    '''Stored relative to the node's working directory, which is why the
    contract has no per-artifact path: step, index and kind are enough.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("node", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0",
                  tarball(["outputs/gcd.pkg.json", "reports/metrics.json"]),
                  content_type="application/gzip")

    results.fetch("j1")

    from siliconcompiler.utils.paths import workdir
    into = workdir(nop_project, step="stepone", index="0")
    assert os.path.isfile(os.path.join(into, "outputs", "gcd.pkg.json"))
    assert os.path.isfile(os.path.join(into, "reports", "metrics.json"))


def test_the_manifest_is_fetched_even_beside_a_node_archive(fake_v1, results):
    '''It is small, it is what the record is replayed from, and a client that
    relied on finding one inside the node archive would break on the deployment that
    indexes a manifest and no bulk output at all.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("manifest"), artifact("node", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None",
                  json.dumps({"schemaversion": "0.0.0"}))
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    assert results.fetch("j1") == 2


def test_a_node_archive_that_is_refused_displaces_nothing(fake_v1, results, caplog):
    '''🔴 A node archive is never grantable, so present-and-refused is the ordinary
    case on a deployment with approvals. Everything else must still be
    fetched, and the caller told why it could not have the node archive.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0", fetchable=False),
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
    '''🔴 Not at the end of the run. A node's node archive carries its manifest, so
    taking it as it appears is what keeps the local record -- metrics, tool
    versions, node states -- current while the rest of the flow runs on.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("node", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0",
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
                  {"items": [artifact("node", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0",
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
                  {"items": [artifact("node", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    results.take("j1", {"nodes": [{"step": "stepone", "index": "0",
                                   "state": "completed", "terminal": True}]})

    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("node", "stepone", "0")]})
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


def test_a_node_with_no_archive_is_not_asked_about_again(fake_v1, results):
    '''🔴 A node the run skipped produces no working directory, so there is
    nothing to archive and its node archive never appears. Recording only the nodes
    whose node archives were FOUND left it outstanding for ever, and this listing
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
    def archive_for(step):
        return artifact("node", step, "0")

    def node(step, terminal):
        return {"step": step, "index": "0", "terminal": terminal,
                "state": "completed" if terminal else "running"}

    # Poll 1: nothing has finished -> no listing at all.
    results.take("j1", {"nodes": [node("stepone", False)]})

    # Poll 2: two finished together -> one listing, two fetches.
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [archive_for("stepone"), archive_for("steptwo")]})
    for step in ("stepone", "steptwo"):
        fake_v1.route(responses.GET, f"jobs/j1/artifacts/art-node-{step}-0",
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


###########################
# What not to pull
###########################

def _ceiling(fake_v1, capabilities, limit):
    '''Move THIS CALLER's auto-fetch ceiling.

    🔴 On `GET /v1/me` and not `GET /v1`, because the ceiling can differ per
    account and the capabilities block carries no credential. What the
    deployment publishes is a default; what applies here is in the identity
    block.
    '''
    limits = {"concurrent_jobs": 4, "concurrent_nodes": None,
              "pending_uploads": 8, "max_job_nodes": 1000, "devices": None,
              "artifact_retention_seconds": 2592000}
    if limit is not None:
        limits["max_download_bytes"] = limit

    fake_v1.route(responses.GET, "me", {
        "id": "01J9-user", "issuer": "local", "projects": [],
        "limits": limits, "can_submit": True, "terms": [],
        "usage": {"compute_seconds": {"used": 0, "limit": None,
                                      "window": "calendar_month",
                                      "resets_at": "2026-10-01T00:00:00.000Z"},
                  "licence_seconds": {}, "storage_bytes": {"used": 0, "limit": None},
                  "concurrent_jobs": 0}})


def test_an_object_over_the_servers_ceiling_is_listed_and_not_pulled(
        fake_v1, capabilities, results, caplog):
    '''🔴 The SERVER's number, not the client's. A deployment knows what its
    link and its disks are for; a client picking its own threshold means every
    client picks a different one and the operator sets no policy at all.'''
    _ceiling(fake_v1, capabilities, 1000)
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0", size_bytes=50_000_000,
                 media_type="application/gzip")]})

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 0

    assert "left on the server" in caplog.text
    assert "47.7 MiB" in caplog.text
    # It named the ceiling too, so the number is not a mystery.
    assert "1000 B" in caplog.text


def test_what_went_in_is_neither_taken_nor_reported_left_behind(
        fake_v1, capabilities, results, caplog):
    '''`input` is the upload and a node's inputs: this machine has the one
    and takes the other as its upstream's outputs. Over the ceiling, saying it
    was left on the server would be a warning about nothing.'''
    _ceiling(fake_v1, capabilities, 1000)
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("input", size_bytes=50_000_000, media_type="application/gzip"),
        artifact("input", "stepone", "0", size_bytes=50_000_000,
                 media_type="application/gzip"),
        artifact("manifest")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None",
                  json.dumps({"schemaversion": "0.0.0"}))

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 1

    assert "left on the server" not in caplog.text
    assert not any("art-input" in call.request.url for call in fake_v1.calls)


def test_a_node_archive_left_behind_does_not_displace_its_nodes_log(
        fake_v1, capabilities, results, nop_project):
    '''🔴 A node archive displaces the objects inside it only because fetching it
    gets you them. One that is not being fetched displaces nothing -- which is
    the case this ceiling exists to produce.'''
    _ceiling(fake_v1, capabilities, 1000)
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0", size_bytes=50_000_000,
                 media_type="application/gzip"),
        artifact("logs", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0",
                  body="stepone ran\n", content_type="text/plain")

    assert results.fetch("j1") == 1

    from siliconcompiler.utils.paths import workdir
    landed = os.path.join(workdir(nop_project, step="stepone", index="0"),
                          "sc_stepone_0.log")
    assert "stepone ran" in open(landed).read()


def test_a_server_that_publishes_no_ceiling_fetches_everything(
        fake_v1, capabilities, results):
    '''A client that has never heard of the limit, or a server older than it,
    behaves exactly as before.'''
    _ceiling(fake_v1, capabilities, None)
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("logs", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0",
                  body="big\n", content_type="text/plain")

    assert results.fetch("j1") == 1


###########################
# A node's manifest, where its archive is withheld
###########################

def _finished(step="stepone"):
    return {"nodes": [{"step": step, "index": "0", "state": "completed",
                       "terminal": True}]}


def test_a_nodes_manifest_is_taken_where_its_archive_is_withheld(
        fake_v1, results, nop_project):
    '''🔴 A deployment that hands over manifests and no bulk output still
    hands over the half that says what happened -- and taking it as the node
    finishes is what fills the dashboard's time, warnings and errors while the
    rest of the run goes on.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0", fetchable=False),
        artifact("manifest", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-stepone-0", "{}")

    assert results.take("j1", _finished()) == 1

    from siliconcompiler.utils.paths import workdir
    assert os.path.isfile(os.path.join(
        workdir(nop_project, step="stepone", index="0"), "outputs", "gcd.pkg.json"))


def test_a_nodes_log_and_reports_are_taken_as_it_finishes_too(
        fake_v1, results, nop_project):
    '''Where the archive is withheld, everything else of the node's that may
    be had comes as the node finishes -- not at the end of the run.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0", fetchable=False),
        artifact("manifest", "stepone", "0"),
        artifact("logs", "stepone", "0"),
        artifact("reports", "stepone", "0"),
        # The run's own: not final until the run is.
        artifact("logs"), artifact("manifest")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-stepone-0", "{}")
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0", "ran\n")
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-reports-stepone-0",
                  tarball(["reports/metrics.json"]), content_type="application/gzip")

    assert results.take("j1", _finished()) == 3

    from siliconcompiler.utils.paths import workdir
    into = workdir(nop_project, step="stepone", index="0")
    assert open(os.path.join(into, "sc_stepone_0.log")).read() == "ran\n"
    assert os.path.isfile(os.path.join(into, "reports", "metrics.json"))

    fetched = {c.request.path_url for c in fake_v1.calls
               if "/artifacts/art-" in c.request.path_url}
    assert "/v1/jobs/j1/artifacts/art-logs-None-None" not in fetched
    assert "/v1/jobs/j1/artifacts/art-manifest-None-None" not in fetched


def test_a_nodes_manifest_is_not_fetched_beside_its_archive(fake_v1, results):
    '''The archive holds them, so fetching both downloads them twice.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0"), artifact("manifest", "stepone", "0"),
        artifact("logs", "stepone", "0"), artifact("reports", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0",
                  tarball(["outputs/gcd.pkg.json"]),
                  content_type="application/gzip")

    assert results.take("j1", _finished()) == 1

    fetched = [c.request.path_url for c in fake_v1.calls
               if "/artifacts/art-" in c.request.path_url]
    assert fetched == ["/v1/jobs/j1/artifacts/art-node-stepone-0"]


def test_an_archive_too_large_to_fetch_does_not_displace_the_manifest(
        fake_v1, results):
    '''🔴 An archive that will not be fetched covers nothing -- otherwise the
    node's record is lost to the size of its outputs.'''
    results._ceiling = 10
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("node", "stepone", "0", size_bytes=1000),
        artifact("manifest", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-stepone-0", "{}")

    assert results.take("j1", _finished()) == 1


def test_the_job_manifest_fills_in_what_every_node_did(fake_v1, results,
                                                       nop_project):
    '''🔴 The job manifest is the run's final state written whole, and it has
    no journal -- so replaying it found nothing, and a listing holding only
    that manifest came back with every node's time, warnings and errors
    blank. Its per-node values are copied instead.'''
    from siliconcompiler import Project

    nop_project.write_manifest("final.pkg.json")
    final = Project.from_manifest(filepath="final.pkg.json")
    final.set("metric", "warnings", 7, step="stepone", index="0")
    final.set("metric", "tasktime", 12.5, step="stepone", index="0")
    final.set("record", "status", "success", step="stepone", index="0")
    # A global value is the server's setting for the run, not the caller's.
    final.set("option", "jobname", "servers-own")
    final.write_manifest("final.pkg.json")

    with open("final.pkg.json") as f:
        body = f.read()
    assert "__journal__" not in json.loads(body)

    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [artifact("manifest")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-None-None", body)

    assert nop_project.get("metric", "warnings", step="stepone", index="0") is None

    results.fetch("j1")

    assert nop_project.get("metric", "warnings", step="stepone", index="0") == 7
    assert nop_project.get("metric", "tasktime", step="stepone", index="0") == 12.5
    assert nop_project.get("record", "status", step="stepone", index="0") == "success"
    assert nop_project.option.get_jobname() == "job0"


def test_a_run_from_part_way_folds_in_only_the_nodes_it_ran(results, nop_project):
    '''🔴 The run marks every node it did not load as pending, with its metrics
    cleared: folded in whole, a node that finished before would look unrun
    here.'''
    from siliconcompiler import Project

    nop_project.set("record", "status", "success", step="stepone", index="0")
    nop_project.set("metric", "tasktime", 3.0, step="stepone", index="0")
    nop_project.option.add_from("steptwo")

    nop_project.write_manifest("final.pkg.json")
    final = Project.from_manifest(filepath="final.pkg.json")
    final.set("record", "status", "pending", step="stepone", index="0")
    final.unset("metric", "tasktime", step="stepone", index="0")
    final.set("record", "status", "success", step="steptwo", index="0")
    final.set("metric", "tasktime", 9.0, step="steptwo", index="0")
    final.write_manifest("final.pkg.json")

    results._fold_in_final("final.pkg.json")

    assert nop_project.get("record", "status", step="stepone", index="0") == "success"
    assert nop_project.get("metric", "tasktime", step="stepone", index="0") == 3.0
    assert nop_project.get("record", "status", step="steptwo", index="0") == "success"
    assert nop_project.get("metric", "tasktime", step="steptwo", index="0") == 9.0


def test_a_continued_nodes_results_come_from_the_job_that_ran_it(fake_v1, results):
    '''What is fetchable now of that one node of the other job: a caller
    approved since then gets the files.'''
    fake_v1.route(responses.GET, "jobs/earlier/artifacts", {"items": [
        artifact("manifest", "stepone", "0"),
        artifact("manifest", "steptwo", "0")]})
    fake_v1.route(responses.GET, "jobs/earlier/artifacts/art-manifest-stepone-0", "{}")

    assert results.fetch_node("earlier", "stepone", "0") == 1

    fetched = [c.request.path_url for c in fake_v1.calls if "/artifacts/art-" in c.request.path_url]
    assert fetched == ["/v1/jobs/earlier/artifacts/art-manifest-stepone-0"]


def test_the_upload_manifest_is_never_folded_back_in(results, nop_project):
    '''Until the server's copy arrives, the file at that path is the one this
    client wrote to upload -- the pre-run record -- and folding it in would
    put that over what the nodes have since said.'''
    from siliconcompiler.utils.paths import jobdir

    os.makedirs(jobdir(nop_project), exist_ok=True)
    nop_project.write_manifest(os.path.join(jobdir(nop_project), "gcd.pkg.json"))
    nop_project.set("metric", "warnings", 3, step="stepone", index="0")

    results._replay()

    assert nop_project.get("metric", "warnings", step="stepone", index="0") == 3


###########################
# Said once per reason
###########################

def test_what_is_withheld_for_one_reason_is_said_once(fake_v1, results, caplog):
    '''⚠️ A deployment that hands over only manifests withholds three objects
    per node. One line per object is seventy lines of the same sentence, and
    the one that differs goes unread.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact(kind, step, "0", fetchable=False)
        for step in ("stepone", "steptwo") for kind in ("logs", "reports", "node")
    ] + [artifact("outputs", "stepone", "0", fetchable=False,
                  deleted_at="2026-09-20T00:00:00.000Z",
                  deleted_cause="removed", deleted_reason=None)]})

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    lines = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert len(lines) == 2
    assert "6 objects (logs x2, reports x2, node x2): you may not have these" in lines[0]
    # The one that differs keeps its own line and its own name.
    assert lines[1] == "outputs for stepone/0: deleted on 2026-09-20."


def test_a_row_for_a_node_the_flow_does_not_have_writes_nothing(fake_v1, results, tmp_path):
    '''🔴 `step: ".."` included: writes stay in the job's local directory.'''
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("outputs", "..", "0"), artifact("outputs", "elsewhere", "0")]})

    assert results.fetch("j1") == 0
    assert not any("/artifacts/art-" in call.request.path_url for call in fake_v1.calls)


def test_bytes_that_do_not_match_the_listing_are_discarded(fake_v1, results, nop_project,
                                                           caplog):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("manifest", "stepone", "0", size_bytes=3, digest="sha256:" + "0" * 64)]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-manifest-stepone-0", "{}")

    assert results.fetch("j1") == 0

    from siliconcompiler.utils.paths import workdir
    assert not os.path.exists(os.path.join(workdir(nop_project, step="stepone", index="0"),
                                           "outputs", "gcd.pkg.json"))
    assert "did not match" in caplog.text


def test_a_returned_manifest_imports_nothing_and_sets_no_job_id(results, nop_project):
    '''🔴 Read as data: a class it names that is not loaded here resolves to
    its base type, and its `record,remoteid` is never the job id.'''
    import sys

    nop_project.set("record", "remoteid", "the-real-job")
    nop_project.write_manifest("final.pkg.json")
    with open("final.pkg.json") as f:
        body = json.load(f)
    body["__meta__"]["class"] = "planted_module_never_imported/Evil"
    body["record"]["remoteid"]["node"]["stepone"] = {"0": {"value": "planted", "signature": None}}
    with open("final.pkg.json", "w") as f:
        json.dump(body, f)

    results._fold_in_final("final.pkg.json")

    assert "planted_module_never_imported" not in sys.modules
    assert nop_project.get("record", "remoteid") == "the-real-job"


def test_final_is_fetched(fake_v1, results):
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        artifact("final", "stepone", "0"), artifact("node", "stepone", "0")]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-final-stepone-0",
                  tarball(["outputs/gcd.v"]))
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-node-stepone-0", tarball(["x.json"]))

    assert results.fetch("j1") == 2


###########################
# A node archive is not self-contained (client-v1-migration.md)
###########################

def linked_tarball(members):
    '''A node archive as `sc-server` now produces one: ``(name, bytes)`` for a
    file, ``(name, "->", target)`` for a symlink, ``(name, "=>", first)`` for a
    tar hard link.'''
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for entry in members:
            info = tarfile.TarInfo(entry[0])
            if len(entry) == 3:
                info.type = tarfile.SYMTYPE if entry[1] == "->" else tarfile.LNKTYPE
                info.linkname = entry[2]
                tar.addfile(info)
            else:
                info.size = len(entry[1])
                tar.addfile(info, io.BytesIO(entry[1]))
    return buffer.getvalue()


def serve_nodes(fake_v1, archives):
    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  {"items": [artifact("node", step, "0") for step in archives]})
    for step, body in archives.items():
        fake_v1.route(responses.GET, f"jobs/j1/artifacts/art-node-{step}-0", body,
                      content_type="application/gzip")


@pytest.mark.parametrize("fallback", [False, True], ids=["data-filter", "fallback"])
def test_a_link_into_a_sibling_nodes_outputs_extracts_inside_the_job(
        fake_v1, results, nop_project, monkeypatch, fallback):
    '''A passed-through file is a link to the node that produced it, and a
    hard-linked pair is one file: both land inside the job's local directory,
    and resolve once the home node is there.'''
    from siliconcompiler import utils
    from siliconcompiler.utils.paths import workdir

    if fallback:
        monkeypatch.setattr(utils, "tar_extract_kwargs", lambda: {})
    serve_nodes(fake_v1, {
        "stepone": linked_tarball([("outputs/gcd.vg", b"module gcd; endmodule\n")]),
        "steptwo": linked_tarball([
            ("outputs/gcd.vg", "->", "../../../stepone/0/outputs/gcd.vg"),
            ("outputs/a.v", b"module a; endmodule\n"),
            ("outputs/b.v", "=>", "outputs/a.v")])})

    results.fetch("j1")

    two = workdir(nop_project, step="steptwo", index="0")
    passed = os.path.join(two, "outputs", "gcd.vg")
    assert os.path.islink(passed)
    with open(passed) as f:
        assert f.read() == "module gcd; endmodule\n"
    assert os.path.samefile(os.path.join(two, "outputs", "a.v"),
                            os.path.join(two, "outputs", "b.v"))


@pytest.mark.parametrize("fallback", [False, True], ids=["data-filter", "fallback"])
def test_a_link_out_of_the_job_is_refused(fake_v1, results, nop_project, monkeypatch,
                                          fallback, caplog):
    from siliconcompiler import utils
    from siliconcompiler.utils.paths import workdir

    if fallback:
        monkeypatch.setattr(utils, "tar_extract_kwargs", lambda: {})
    serve_nodes(fake_v1, {"steptwo": linked_tarball([
        ("outputs/stolen", "->", "../../../../../../../../etc/passwd")])})

    results.fetch("j1")

    two = workdir(nop_project, step="steptwo", index="0")
    assert not os.path.lexists(os.path.join(two, "outputs", "stolen"))
