import io
import json
import os
import tarfile

import pytest
import responses

from siliconcompiler.remote.client.results import Results
from siliconcompiler.remote.runflow import runtime_nodes
from siliconcompiler.utils.paths import jobdir, workdir

from conftest import problem


# What the integration rig cannot reach: `blocked_by`, a proxy's HTML 502, and
# each not-fetchable case's sentence.


def artifact(kind="manifest", step=None, index=None, fetchable=True, **extra):
    return {"id": f"art-{kind}-{step}-{index}", "step": step, "index": index, "kind": kind,
            "media_type": "application/json" if kind == "manifest" else "text/plain",
            "created_at": "2026-09-22T10:00:00.000Z",
            "retained_until": "2031-09-22T10:00:00.000Z",
            "deleted_at": None, "deleted_cause": None, "deleted_reason": None,
            "fetchable": fetchable, "can_request_access": False, **extra}


def tarball(members):
    '''A gzip tar: a bare ``name`` holds ``{}``; ``(name, bytes)`` is a file,
    ``(name, "->", target)`` a symlink, ``(name, "=>", first)`` a hard link.'''
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for entry in members:
            entry = (entry, b"{}") if isinstance(entry, str) else entry
            info = tarfile.TarInfo(entry[0])
            if len(entry) == 3:
                info.type = tarfile.SYMTYPE if entry[1] == "->" else tarfile.LNKTYPE
                info.linkname = entry[2]
                tar.addfile(info)
            else:
                info.size = len(entry[1])
                tar.addfile(info, io.BytesIO(entry[1]))
    return buffer.getvalue()


@pytest.fixture
def fake_v1(fake_v1):
    '''Serves each artifact as the v1 API stores it: gzipped, and a node's
    `logs` as a gzip tar of its log files. A test routes the plain bytes.'''
    import gzip
    import re

    route = fake_v1.route

    def served(method, path, body, *args, **kwargs):
        found = re.search(r"/artifacts/art-(\w+)-(\w+)-(\w+)$", path)
        if found and isinstance(body, (str, bytes)) and kwargs.get("status", 200) < 300:
            kind, step, index = found.groups()
            data = body.encode() if isinstance(body, str) else body
            if kind == "logs" and step != "None":
                data = tarball([(f"sc_{step}_{index}.log", data)])
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


def serve(fake_v1, items, bodies=None, job="j1"):
    '''List ``items`` for ``job``, and answer each of ``bodies``, keyed by
    artifact id less its ``art-`` prefix.'''
    fake_v1.route(responses.GET, f"jobs/{job}/artifacts", {"items": items})
    for name, body in (bodies or {}).items():
        fake_v1.route(responses.GET, f"jobs/{job}/artifacts/art-{name}", body)


def fetched(fake_v1):
    '''The path of every artifact download, in order.'''
    return [c.request.path_url for c in fake_v1.calls
            if "/artifacts/art-" in c.request.path_url]


def listings(fake_v1):
    return [c for c in fake_v1.calls
            if "artifacts" in c.request.path_url and "/artifacts/" not in c.request.path_url]


def finished(*steps, running=()):
    return {"nodes": [{"step": step, "index": "0", "state": "completed", "terminal": True}
                      for step in steps]
            + [{"step": step, "index": "0", "state": "running", "terminal": False}
               for step in running]}


def landed(project, step, *path):
    return os.path.isfile(os.path.join(workdir(project, step=step, index="0"), *path))


def test_a_manifest_alone_is_a_successful_run_and_fills_in_every_node(
        fake_v1, results, nop_project, caplog):
    '''The manifest carries the record. Having no journal, its per-node
    values are copied; a global one, the server's setting, is not.'''
    from siliconcompiler import Project

    nop_project.write_manifest("final.pkg.json")
    final = Project.from_manifest(filepath="final.pkg.json")
    final.set("metric", "warnings", 7, step="stepone", index="0")
    final.set("metric", "tasktime", 12.5, step="stepone", index="0")
    final.set("record", "status", "success", step="stepone", index="0")
    final.set("option", "jobname", "servers-own")
    final.write_manifest("final.pkg.json")

    with open("final.pkg.json") as f:
        body = f.read()
    assert "__journal__" not in json.loads(body)

    serve(fake_v1, [artifact("manifest")], {"manifest-None-None": body})
    assert nop_project.get("metric", "warnings", step="stepone", index="0") is None

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 1

    assert "could not" not in caplog.text.lower()
    assert os.path.isfile(os.path.join(jobdir(nop_project), "gcd.pkg.json"))
    assert nop_project.get("metric", "warnings", step="stepone", index="0") == 7
    assert nop_project.get("metric", "tasktime", step="stepone", index="0") == 12.5
    assert nop_project.get("record", "status", step="stepone", index="0") == "success"
    assert nop_project.option.get_jobname() == "job0"


def test_an_empty_listing_is_legal(fake_v1, results, caplog):
    '''No bulk output, no pipeline here, or retention took it all: no error.'''
    serve(fake_v1, [])
    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 0
    assert "kept nothing" in caplog.text
    assert "not an error" in caplog.text


def test_a_refused_archive_and_no_manifest_still_fetch_the_rest(fake_v1, results, caplog):
    '''A node archive is never grantable: the rest is fetched, and no
    manifest is not a failure. (`/v1/me` here publishes no ceiling.)'''
    ceiling(fake_v1, None)
    serve(fake_v1, [artifact("node", "stepone", "0", fetchable=False),
                    artifact("logs", "stepone", "0")],
          {"logs-stepone-0": "ran\n"})

    with caplog.at_level("INFO"):
        assert results.fetch("j1") == 1

    assert "may not have this" in caplog.text
    assert "does not keep those" in caplog.text
    assert "nothing to retry" in caplog.text


def test_the_five_states_are_different_sentences(results):
    '''Deleted before expiry; only `deleted_cause: expired` is the reaper,
    an unknown cause is somebody deciding; a reason is repeated verbatim.'''
    def why(**case):
        return results._why(artifact(fetchable=False, **case))

    at = dict(deleted_at="2026-09-20T00:00:00.000Z")
    assert why(deleted_cause="removed", expires_at="2020-01-01T00:00:00.000Z", **at) == \
        "deleted on 2026-09-20."
    assert why(deleted_cause="legal", **at) == "deleted on 2026-09-20."
    assert why(deleted_cause="removed", deleted_reason="superseded by the rerun", **at) == \
        "deleted on 2026-09-20 -- superseded by the rerun."
    expired = why(deleted_cause="expired", **at)
    assert expired.startswith("aged out on 2026-09-20.") and "deleted" not in expired

    said = {why(**case) for case in (
        dict(deleted_cause="removed", **at), dict(deleted_cause="expired", **at),
        dict(blocked_by=["nda"]), dict(can_request_access=True),
        dict(can_request_access=True, access_requested_at="2026-09-20T00:00:00.000Z"),
        dict())}
    assert len(said) == 6


def test_blocked_by_names_each_document_by_its_title(fake_v1, results, caplog):
    '''*Sign*: each `terms` id by its title from GET /v1/me, or by its
    id where it has none -- and no link is invented.'''
    fake_v1.route(responses.GET, "me", {"id": "u1", "terms": [
        {"id": "gf22-nda", "title": "GF22 non-disclosure agreement", "can_decide": True}]})
    serve(fake_v1, [artifact("final", "stepone", "0", fetchable=False,
                             blocked_by=["gf22-nda", "gf22-export"])])
    caplog.set_level("WARNING")
    results.fetch("j1")
    assert "sign GF22 non-disclosure agreement" in caplog.text
    assert "sign gf22-export" in caplog.text
    assert "http" not in caplog.text


@pytest.mark.parametrize("terminal", [False, True])
def test_an_approval_is_asked_for_and_opened_only_on_a_terminal_yes(
        fake_v1, results, monkeypatch, caplog, terminal):
    '''*Ask* names no URL. On a terminal: one question, then endpoint 6's page
    for each askable object by id -- none for one already requested.'''
    from siliconcompiler.remote import client as client_module

    if terminal:
        for stream in ("stdin", "stdout"):
            monkeypatch.setattr(f"sys.{stream}.isatty", lambda: True)
        monkeypatch.delenv("CI", raising=False)
    opened, asked = [], []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(client_module, "_ask", lambda question: asked.append(question) or "y")
    fake_v1.route(responses.POST, "auth/browser",
                  {"url": "https://portal.test/enter?token=a", "expires_at": None})
    serve(fake_v1, [
        artifact("final", "stepone", "0", fetchable=False, can_request_access=True),
        artifact("final", "steptwo", "0", fetchable=False, can_request_access=True,
                 access_requested_at="2026-09-21T10:00:00.000Z")])

    caplog.set_level("WARNING")
    results.fetch("j1")

    assert "needs an approval. Ask for access on its page" in caplog.text
    assert "requested on 2026-09-21" in caplog.text
    pages = [json.loads(c.request.body) for c in fake_v1.calls
             if c.request.url.endswith("/v1/auth/browser")]
    assert pages == ([{"artifact_id": "art-final-stepone-0"}] if terminal else [])
    assert opened == (["https://portal.test/enter?token=a"] if terminal else [])
    assert len(asked) == int(terminal)


def test_a_not_fetchable_artifact_is_never_fetched(fake_v1, results, caplog):
    '''`fetchable: false` is the answer and nothing is fetched to find
    out; ungranted with no way to yes says asking will not help.'''
    serve(fake_v1, [
        artifact("node", "stepone", "0", fetchable=False),
        artifact("node", "steptwo", "0", fetchable=False, can_request_access=True)])
    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 0
    assert not fetched(fake_v1)
    assert "may not have this" in caplog.text
    assert "not something asking would change" in caplog.text


def test_no_fetch_once_probe_remains():
    '''Follow-on 23's probe, removed: *listed* means describable.'''
    from siliconcompiler.remote.client import results as module
    for name in ("_fetch_once", "_names_no_way", "NOT_READY_ASKS"):
        assert not hasattr(module, name) and not hasattr(module.Results, name), name


def test_only_what_landed_is_counted_as_retrieved(fake_v1, results, caplog):
    '''A kind with no home here -- job-level or node-bound -- writes nothing,
    and is not "retrieved".'''
    serve(fake_v1, [artifact("manifest"), artifact("reports"),
                    artifact("unheardof", "stepone", "0")],
          {"manifest-None-None": "{}"})
    with caplog.at_level("INFO"):
        assert results.fetch("j1") == 1
    assert "Retrieved 1 objects" in caplog.text
    assert "/v1/jobs/j1/artifacts/art-unheardof-stepone-0" not in fetched(fake_v1)


@pytest.mark.parametrize("kind", ["outputs", "node"])
def test_an_archive_lands_in_the_nodes_own_directory(fake_v1, results, nop_project, kind):
    '''Stored relative to the node's directory: step, index and kind are enough.'''
    serve(fake_v1, [artifact(kind, "stepone", "0")],
          {f"{kind}-stepone-0": tarball(["outputs/gcd.pkg.json", "reports/metrics.json"])})
    results.fetch("j1")
    assert landed(nop_project, "stepone", "outputs", "gcd.pkg.json")
    assert landed(nop_project, "stepone", "reports", "metrics.json")


def test_one_objects_failure_does_not_abort_the_others(fake_v1, results,
                                                       nop_project, caplog):
    '''B4: one node's failure must not cost the caller the rest of the run.'''
    serve(fake_v1, [artifact("logs", "stepone", "0"), artifact("logs", "steptwo", "0")],
          {"logs-steptwo-0": "ran\n"})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/art-logs-stepone-0",
                  problem("not-found", 404), status=404,
                  content_type="application/problem+json")
    with caplog.at_level("ERROR"):
        assert results.fetch("j1") == 1
    assert landed(nop_project, "steptwo", "sc_steptwo_0.log")


def test_a_node_archive_displaces_what_it_contains(fake_v1, results):
    '''Fetching a node archive and the objects inside it downloads twice. The
    job manifest is still fetched beside it, and so is `final`.'''
    serve(fake_v1, [artifact("manifest"),
                    artifact("node", "stepone", "0"), artifact("node", "steptwo", "0"),
                    artifact("logs", "stepone", "0"), artifact("logs", "steptwo", "0"),
                    artifact("final", "stepone", "0")],
          {"manifest-None-None": json.dumps({"schemaversion": "0.0.0"}),
           "final-stepone-0": tarball(["outputs/gcd.v"]),
           **{f"node-{step}-0": tarball(["outputs/gcd.pkg.json", f"sc_{step}_0.log"])
              for step in ("stepone", "steptwo")}})

    assert results.fetch("j1") == 4

    assert sorted(fetched(fake_v1)) == ["/v1/jobs/j1/artifacts/art-final-stepone-0",
                                        "/v1/jobs/j1/artifacts/art-manifest-None-None",
                                        "/v1/jobs/j1/artifacts/art-node-stepone-0",
                                        "/v1/jobs/j1/artifacts/art-node-steptwo-0"]


def test_the_job_level_log_lands_beside_the_nodes_not_on_top_of_job_log(
        fake_v1, results, nop_project):
    '''A remote run is a `Scheduler` run, so `job.log` is open for the whole
    run: downloading onto it truncates a file this process is writing.'''
    serve(fake_v1, [artifact("logs", media_type="text/plain")],
          {"logs-None-None": "RuntimeError: git is required\n"})

    here = jobdir(nop_project)
    os.makedirs(here, exist_ok=True)
    with open(os.path.join(here, "job.log"), "w") as local:
        local.write("what this process logged\n")

    assert results.fetch("j1") == 1

    assert open(os.path.join(here, "job.log")).read() == "what this process logged\n"
    assert "git is required" in open(os.path.join(here, "remote-job.log")).read()


def test_the_advice_names_the_file_the_client_actually_writes():
    '''Rendered in errors, written in results: only this keeps them in step.'''
    from siliconcompiler.remote.client.errors import NO_NODE_FAILED
    from siliconcompiler.remote.client.results import REMOTE_JOB_LOG
    assert REMOTE_JOB_LOG in NO_NODE_FAILED


def test_a_proxys_html_502_on_the_listing_is_rendered_and_not_fatal_mid_run(fake_v1,
                                                                            results):
    '''problem+json is promised only for what a handler produced. Mid-run,
    nothing is lost: the sweep at the end asks again.'''
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.GET, "jobs/j1/artifacts",
                  "<html><body><h1>502 Bad Gateway</h1></body></html>",
                  status=502, content_type="text/html")

    assert results.take("j1", finished("stepone")) == 0
    with pytest.raises(ServerProblem) as raised:
        results.fetch("j1")

    assert "502" in str(raised.value)
    assert raised.value.slug is None


def test_a_half_written_download_is_never_left_behind(fake_v1, logged_in, tmp_path):
    '''A half-file in the build directory would be read as real by the next step.'''
    import unittest.mock as mock
    fake_v1.route(responses.GET, "jobs/j1/artifacts/a1", "x" * 100)
    target = tmp_path / "thing.json"
    with mock.patch("shutil.copyfileobj", side_effect=OSError("cut off")):
        with pytest.raises(OSError):
            logged_in.fetch_artifact("j1", "a1", target)
    assert not target.exists()
    assert not (tmp_path / "thing.json.part").exists()


def test_a_finished_nodes_log_comes_from_its_logs_artifact(fake_v1, logged_in, tmp_path):
    '''`/logs` is live output only: a finished node's log is its `logs` artifact.'''
    serve(fake_v1, [artifact("logs", "stepone", "0")], {"logs-stepone-0": "ran\n"})
    logged_in.node_log("j1", "stepone", "0", tmp_path / "node.log")
    assert (tmp_path / "node.log").read_text() == "ran\n"
    assert not any("/logs" in call.request.path_url for call in fake_v1.calls)


def test_a_nodes_results_are_taken_when_it_finishes_and_not_again_by_the_sweep(
        fake_v1, results, nop_project):
    '''As each node finishes, so the local record stays current; the final
    sweep does not fetch it again.'''
    serve(fake_v1, [artifact("node", "stepone", "0")],
          {"node-stepone-0": tarball(["outputs/gcd.pkg.json"])})
    assert results.take("j1", finished("stepone", running=["steptwo"])) == 1
    assert landed(nop_project, "stepone", "outputs", "gcd.pkg.json")
    assert results.fetch("j1") == 0
    assert len(fetched(fake_v1)) == 1


def test_a_node_with_no_archive_is_not_asked_about_again(fake_v1, results):
    '''A skipped node never has an archive: recording only nodes whose
    archive was FOUND listed again on every poll, per client.'''
    job = {"nodes": [{"step": "stepone", "index": "0", "state": "skipped",
                      "terminal": True}]}
    for _ in range(4):
        serve(fake_v1, [])
        results.take("j1", job)
    assert len(listings(fake_v1)) == 1


def test_one_listing_per_batch_of_finished_nodes(fake_v1, results):
    '''Not one per poll, nor one per node; a quiet poll asks nothing, and a node is taken once.'''
    results.take("j1", finished(running=["stepone"]))
    serve(fake_v1, [artifact("node", "stepone", "0"), artifact("node", "steptwo", "0")],
          {f"node-{step}-0": tarball(["outputs/gcd.pkg.json"])
           for step in ("stepone", "steptwo")})
    assert results.take("j1", finished("stepone", "steptwo")) == 2
    assert results.take("j1", finished("stepone", "steptwo")) == 0
    assert len(listings(fake_v1)) == 1
    assert len(fetched(fake_v1)) == 2


def ceiling(fake_v1, limit):
    '''THIS caller's ceiling, on `GET /v1/me`: it can differ per account.'''
    limits = {} if limit is None else {"max_download_bytes": limit}
    fake_v1.route(responses.GET, "me", {"id": "01J9-user", "terms": [], "limits": limits})


def test_over_the_servers_ceiling_is_left_and_displaces_nothing(
        fake_v1, results, nop_project, caplog):
    '''The SERVER's number, named once. An archive left behind displaces
    nothing; `input` is neither taken nor reported.'''
    ceiling(fake_v1, 1000)
    serve(fake_v1, [
        artifact("input", size_bytes=50_000_000, media_type="application/gzip"),
        artifact("input", "stepone", "0", size_bytes=50_000_000,
                 media_type="application/gzip"),
        artifact("node", "stepone", "0", size_bytes=50_000_000,
                 media_type="application/gzip"),
        artifact("logs", "stepone", "0")],
        {"logs-stepone-0": "stepone ran\n"})

    with caplog.at_level("WARNING"):
        assert results.fetch("j1") == 1

    assert "1 object(s) were left on the server (47.7 MiB)" in caplog.text
    assert "1000 B" in caplog.text
    assert "input" not in caplog.text
    assert not any("art-input" in call.request.url for call in fake_v1.calls)
    assert landed(nop_project, "stepone", "sc_stepone_0.log")


def test_a_nodes_manifest_log_and_reports_are_taken_where_its_archive_is_withheld(
        fake_v1, results, nop_project):
    '''As the node finishes, not at the end; the job's own log and manifest
    are not final until the run is.'''
    serve(fake_v1, [
        artifact("node", "stepone", "0", fetchable=False),
        artifact("manifest", "stepone", "0"),
        artifact("logs", "stepone", "0"),
        artifact("reports", "stepone", "0"),
        artifact("logs"), artifact("manifest")],
        {"manifest-stepone-0": "{}", "logs-stepone-0": "ran\n",
         "reports-stepone-0": tarball(["reports/metrics.json"])})

    assert results.take("j1", finished("stepone")) == 3

    into = workdir(nop_project, step="stepone", index="0")
    assert open(os.path.join(into, "sc_stepone_0.log")).read() == "ran\n"
    assert landed(nop_project, "stepone", "reports", "metrics.json")
    assert landed(nop_project, "stepone", "outputs", "gcd.pkg.json")
    assert "/v1/jobs/j1/artifacts/art-logs-None-None" not in fetched(fake_v1)
    assert "/v1/jobs/j1/artifacts/art-manifest-None-None" not in fetched(fake_v1)


@pytest.mark.parametrize("limit,taken", [
    (None, ["node"]),
    # An archive too large to fetch covers nothing, or the node's record is
    # lost to the size of its outputs.
    (10, ["manifest", "logs", "reports"])], ids=["fetched", "too-large"])
def test_a_nodes_archive_displaces_its_manifest_log_and_reports_only_if_fetched(
        fake_v1, results, limit, taken):
    results._ceiling = limit
    node = tarball(["outputs/gcd.pkg.json"])
    serve(fake_v1, [artifact("node", "stepone", "0", size_bytes=len(node))]
          + [artifact(kind, "stepone", "0") for kind in ("manifest", "logs", "reports")],
          {"node-stepone-0": node, "manifest-stepone-0": "{}", "logs-stepone-0": "ran\n",
           "reports-stepone-0": tarball(["reports/metrics.json"])})
    assert results.take("j1", finished("stepone")) == len(taken)
    assert fetched(fake_v1) == [f"/v1/jobs/j1/artifacts/art-{kind}-stepone-0" for kind in taken]


def test_a_continued_nodes_results_come_from_the_job_that_ran_it(fake_v1, results):
    '''Only that node of the other job, as fetchable now.'''
    serve(fake_v1, [artifact("manifest", "stepone", "0"), artifact("manifest", "steptwo", "0")],
          {"manifest-stepone-0": "{}"}, job="earlier")
    assert results.fetch_node("earlier", "stepone", "0") == 1
    assert fetched(fake_v1) == ["/v1/jobs/earlier/artifacts/art-manifest-stepone-0"]


def test_the_upload_manifest_is_never_folded_back_in(results, nop_project):
    '''Until the server's copy arrives that file is the pre-run record.'''
    os.makedirs(jobdir(nop_project), exist_ok=True)
    nop_project.write_manifest(os.path.join(jobdir(nop_project), "gcd.pkg.json"))
    nop_project.set("metric", "warnings", 3, step="stepone", index="0")
    results._replay()
    assert nop_project.get("metric", "warnings", step="stepone", index="0") == 3


def test_what_is_withheld_for_one_reason_is_said_once(fake_v1, results, caplog):
    '''One line per object buries the one that differs, which keeps its own.'''
    serve(fake_v1, [artifact(kind, step, "0", fetchable=False)
                    for step in ("stepone", "steptwo") for kind in ("logs", "reports", "node")]
          + [artifact("outputs", "stepone", "0", fetchable=False,
                      deleted_at="2026-09-20T00:00:00.000Z", deleted_cause="removed")])

    with caplog.at_level("WARNING"):
        results.fetch("j1")

    lines = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert len(lines) == 2
    assert "6 objects (logs x2, reports x2, node x2): you may not have these" in lines[0]
    assert lines[1] == "outputs for stepone/0: deleted on 2026-09-20."


def test_a_row_for_a_node_the_flow_does_not_have_writes_nothing(fake_v1, results):
    '''`step: ".."` included: writes stay in the job's local directory.'''
    serve(fake_v1, [artifact("outputs", "..", "0"), artifact("outputs", "elsewhere", "0")])
    assert results.fetch("j1") == 0
    assert not fetched(fake_v1)


def test_bytes_that_do_not_match_the_listing_are_discarded(fake_v1, results, nop_project,
                                                           caplog):
    serve(fake_v1, [artifact("manifest", "stepone", "0", size_bytes=3,
                             digest="sha256:" + "0" * 64)],
          {"manifest-stepone-0": "{}"})
    assert results.fetch("j1") == 0
    assert not landed(nop_project, "stepone", "outputs", "gcd.pkg.json")
    assert "did not match" in caplog.text


def test_a_returned_manifest_folds_in_only_the_nodes_it_ran_as_data(results, nop_project):
    '''A run from part-way returns unloaded nodes pending. Read as data: an
    unloaded class is its base type; `record,remoteid` is never the job id.'''
    import sys

    from siliconcompiler import Project

    nop_project.set("record", "status", "success", step="stepone", index="0")
    nop_project.set("metric", "tasktime", 3.0, step="stepone", index="0")
    nop_project.set("record", "remoteid", "the-real-job")
    nop_project.option.add_from("steptwo")

    nop_project.write_manifest("final.pkg.json")
    final = Project.from_manifest(filepath="final.pkg.json")
    final.set("record", "status", "pending", step="stepone", index="0")
    final.unset("metric", "tasktime", step="stepone", index="0")
    final.set("record", "status", "success", step="steptwo", index="0")
    final.set("metric", "tasktime", 9.0, step="steptwo", index="0")
    final.write_manifest("final.pkg.json")
    with open("final.pkg.json") as f:
        body = json.load(f)
    body["__meta__"]["class"] = "planted_module_never_imported/Evil"
    body["record"]["remoteid"]["node"]["steptwo"] = {"0": {"value": "planted", "signature": None}}
    with open("final.pkg.json", "w") as f:
        json.dump(body, f)

    results._fold_in_final("final.pkg.json", set(runtime_nodes(nop_project)))

    assert nop_project.get("record", "status", step="stepone", index="0") == "success"
    assert nop_project.get("metric", "tasktime", step="stepone", index="0") == 3.0
    assert nop_project.get("record", "status", step="steptwo", index="0") == "success"
    assert nop_project.get("metric", "tasktime", step="steptwo", index="0") == 9.0
    assert "planted_module_never_imported" not in sys.modules
    assert nop_project.get("record", "remoteid") == "the-real-job"


def serve_nodes(fake_v1, archives):
    serve(fake_v1, [artifact("node", step, "0") for step in archives],
          {f"node-{step}-0": body for step, body in archives.items()})


@pytest.fixture(params=[False, True], ids=["data-filter", "fallback"])
def extraction(request, monkeypatch):
    '''Each way an archive is extracted: the `data` filter, and the checks
    made by hand where the interpreter has none.'''
    from siliconcompiler import utils
    if request.param:
        monkeypatch.setattr(utils, "tar_extract_kwargs", lambda: {})


def test_a_link_into_a_sibling_nodes_outputs_extracts_inside_the_job(
        fake_v1, results, nop_project, extraction):
    '''A passed-through file links to its home node, and a hard-linked pair is
    one file: both land inside the job and resolve.'''
    serve_nodes(fake_v1, {
        "stepone": tarball([("outputs/gcd.vg", b"module gcd; endmodule\n")]),
        "steptwo": tarball([
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


def test_a_link_out_of_the_job_is_refused(fake_v1, results, nop_project, extraction):
    serve_nodes(fake_v1, {"steptwo": tarball([
        ("outputs/stolen", "->", "../../../../../../../../etc/passwd")])})
    results.fetch("j1")
    two = workdir(nop_project, step="steptwo", index="0")
    assert not os.path.lexists(os.path.join(two, "outputs", "stolen"))
