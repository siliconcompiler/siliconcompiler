import json

import pytest

from conftest import call, outcome, slug
from test_server_artifacts import listing, ran
from test_server_jobs import FakeDispatcher, stage, submit


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.config import (                  # noqa: E402
    DEFAULT_LIMITS, DEFAULTS, TEST_MODES, Config)


# Every test mode is a legal v1 deployment: each says what it serves on
# `GET /v1` and does exactly that to the API, while the portal shows
# everything. Mode 4 serves what mode 1 does from a server that fetches nothing.


@pytest.fixture
def mode():
    return 1


@pytest.fixture
def server(mode):
    '''The conftest server, in a test mode.'''
    from siliconcompiler.remote.server.app import create_app

    return create_app("datadir", cluster="local", test_mode=mode)


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


@pytest.fixture
def finished(server, server_client, key, token, job_archive, dispatcher):
    return ran(server, server_client, key, token, job_archive)


@pytest.fixture
def signed_in(server, server_client, key, token):
    response = call(server_client, key, "POST", "/v1/auth/browser", token, json={})
    url = response.get_json()["url"]
    assert server_client.get(url.split("http://localhost", 1)[1]).status_code == 302
    return server_client


def fetch(client, key, token, job_id, item):
    return call(client, key, "GET", f"/v1/jobs/{job_id}/artifacts/{item['id']}", token)


def node_log(client, key, token, job_id):
    return call(client, key, "GET", f"/v1/jobs/{job_id}/logs?step=stepone&index=0", token)


def test_the_presets_are_config(tmp_path):
    '''Mode 1 is the defaults; an unknown mode is refused; and a preset names
    only keys the config has, or it claims a restriction it does not make.'''
    assert Config.load(tmp_path, test_mode=1)._values == Config.load(tmp_path)._values
    with pytest.raises(ValueError, match="test mode 5"):
        Config.load(tmp_path, test_mode=5)
    for preset in TEST_MODES.values():
        assert set(preset) <= set(DEFAULTS)
        assert set(preset.get("limits", {})) <= set(DEFAULT_LIMITS)


def test_config_json_still_applies_on_top_of_a_mode(tmp_path):
    '''So one value can be moved without writing out the rest of the mode.'''
    (tmp_path / "config.json").write_text(json.dumps({"limits": {"concurrent_jobs": 3}}))

    config = Config.load(tmp_path, test_mode=3)

    assert config.limits["concurrent_jobs"] == 3
    assert config["features"] == []
    assert config.limits["pending_uploads"] == 2


def test_a_denial_is_a_glob_and_case_matters(tmp_path):
    config = Config.load(tmp_path, test_mode=3)

    assert config.denied("pdk", "GF180_5LM_1TM_9K_9t")
    assert not config.denied("pdk", "gf180")
    assert not config.denied("pdk", "skywater130")
    assert config.denied("library", "nangate45")
    assert config.denied("tool", "verilator")
    assert not config.denied("tool", "openroad")


@pytest.mark.parametrize("mode", [3])
def test_the_mode_is_what_get_v1_publishes(server_client):
    '''Nothing tells a client its mode: it reads features and limits.'''
    published = server_client.get("/v1").get_json()

    assert published["features"] == []
    assert published["limits"]["concurrent_jobs"] == 1
    assert published["limits"]["max_download_bytes"] == 20971520


@pytest.mark.parametrize("mode", [2])
def test_a_kind_the_api_withholds_is_listed_and_not_approved(
        server_client, key, token, finished):
    '''Listed, since leaving it out would say *this server does not keep
    those* while the portal shows it; not fetchable, with no path to yes. Not
    `entitlement-denied`, which names a resource: this is the per-object gate.'''
    items = listing(server_client, key, token, finished["id"])

    by_kind = {}
    for item in items:
        by_kind.setdefault(item["kind"], set()).add(item["fetchable"])
    assert by_kind["node"] == {False}
    assert by_kind["manifest"] == by_kind["logs"] == by_kind["reports"] == {True}
    assert not any("access_request_url" in item or "blocked_by" in item for item in items)

    response = fetch(server_client, key, token, finished["id"],
                     next(item for item in items if item["kind"] == "node"))
    assert (response.status_code, slug(response)) == (403, "artifact-not-approved")
    assert "Retry-After" not in response.headers


@pytest.mark.parametrize("mode", [3])
def test_mode_three_hands_over_the_manifests_and_no_logs(server_client, key, token, finished):
    '''The node manifests too: each node's record and metrics, so a client
    can still say how long a node took. No `logs.stream` is a permanent
    refusal, not only a word missing from a list.'''
    items = listing(server_client, key, token, finished["id"])

    assert {(item["kind"], item["step"]) for item in items if item["fetchable"]} == {
        ("manifest", None), ("manifest", "stepone"), ("manifest", "steptwo")}
    manifest = next(item for item in items if item["kind"] == "manifest")
    assert fetch(server_client, key, token, finished["id"], manifest).status_code == 303

    response = node_log(server_client, key, token, finished["id"])
    assert (response.status_code, slug(response)) == (501, "feature-unsupported")
    assert response.get_json()["feature"] == "logs.stream"
    assert "Retry-After" not in response.headers
    # The job stream names the broadest missing capability, or a client
    # falls back to per-node requests that fail too.
    whole = call(server_client, key, "GET", f"/v1/jobs/{finished['id']}/logs", token)
    assert (whole.status_code, whole.get_json()["feature"]) == (501, "logs.stream")


@pytest.mark.parametrize("mode", [3])
def test_the_portal_still_lists_and_serves_every_kind_and_the_log(server, signed_in, finished):
    '''The split `max_download_bytes` already makes: the restriction binds the
    API, and the portal is a person choosing one object.'''
    row = server.config["SC_STORE"].one(
        "SELECT id FROM artifacts WHERE job_id = ? AND kind = 'node' "
        "AND step = 'stepone'", (finished["id"],))

    response = signed_in.get(f"/portal/jobs/{finished['id']}/artifacts/{row['id']}")
    assert response.status_code == 302
    assert signed_in.get(response.headers["Location"]).status_code == 200
    assert row["id"] in signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)

    log = signed_in.get(f"/portal/jobs/{finished['id']}/logs/stepone/0")
    assert log.status_code == 200
    assert "stepone ran" in log.get_data(as_text=True)


@pytest.mark.parametrize("mode", [2])
def test_mode_two_serves_each_nodes_log_and_no_job_stream(
        server, server_client, key, token, job_archive, finished):
    '''A finished node's archive and a running node's tail; the job stream is
    refused permanently, so a client falls back to one stream per node.'''
    assert node_log(server_client, key, token, finished["id"]).status_code == 303

    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'running' WHERE job_id = ?", (job["id"],))

    tail = node_log(server_client, key, token, job["id"])
    assert tail.status_code == 303
    assert "/stream/logs/" in tail.headers["Location"]

    whole = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/logs", token)
    assert (whole.status_code, whole.get_json()["feature"]) == (501, "logs.stream.job")
    assert "Retry-After" not in whole.headers


@pytest.fixture
def lint_project(nop_project):
    '''A flow whose one node declares verilator, which mode 3 denies.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.verilator.lint import LintTask

    flow = Flowgraph("lintflow")
    flow.node("lint", LintTask())
    nop_project.set_flow(flow)
    return nop_project


def submitted(server_client, key, token, archive):
    path, digest, size = archive
    job = stage(server_client, key, token, path, size)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


@pytest.mark.parametrize("mode", [3])
def test_a_denied_tool_is_refused_at_submit(server_client, key, token,
                                            job_archive, lint_project, dispatcher):
    '''As a grant-backed deployment refuses: `entitlement-denied` naming the
    kind and the name, the job `rejected`, nothing handed to the cluster.'''
    job, response = submitted(server_client, key, token, job_archive(lint_project))

    assert (response.status_code, slug(response)) == (403, "entitlement-denied")
    assert response.get_json()["resource_kind"] == "tool"
    assert response.get_json()["resource"] == "verilator"
    assert not dispatcher.submitted

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "rejected"
    assert read["error"]["type"].endswith("/entitlement-denied")


def test_the_same_tool_runs_where_nothing_is_denied(server_client, key, token,
                                                    job_archive, lint_project, dispatcher):
    archive, digest, size = job_archive(lint_project)
    job = stage(server_client, key, token, archive, size)

    assert submit(server_client, key, token, job["id"], digest, size).status_code == 202


@pytest.mark.parametrize("mode", [3])
def test_the_pdk_is_named_first_and_the_rest_are_counted(
        server, server_client, key, token, job_archive, lint_project,
        dispatcher, monkeypatch):
    '''The slug carries one `resource` -- PDK, then library, then tool -- and
    the detail says there are more, so fixing one is no surprise.'''
    jobs = server.config["SC_JOBS"]
    real = jobs._act_on

    def act_on(job, raw):
        summary = real(job, raw)
        summary.update(pdk="GF180_5LM_1TM_9K_9t", libraries=["nangate45"])
        return summary

    monkeypatch.setattr(jobs, "_act_on", act_on)

    _, response = submitted(server_client, key, token, job_archive(lint_project))

    assert response.status_code == 403
    body = response.get_json()
    assert (body["resource_kind"], body["resource"]) == ("pdk", "GF180_5LM_1TM_9K_9t")
    assert "2 more" in body["detail"]


def test_the_libraries_are_the_main_library_and_the_rest():
    '''`asic,asiclib` is filled from the main library when a run starts, so a
    manifest that never ran may carry only `asic,mainlib`.'''
    from siliconcompiler.remote.server.staging.manifestread import _libraries

    class Manifest:
        def __init__(self, **values):
            self.values = values

        def get(self, *keypath):
            if keypath[-1] not in self.values:
                raise KeyError(keypath)
            return self.values[keypath[-1]]

    assert _libraries(Manifest(mainlib="nangate45", asiclib=[])) == ["nangate45"]
    assert _libraries(Manifest(mainlib="a", asiclib=["a", "b"])) == ["a", "b"]
    assert _libraries(Manifest()) == []


@pytest.mark.parametrize("mode", [4])
def test_mode_four_publishes_what_mode_one_does(server_client, tmp_path):
    '''Nothing on the wire says a server cannot fetch: that is found out per
    job, by being asked for the source.'''
    from siliconcompiler.remote.server.app import create_app

    one = create_app(tmp_path / "one", cluster="local", test_mode=1).test_client()
    assert server_client.get("/v1").get_json() == one.get("/v1").get_json()


@pytest.mark.parametrize("mode", [4])
def test_mode_four_sends_the_source_back_and_keeps_both_uploads(
        server, server_client, key, token, job_archive, dispatcher, gcd_design,
        tmp_path):
    '''The follow-up path on demand: the allowlisted PDK is not asked for
    at create, every fetch fails for good, a copy already held is not used --
    so the job asks for it, and the second archive is its own `input`.'''
    from siliconcompiler import PDK
    from test_owners import DATASHEET, _nop_asic, collected_path, resource
    from test_server_sources_flow import LAMBDA, read, send, wait_for

    # A copy from before would supply the job and skip the path under test.
    server.config["SC_JOBS"]._sources.held = lambda source, ref: str(tmp_path)

    project = _nop_asic(gcd_design, tmp_path, resource(PDK, "lambda", LAMBDA, create=False))
    archive, digest, size = job_archive(project)
    job = stage(server_client, key, token, archive, size)
    assert "upload_sources" not in job or job["upload_sources"] == []

    assert submit(server_client, key, token, job["id"], digest, size).status_code == 202
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    == "awaiting_input")
    back = read(server_client, key, token, job["id"])
    assert back["upload_sources"] == [
        {"kind": "dataroot", "keypath": ["library", "lambda", "dataroot", "lambda"]}]
    reason = server.config["SC_STORE"].one(
        "SELECT reason FROM job_state_transitions WHERE job_id = ? "
        "AND to_state = 'awaiting_input' AND from_state = 'staging'", (job["id"],))["reason"]
    assert "fetches nothing" in reason

    hashed = collected_path(project, ("library", "lambda", *DATASHEET))
    response = send(server_client, key, token, job["id"],
                    {f"sc_collected_files/{hashed}": b"sent by the client\n"})
    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: dispatcher.submitted)

    uploads = [item for item in listing(server_client, key, token, job["id"], "?kind=input")
               if item["step"] is None]
    assert len(uploads) == 2 and uploads[0]["digest"] == digest
