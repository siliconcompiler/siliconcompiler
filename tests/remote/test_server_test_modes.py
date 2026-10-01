import json

import pytest

from conftest import call, outcome, slug
from test_server_artifacts import listing, ran
from test_server_jobs import FakeDispatcher, stage, submit


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.config import (                  # noqa: E402
    DEFAULT_LIMITS, DEFAULTS, TEST_MODES, Config)


# The test modes. Every one is a legal v1 deployment, so what is asserted here
# is that each says what it serves on `GET /v1` and then does exactly that -- to
# the API, while the portal keeps showing everything. Mode 4 serves what mode 1
# does from a server that can fetch nothing.


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


###########################
# The presets
###########################

def test_mode_one_is_the_defaults(tmp_path):
    assert Config.load(tmp_path, test_mode=1)._values == Config.load(tmp_path)._values


def test_a_mode_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(ValueError, match="test mode 5"):
        Config.load(tmp_path, test_mode=5)


def test_every_mode_names_only_keys_the_config_has():
    '''The same rule as config.json: a preset key spelled wrong would be a
    restriction the mode claims and does not make.'''
    for preset in TEST_MODES.values():
        assert set(preset) <= set(DEFAULTS)
        assert set(preset.get("limits", {})) <= set(DEFAULT_LIMITS)


def test_config_json_still_applies_on_top_of_a_mode(tmp_path):
    '''⚠️ Under config.json, so one value can be moved without writing out the
    rest of the mode.'''
    (tmp_path / "config.json").write_text(json.dumps({"limits": {"concurrent_jobs": 3}}))

    config = Config.load(tmp_path, test_mode=3)

    assert config.limits["concurrent_jobs"] == 3
    assert config["features"] == []
    assert config.limits["pending_uploads"] == 2


@pytest.mark.parametrize("overlay,match", [
    ({"api_fetchable_kinds": ["manifest", "gds"]}, "unknown kinds: gds"),
    ({"denied_resources": {"pdks": ["x"]}}, "unknown resource kinds: pdks"),
    ({"denied_resources": {"pdk": "GF180*"}}, "must be a list"),
])
def test_a_policy_that_would_mean_nothing_is_refused(tmp_path, overlay, match):
    (tmp_path / "config.json").write_text(json.dumps(overlay))

    with pytest.raises(ValueError, match=match):
        Config.load(tmp_path)


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
    '''🔴 Nothing tells a client which mode it is in. It reads the features
    and the limits, as it would from any deployment.'''
    published = server_client.get("/v1").get_json()

    assert published["features"] == []
    assert published["limits"]["concurrent_jobs"] == 1
    assert published["limits"]["max_download_bytes"] == 20971520


###########################
# What the API hands over, and what the portal still does
###########################

@pytest.mark.parametrize("mode", [2])
def test_a_kind_the_api_withholds_is_listed_and_not_fetchable(
        server_client, key, token, finished):
    '''🔴 Listed, because it exists -- leaving it out would say *this server
    does not keep those*, which is untrue while the portal is showing it. Not
    fetchable, with no `access_request_url`: there is no path to yes from
    here.'''
    items = listing(server_client, key, token, finished["id"])

    by_kind = {}
    for item in items:
        by_kind.setdefault(item["kind"], set()).add(item["fetchable"])

    assert by_kind["node"] == {False}
    assert by_kind["manifest"] == {True}
    assert by_kind["logs"] == {True}
    assert by_kind["reports"] == {True}
    assert not any("access_request_url" in item or "blocked_by" in item
                   for item in items)


@pytest.mark.parametrize("mode", [2])
def test_fetching_a_withheld_kind_is_not_approved(
        server_client, key, token, finished):
    '''Not `entitlement-denied`, which names a resource: withholding a kind
    is the per-object gate.'''
    item = next(item for item in listing(server_client, key, token, finished["id"])
                if item["kind"] == "node")

    response = fetch(server_client, key, token, finished["id"], item)

    assert response.status_code == 403
    assert slug(response) == "artifact-not-approved"
    assert "Retry-After" not in response.headers


@pytest.mark.parametrize("mode", [3])
def test_mode_three_hands_over_the_manifest_and_nothing_else(
        server_client, key, token, finished):
    items = listing(server_client, key, token, finished["id"])

    fetchable = {(item["kind"], item["step"]) for item in items if item["fetchable"]}
    # 🔴 The node manifests too: they carry each node's record and metrics, so
    # the client can still say how long a node took and what it warned about.
    assert fetchable == {("manifest", None), ("manifest", "stepone"),
                         ("manifest", "steptwo")}

    manifest = next(item for item in items if item["kind"] == "manifest")
    assert fetch(server_client, key, token, finished["id"], manifest).status_code == 303


@pytest.mark.parametrize("mode", [3])
def test_the_portal_still_lists_and_serves_every_kind(
        server, signed_in, key, token, finished):
    '''The surface split `max_download_bytes` already makes: the restriction
    binds the API, and the portal is a person choosing one object.'''
    row = server.config["SC_STORE"].one(
        "SELECT id FROM artifacts WHERE job_id = ? AND kind = 'node' "
        "AND step = 'stepone'", (finished["id"],))

    response = signed_in.get(f"/portal/jobs/{finished['id']}/artifacts/{row['id']}")
    assert response.status_code == 302
    assert signed_in.get(response.headers["Location"]).status_code == 200

    page = signed_in.get(f"/portal/jobs/{finished['id']}").get_data(as_text=True)
    assert row["id"] in page


###########################
# Logs
###########################

@pytest.mark.parametrize("mode", [3])
def test_no_logs_over_the_api_is_permanent(server_client, key, token, finished):
    '''🔴 `logs.stream` absent from the features is a refusal and not only a
    word missing from a list.'''
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"
    assert response.get_json()["feature"] == "logs.stream"


@pytest.mark.parametrize("mode", [3])
def test_the_portal_still_shows_the_log(signed_in, finished):
    response = signed_in.get(f"/portal/jobs/{finished['id']}/logs/stepone/0")

    assert response.status_code == 200
    assert "stepone ran" in response.get_data(as_text=True)


@pytest.mark.parametrize("mode", [2])
def test_mode_two_keeps_the_archived_log(server_client, key, token, finished):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{finished['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 303


def _running(server, server_client, key, token, job_archive):
    archive, digest, size = job_archive()
    job = stage(server_client, key, token, archive, size)
    submit(server_client, key, token, job["id"], digest, size)
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'running' WHERE job_id = ?", (job["id"],))
    return job


@pytest.mark.parametrize("mode", [2])
def test_mode_two_tails_each_node(server, server_client, key, token,
                                  job_archive, dispatcher):
    job = _running(server, server_client, key, token, job_archive)

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job['id']}/logs?step=stepone&index=0", token)

    assert response.status_code == 303
    assert "/stream/logs/" in response.headers["Location"]


@pytest.mark.parametrize("mode", [2])
def test_mode_two_has_no_job_stream_and_says_so_permanently(
        server, server_client, key, token, job_archive, dispatcher):
    '''So a client falls back to one stream per running node, which is the
    whole reason `logs.stream.job` is its own string.'''
    job = _running(server, server_client, key, token, job_archive)

    response = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/logs", token)

    assert response.status_code == 501
    assert response.get_json()["feature"] == "logs.stream.job"
    assert "Retry-After" not in response.headers


@pytest.mark.parametrize("mode", [3])
def test_mode_three_names_the_broadest_missing_capability(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 `logs.stream`, not `logs.stream.job`: told only that the job stream is
    missing, a client falls back to per-node requests that fail too.'''
    job = _running(server, server_client, key, token, job_archive)

    response = call(server_client, key, "GET", f"/v1/jobs/{job['id']}/logs", token)

    assert response.status_code == 501
    assert response.get_json()["feature"] == "logs.stream"


###########################
# A PDK, library or tool nobody may use
###########################

@pytest.fixture
def lint_project(nop_project):
    '''A flow whose one node declares verilator, which mode 3 denies.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.verilator.lint import LintTask

    flow = Flowgraph("lintflow")
    flow.node("lint", LintTask())
    nop_project.set_flow(flow)
    return nop_project


@pytest.mark.parametrize("mode", [3])
def test_a_denied_tool_is_refused_at_submit(server_client, key, token,
                                            job_archive, lint_project, dispatcher):
    '''🔴 The refusal a grant-backed deployment gives: `entitlement-denied`
    naming the kind and the name, the job `rejected`, and nothing handed to
    the cluster.'''
    archive, digest, size = job_archive(lint_project)
    job = stage(server_client, key, token, archive, size)

    response = outcome(server_client, key, token,
                       submit(server_client, key, token, job["id"], digest, size))

    assert response.status_code == 403
    assert slug(response) == "entitlement-denied"
    assert response.get_json()["resource_kind"] == "tool"
    assert response.get_json()["resource"] == "verilator"
    assert not dispatcher.submitted

    read = call(server_client, key, "GET", f"/v1/jobs/{job['id']}", token).get_json()
    assert read["state"] == "rejected"
    assert read["error"]["type"].endswith("/entitlement-denied")


@pytest.mark.parametrize("mode", [1])
def test_the_same_tool_runs_where_nothing_is_denied(server_client, key, token,
                                                    job_archive, lint_project,
                                                    dispatcher):
    archive, digest, size = job_archive(lint_project)
    job = stage(server_client, key, token, archive, size)

    assert submit(server_client, key, token, job["id"], digest, size).status_code == 202


@pytest.mark.parametrize("mode", [3])
def test_the_pdk_is_named_first_and_the_rest_are_counted(
        server, server_client, key, token, job_archive, lint_project,
        dispatcher, monkeypatch):
    '''The slug carries one `resource`, so the first is named -- PDK, then
    library, then tool -- and the detail says there are more, so fixing one
    is not followed by a surprise.'''
    jobs = server.config["SC_JOBS"]
    real = jobs._act_on

    def act_on(job, raw):
        summary = real(job, raw)
        summary.update(pdk="GF180_5LM_1TM_9K_9t", libraries=["nangate45"])
        return summary

    monkeypatch.setattr(jobs, "_act_on", act_on)

    archive, digest, size = job_archive(lint_project)
    job = stage(server_client, key, token, archive, size)
    response = outcome(server_client, key, token,
                       submit(server_client, key, token, job["id"], digest, size))

    assert response.status_code == 403
    body = response.get_json()
    assert (body["resource_kind"], body["resource"]) == ("pdk", "GF180_5LM_1TM_9K_9t")
    assert "2 more" in body["detail"]


def test_the_libraries_are_the_main_library_and_the_rest():
    '''`asic,asiclib` is filled from the main library when a run starts, so a
    manifest that has never run may carry only `asic,mainlib`.'''
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


###########################
# Mode 4: a server that fetches nothing
###########################

@pytest.mark.parametrize("mode", [4])
def test_mode_four_publishes_what_mode_one_does(server_client, tmp_path):
    '''Nothing on the wire says a server cannot fetch: that is found out
    per job, by being asked for the source.'''
    from siliconcompiler.remote.server.app import create_app

    one = create_app(tmp_path / "one", cluster="local", test_mode=1).test_client()
    assert server_client.get("/v1").get_json() == one.get("/v1").get_json()


@pytest.mark.parametrize("mode", [4])
def test_mode_four_sends_the_source_back_and_keeps_both_uploads(
        server, server_client, key, token, job_archive, dispatcher, gcd_design,
        tmp_path):
    '''🔴 The follow-up path, on demand: the allowlisted PDK is not asked for
    at create, every fetch fails for good, and a copy already held is not used
    -- so the job goes back asking for it, and the second archive is kept as
    its own `input` beside the first.'''
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
