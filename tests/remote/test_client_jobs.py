import hashlib
import json
import os

import pytest
import requests
import responses

from siliconcompiler.remote import RemoteError, ServerProblem
from siliconcompiler.remote.client.run import RemoteRun, node_status
from siliconcompiler.tools.builtin.nop import NOPTask

from conftest import (
    creates, job_body, node_body, problem, put_body, refused, route_created, route_granted,
    route_submitted, routes_for_a_submit)


RUN_FAILED = "https://siliconcompiler.com/server-errors/run-failed"


@pytest.fixture
def run(logged_in, nop_project):
    return RemoteRun(nop_project, logged_in)


def _cancels(fake_v1):
    return [c.request for c in fake_v1.calls if c.request.path_url.endswith("/cancel")]


def _cancelled(fake_v1):
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel", job_body("cancelled"), status=202)


@pytest.mark.parametrize("state,terminal,expected", [
    ("pending", False, "pending"), ("queued", False, "queued"),
    ("running", False, "running"), ("completed", True, "success"),
    ("failed", True, "error"), ("skipped", True, "skipped"),
    ("cancelled", True, "error"),
    # Fetching its image: waiting, so a six-minute pull is not read as a hang.
    ("preparing", False, "queued"),
    # An unknown state reads `terminal`, never its name.
    ("quiescing", False, "pending"), ("evaporated", True, "error"),
])
def test_every_node_state_maps(state, terminal, expected):
    assert node_status(state, terminal) == expected


def test_submit_is_four_calls_and_the_upload_carries_no_session(fake_v1, run, caplog):
    '''The PUT addresses storage, which may be somebody else's bucket. The
    grant carries the archive's own size and digest, and each POST its
    own idempotency key.'''
    routes_for_a_submit(fake_v1)

    with caplog.at_level("INFO"):
        assert run._start() == "01J9-job"

    paths = [call.request.path_url for call in fake_v1.calls]
    assert paths[-4:] == ["/v1/jobs", "/v1/jobs/01J9-job/upload-grant",
                          "/put", "/v1/jobs/01J9-job/submit"]

    upload = next(c.request for c in fake_v1.calls
                  if c.request.url == "https://storage.test/put")
    assert "Authorization" not in upload.headers and "DPoP" not in upload.headers

    posts = {call.request.path_url: call.request
             for call in fake_v1.calls if call.request.method == "POST"}
    keys = [posts[path].headers["Idempotency-Key"]
            for path in ("/v1/jobs", "/v1/jobs/01J9-job/submit")]
    assert all(keys) and keys[0] != keys[1]

    grant = json.loads(posts["/v1/jobs/01J9-job/upload-grant"].body)
    sent = put_body(fake_v1)
    assert grant == {"size_bytes": len(sent),
                     "digest": f"sha256:{hashlib.sha256(sent).hexdigest()}"}

    assert "Uploading" in caplog.text
    assert "design gcd (library,gcd,dataroot,gcd-pytest-example):" in caplog.text


def test_the_create_body_is_two_names_and_a_descriptor(fake_v1, run):
    '''Authoritative at the top, advisory under `descriptor`; no `versions`,
    no `resources` and no `run_hash`; submit has no body.'''
    routes_for_a_submit(fake_v1)

    run._start()

    created = next(c.request for c in fake_v1.calls if c.request.path_url == "/v1/jobs")
    body = json.loads(created.body)
    assert set(body) == {"design", "jobname", "descriptor"}
    descriptor = body["descriptor"]
    assert "versions" not in descriptor and "resources" not in descriptor
    pins = descriptor["requested_versions"]["python"]["siliconcompiler"]
    assert isinstance(pins, list) and pins[0].startswith("==")
    # The flow's name and node count.
    assert isinstance(descriptor["flow"], str) and descriptor["flow"]
    assert descriptor["node_count"] == 2
    assert "run_hash" not in body and "run_hash" not in descriptor
    # No node runs the user's own Python, so no interpreter is named.
    assert "interpreter" not in descriptor["requested_versions"]

    submitted = next(c.request for c in fake_v1.calls
                     if c.request.path_url.endswith("/submit"))
    assert json.loads(submitted.body) == {}


def _versions(run):
    '''The `requested_versions` a run would create its job with.'''
    return run._plan(run._read()).versions


def test_requested_python_is_the_fixed_list(fake_v1, logged_in, gcd_design):
    '''Never every class the manifest names: lambdapdk's PDK and libraries
    are data the job carries.'''
    from importlib.metadata import version

    from siliconcompiler import ASIC
    from siliconcompiler.targets import skywater130_demo

    project = ASIC(gcd_design)
    skywater130_demo(project)

    pins = _versions(RemoteRun(project, logged_in))["python"]

    assert list(pins) == ["siliconcompiler"]
    assert version("lambdapdk")          # there to be left out


@pytest.mark.parametrize("distribution,listed,named", [
    ("scfakedata", "1.0.0", True), ("scfakedata", "0.9.0", False), (None, "1.0.0", False)],
    ids=["listed", "another-version", "no-distribution"])
def test_an_installed_data_package_is_named_only_where_the_server_lists_it(
        fake_v1, logged_in, nop_project, capabilities, monkeypatch, distribution, listed,
        named):
    '''Listed at this version, it is named exactly and its dataroots do not
    upload; otherwise, or with no distribution to name, its files go up with the job.'''
    from siliconcompiler import StdCellLibrary
    from siliconcompiler.package import PythonPathResolver
    from siliconcompiler.remote import owners

    lib = StdCellLibrary("scfakelib")
    lib.set_dataroot("scfakedata", "python://scfakedata_module")
    with lib.active_dataroot("scfakedata"):
        lib.set("package", "doc", "datasheet", "datasheet.pdf")
    nop_project.add_dep(lib)
    monkeypatch.setattr(PythonPathResolver, "is_python_module_editable",
                        staticmethod(lambda module: False))
    monkeypatch.setattr(owners, "_distribution_of", lambda module: distribution)
    monkeypatch.setattr("siliconcompiler.remote.client.run.metadata.version",
                        lambda name: "1.0.0" if name == "scfakedata"
                        else __import__("importlib.metadata").metadata.version(name))
    published = json.loads(json.dumps(capabilities))
    published["software"]["python"]["scfakedata"] = [listed]
    fake_v1.replace(responses.GET, "", published)

    run = RemoteRun(nop_project, logged_in)
    reads = run._read()
    one, = [one for one in reads.values if one.key[:2] == ("library", "scfakelib")]

    assert one.upload is not named
    assert ("scfakedata" in run._plan(reads).versions["python"]) is named
    if named:
        assert run._plan(reads).versions["python"]["scfakedata"] == ["==1.0.0"]


def _declared(name):
    from importlib import metadata

    from packaging.requirements import Requirement

    return [str(Requirement(line).specifier)
            for line in metadata.requires("siliconcompiler") or []
            if Requirement(line).name == name]


def _one_node_project(gcd_design, task):
    from siliconcompiler import Flowgraph, Project

    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("one")
    flow.node("only", task)
    project.set_flow(flow)
    return project


def test_a_framework_distribution_is_pinned_where_installed(fake_v1, logged_in, gcd_design):
    '''scfakebits is RunsATestbench's framework: nothing declares a range for
    it, so it is pinned at what is installed.'''
    from pytasks import RunsATestbench

    open("tb.py", "w").write("")
    pins = _versions(RemoteRun(_one_node_project(gcd_design, RunsATestbench()),
                               logged_in))["python"]

    assert _declared("scfakebits") == []
    assert "scfakebits" in pins
    assert pins["siliconcompiler"]


def test_a_cocotb_node_names_siliconcompilers_cocotb_range(fake_v1, logged_in, gcd_design):
    '''Declared on the task's class, so Verilator's compile step -- which
    needs Verilator's setup -- still lands where cocotb is.'''
    from siliconcompiler.remote.client.run import _framework_range
    from siliconcompiler.tools.verilator.cocotb_compile import CocotbCompileTask

    declared = _declared("cocotb")
    project = _one_node_project(gcd_design, CocotbCompileTask())

    assert declared and _framework_range("cocotb") == declared[0]
    assert _versions(RemoteRun(project, logged_in))["python"]["cocotb"] == declared


def test_the_loop_ends_on_terminal_and_not_on_the_name(fake_v1, run, no_sleep):
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("running"))
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("quiescing", terminal=True))

    with pytest.raises(RemoteError):
        run._poll("01J9-job")

    assert len([c for c in fake_v1.calls if c.request.method == "GET"]) >= 2


@pytest.mark.parametrize("retry_after,paced", [("17", 17), ("0", 1), ("soon", None)])
def test_the_server_sets_the_pace(fake_v1, run, no_sleep, retry_after, paced):
    '''`Retry-After` per response, never below a second; an unreadable one
    is not a failed poll.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("running"),
                  headers={"Retry-After": retry_after})
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run._poll("01J9-job")

    assert no_sleep and (paced is None or paced in no_sleep)


def test_node_states_are_recorded_and_unknown_nodes_ignored(fake_v1, run, nop_project):
    '''A node the project never heard of, or no node at all, does not end a run.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "completed",
        nodes=[node_body("stepone", "completed", exit_code=0), node_body("steptwo", "skipped"),
               {"step": "nowhere", "index": "9", "state": "completed", "terminal": True},
               {"state": "completed", "terminal": True}]))

    run._poll("01J9-job")

    assert nop_project.get('record', 'status', step="stepone", index="0") == "success"
    assert nop_project.get('record', 'status', step="steptwo", index="0") == "skipped"


SIGN_IN = {"url": "https://sc-server.test/portal/enter?token=t",
           "expires_at": "2026-10-01T18:04:30Z"}


@pytest.fixture
def opened(run, monkeypatch):
    '''What the run opened in a browser, as at a terminal outside CI.'''
    urls = []
    run.project.option.set_nodisplay(False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(run.client, "open_url",
                        lambda url, what, require_tty=True: urls.append(url) or True)
    return urls


def _pages(fake_v1):
    return [c.request for c in fake_v1.calls if c.request.url.endswith("/v1/auth/browser")]


@pytest.mark.parametrize("which,asked", [("job", {"job_id": "01J9-job"}), ("home", {})])
def test_a_page_is_asked_for_never_built(fake_v1, run, opened, which, asked):
    '''After a submit, the job's page by its id; `sc-config remote portal`, the
    home page. The client opens what comes back.'''
    fake_v1.route(responses.POST, "auth/browser", SIGN_IN)

    if which == "job":
        run._open_portal("01J9-job")
    else:
        run.client.portal()

    page, = _pages(fake_v1)
    assert json.loads(page.body) == asked
    assert page.headers["Authorization"].startswith("DPoP ")
    assert opened == [SIGN_IN["url"]]


def test_a_sign_in_is_printed_only_where_no_browser_opened_and_never_logged(
        fake_v1, run, monkeypatch, caplog, capsys):
    '''A sign-in link is a bearer secret for its page.'''
    import logging

    caplog.set_level(logging.DEBUG)
    fake_v1.route(responses.POST, "auth/browser", SIGN_IN)

    for opens in (True, False):
        monkeypatch.setattr(run.client, "open_url",
                            lambda url, what, require_tty=True: opens)
        assert run.client.open_page("the job's page", job_id="01J9-job") is opens
        assert (SIGN_IN["url"] in capsys.readouterr().out) is not opens

    assert "token=t" not in caplog.text


def test_a_plain_page_is_printed_and_opened(fake_v1, run, opened, caplog):
    '''`expires_at: null` is the page itself, which needs no secrecy.'''
    import logging

    caplog.set_level(logging.INFO)
    fake_v1.route(responses.POST, "auth/browser",
                  {"url": "https://crucible.test/jobs/01J9-job", "expires_at": None})

    run._open_portal("01J9-job")

    assert opened == ["https://crucible.test/jobs/01J9-job"]
    assert "https://crucible.test/jobs/01J9-job" in caplog.text


@pytest.mark.parametrize("slug,status", [("not-found", 404), ("not-permitted", 403)])
def test_a_refused_page_is_said_and_the_run_carries_on(fake_v1, run, opened, caplog,
                                                       slug, status):
    refused(fake_v1, responses.POST, "auth/browser", slug, status)

    run._open_portal("01J9-job")

    assert opened == []
    assert "No page for the job's page" in caplog.text


def test_a_refused_portal_command_fails_and_says_why(fake_v1, run, opened):
    '''Asked for on purpose, so the command fails.'''
    refused(fake_v1, responses.POST, "auth/browser", "not-permitted", 403)

    with pytest.raises(RemoteError, match="not-permitted|Not permitted"):
        run.client.portal()
    assert opened == []


@pytest.mark.parametrize("why", ["ci", "browser-off", "nodisplay"])
def test_a_job_page_is_asked_for_only_where_somebody_watches(fake_v1, run, opened,
                                                             monkeypatch, settings, why):
    '''Not in CI, which asks for no page at all, nor with the `remote browser`
    setting off or `option,nodisplay` set.'''
    from siliconcompiler.remote.client.credentials import BROWSER

    if why == "ci":
        monkeypatch.setenv("SC_CI_CREDENTIAL", "scci_01J9credential_key")
        with pytest.raises(RemoteError, match="CI session"):
            run.client.portal()
    elif why == "browser-off":
        BROWSER.set(False)
    else:
        run.project.option.set_nodisplay(True)

    run._open_portal("01J9-job")

    assert not _pages(fake_v1)
    assert not opened


ARTIFACTS = "jobs/01J9-job/artifacts"


@pytest.mark.parametrize("link", [
    f"</v1/{ARTIFACTS}?limit=1&cursor=abc&kept=1>; rel=next",
    f'</v1/{ARTIFACTS}?cursor=zzz>; rel="prev", </v1/{ARTIFACTS}?limit=1&cursor=abc&kept=1>; '
    'rel="next"',
    f'<https://sc-server.test/v1/{ARTIFACTS}?limit=1&cursor=abc&kept=1>; title="a, b"; '
    'rel="next last"',
    f"</v1/{ARTIFACTS}?limit=1&cursor=abc&kept=1>; REL=Next",
], ids=["unquoted", "second", "absolute", "case"])
def test_the_next_page_is_the_link_target_as_given(fake_v1, logged_in, link):
    '''RFC 8288: the `rel="next"` URL requested unchanged,
    never this request rebuilt around a cursor.'''
    from urllib.parse import urlsplit

    fake_v1.route(responses.GET, ARTIFACTS, {"items": [{"id": "a1"}]}, headers={"Link": link})
    fake_v1.route(responses.GET, ARTIFACTS, {"items": [{"id": "a2"}]})

    assert len(logged_in.artifacts("01J9-job", kind="node")) == 2

    pages = [c.request.url for c in fake_v1.calls
             if urlsplit(c.request.url).path == f"/v1/{ARTIFACTS}"]
    assert pages[-1] == f"https://sc-server.test/v1/{ARTIFACTS}?limit=1&cursor=abc&kept=1"


@pytest.mark.parametrize("again", [False, True], ids=["restarted", "twice"])
def test_a_cursor_the_server_no_longer_takes_restarts_the_listing_once(
        fake_v1, logged_in, again):
    '''`invalid-cursor` starts the listing again from its first page, keeping
    nothing from before; a second one is the answer.'''
    first = {"headers": {"Link": f'</v1/{ARTIFACTS}?cursor=stale>; rel="next"'}}
    stale = {"status": 400, "content_type": "application/problem+json"}
    fake_v1.route(responses.GET, ARTIFACTS, {"items": [{"id": "a1"}]}, **first)
    fake_v1.route(responses.GET, ARTIFACTS, problem("invalid-cursor", 400), **stale)
    fake_v1.route(responses.GET, ARTIFACTS, {"items": [{"id": "a1"}]}, **first)
    if again:
        fake_v1.route(responses.GET, ARTIFACTS, problem("invalid-cursor", 400), **stale)
        with pytest.raises(ServerProblem):
            logged_in.artifacts("01J9-job")
    else:
        fake_v1.route(responses.GET, ARTIFACTS, {"items": [{"id": "a2"}]})
        assert [item["id"] for item in logged_in.artifacts("01J9-job")] == ["a1", "a2"]


def test_a_next_page_on_another_origin_is_not_followed(fake_v1, logged_in):
    '''The request carries this session.'''
    fake_v1.route(responses.GET, ARTIFACTS, {"items": []},
                  headers={"Link": f'<https://elsewhere.test/v1/{ARTIFACTS}?cursor=a>; '
                                   'rel="next"'})

    with pytest.raises(RemoteError, match="another origin"):
        logged_in.artifacts("01J9-job")

    assert not [c for c in fake_v1.calls if "elsewhere" in c.request.url]


def test_a_boolean_filter_goes_as_true_or_false(fake_v1, logged_in):
    '''`true` or `false`, never Python's `True`.'''
    from urllib.parse import parse_qs, urlsplit

    fake_v1.route(responses.GET, ARTIFACTS, {"items": []})

    logged_in.artifacts("01J9-job", fetchable=True, deleted=False)
    logged_in.artifacts("01J9-job", fetchable=[True, False])

    first, second = [parse_qs(urlsplit(call.request.url).query) for call in fake_v1.calls
                     if urlsplit(call.request.url).path == f"/v1/{ARTIFACTS}"]
    assert (first["fetchable"], first["deleted"]) == (["true"], ["false"])
    assert second["fetchable"] == ["true", "false"]


@pytest.mark.parametrize("slug,status,said", [("not-found", 404, "not one you are a member of"),
                                              ("not-permitted", 403, "is archived")])
def test_a_create_refused_over_its_project_names_the_project(fake_v1, logged_in, monkeypatch,
                                                             slug, status, said):
    '''At create these refusals are about the project SC_REMOTE_PROJECT names, never a job.'''
    monkeypatch.setenv("SC_REMOTE_PROJECT", "rocket-v2")
    refused(fake_v1, responses.POST, "jobs", slug, status)

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    rendered = str(raised.value)
    assert "The project rocket-v2, which SC_REMOTE_PROJECT names" in rendered and said in rendered
    assert "this job" not in rendered


def test_the_grants_content_length_is_not_forwarded(fake_v1, logged_in, tmp_path):
    '''The file's own length: announcing a gigabyte over twenty bytes
    would leave the server waiting for ever.'''
    payload = tmp_path / "upload.tar.gz"
    payload.write_bytes(b"x" * 20)
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")

    logged_in.upload({"url": "https://storage.test/put",
                      "headers": {"content-length": "1073741824"}}, payload)

    assert fake_v1.calls[-1].request.headers["Content-Length"] == "20"


@pytest.mark.parametrize("url,status", [
    ("http://storage.test/put", None),
    ("ftp://storage.test/put", None),
    ("https://storage.test/put", 307),
], ids=["downgrade", "ftp", "redirect"])
def test_an_upload_lands_only_on_https_and_a_2xx(fake_v1, logged_in, url, status):
    '''An https grant never sends the bytes to plain http or another scheme,
    and a redirect is not the object stored.'''
    with open("upload.tar.gz", "wb") as f:
        f.write(b"x")
    if status:
        fake_v1.elsewhere(responses.PUT, url, "", status=status)

    with pytest.raises(RemoteError):
        logged_in.upload({"url": url, "headers": {}}, "upload.tar.gz")

    puts = [c.request.url for c in fake_v1.calls if c.request.method == "PUT"]
    assert puts == ([url] if status else [])


def _answer(method, path, body="", status=200, content_type="application/json",
            headers=None):
    return method, path, body, status, content_type, headers


def _problem(method, path, slug, status, headers=None, **members):
    return _answer(method, path, problem(slug, status, **members), status,
                   "application/problem+json", headers)


GET, POST = responses.GET, responses.POST
JOB = "jobs/01J9-job"
GRANT = "jobs/01J9-job/upload-grant"
HTML = "<html><body><h1>502 Bad Gateway</h1></body></html>"
DONE = _answer(GET, JOB, job_body("completed"))


# `queue` is what the server answers; `asked` is (path, count) of the requests that
# reached it; `slept` the waits, exactly, and `paced` one that must be among them.
@pytest.mark.parametrize("case", [
    # Only an HTML 401 or 403 is the edge refusing; a 3xx other than the hand-off is too.
    pytest.param(dict(call="me", queue=[_answer(GET, "me", "<html>Forbidden</html>", 403,
                                                "text/html")],
                      outcome="EdgeRefused", said=["not the API"]), id="access-layer-html"),
    pytest.param(dict(call="me", queue=[_answer(GET, "me", "", 302, "text/html", {
                          "Location": "https://idp.example/login"})],
                      outcome="EdgeRefused", said=["not the API"], unseen="idp.example"),
                 id="login-redirect"),
    pytest.param(dict(call="artifact", queue=[_answer(
                          GET, "jobs/J/artifacts/A", "", 307,
                          headers={"Location": "https://storage.test/object"})],
                      outcome="EdgeRefused", unseen="storage.test"), id="only-a-303-hands-off"),
    # Any other HTML failure is untyped, and acted on by its status.
    pytest.param(dict(call="me", queue=[_answer(GET, "me", HTML, 502, "text/html")],
                      outcome="ServerProblem", status=502, said=["502"], unsaid=["<html>"]),
                 id="proxy-html-5xx"),
    pytest.param(dict(call="me", queue=[_answer(GET, "me", "", 503, "text/plain")],
                      outcome="ServerProblem", status=503), id="empty-5xx"),
    pytest.param(dict(call="job", queue=[_answer(GET, JOB, "<html>later</html>", 429,
                                                 "text/html", {"Retry-After": "2"}), DONE],
                      slept=[2.0]), id="html-429-waited"),
    pytest.param(dict(call="job", queue=[_answer(GET, JOB, "<html>later</html>", 503,
                                                 "text/html", {"Retry-After": "2"}), DONE],
                      slept=[2.0]), id="html-5xx-waited"),
    pytest.param(dict(call="job", queue=[_answer(GET, JOB, "<html>later</html>", 404,
                                                 "text/html")],
                      outcome="ServerProblem", status=404, slept=[]), id="html-404-answered"),
    # A type outside the registry is untyped: a wait is honoured only where it is named.
    pytest.param(dict(call="job", queue=[_problem(GET, JOB, "brand-new-limit", 429,
                                                  {"Retry-After": "2"}), DONE],
                      slept=[2.0]), id="unknown-type-429-waited"),
    pytest.param(dict(call="job", queue=[_problem(GET, JOB, "brand-new-outage", 503,
                                                  {"Retry-After": "2"}), DONE],
                      slept=[2.0]), id="unknown-type-5xx-waited"),
    pytest.param(dict(call="job", queue=[_problem(GET, JOB, "brand-new-limit", 429)],
                      outcome="ServerProblem", status=429, slept=[]),
                 id="unknown-type-429-no-wait-named"),
    # Not keyed, but repeating it is safe: a wait the 5xx names is honoured.
    pytest.param(dict(call="grant", queue=[
        _answer(POST, GRANT, HTML, 503, "text/html", {"Retry-After": "3"}),
        _answer(POST, GRANT, {"url": "https://storage.test/put", "headers": {}})],
        slept=[3.0], asked=("/v1/" + GRANT, 2)), id="unkeyed-post-5xx-waited"),
    pytest.param(dict(call="grant", queue=[_answer(POST, GRANT, HTML, 503, "text/html")],
                      outcome="ServerProblem", status=503, slept=[],
                      asked=("/v1/" + GRANT, 1)), id="unkeyed-post-5xx-no-wait-named"),
    # A keyed create replays, so a 5xx or a dropped connection is retried with its key.
    pytest.param(dict(call="create", queue=[_answer(POST, "jobs", HTML, 502, "text/html")],
                      outcome="ServerProblem", status=502, said=["502"],
                      asked=("/v1/jobs", 3)), id="keyed-create-gateway"),
    pytest.param(dict(call="create", queue=[requests.ConnectionError("connection reset"),
                                            _answer(POST, "jobs", {"id": "01J9-job"}, 201)],
                      asked=("/v1/jobs", 2)), id="keyed-create-dropped"),
    # A typed 5xx is the server's answer, not a failure worth repeating.
    pytest.param(dict(call="create", queue=[_problem(POST, "jobs", "feature-unsupported",
                                                     501, feature="python.env")],
                      outcome="ServerProblem", status=501, slug="feature-unsupported",
                      slept=[], asked=("/v1/jobs", 1)), id="feature-unsupported-create"),
    pytest.param(dict(call="job", queue=[_problem(GET, JOB, "feature-unsupported", 501,
                                                  {"Retry-After": "2"}, feature="python.env")],
                      outcome="ServerProblem", status=501, slug="feature-unsupported",
                      slept=[], asked=("/v1/" + JOB, 1)), id="feature-unsupported-read"),
    # A run ends on a refusal, or falling through would announce a finished job with
    # nothing in it; a type this client does not know is acted on by its status class.
    pytest.param(dict(call="poll", queue=[_problem(GET, JOB, "not-found", 404)],
                      outcome="RemoteError", said=["01J9-job"]), id="poll-not-found"),
    pytest.param(dict(call="poll", queue=[_problem(GET, JOB, "feature-unsupported", 501)],
                      outcome="RemoteError", said=["01J9-job"]), id="poll-unsupported"),
    pytest.param(dict(call="poll", queue=[_problem(GET, JOB, "brand-new-refusal", 400)],
                      outcome="RemoteError", said=["01J9-job"]), id="poll-unknown-4xx"),
    # A server error or not-ready is waited through, at the refusal's own pace.
    pytest.param(dict(call="poll", queue=[_answer(GET, JOB, HTML, 502, "text/html"), DONE],
                      warned="Bad Gateway", paced=5), id="poll-proxy-html"),
    pytest.param(dict(call="poll", queue=[_problem(GET, JOB, "not-ready", 409), DONE],
                      paced=5), id="poll-not-ready"),
    pytest.param(dict(call="poll", queue=[_problem(GET, JOB, "brand-new-outage", 503), DONE],
                      warned="Brand new outage", paced=5), id="poll-unknown-5xx"),
    pytest.param(dict(call="poll", queue=[_problem(GET, JOB, "brand-new-limit", 429,
                                                   {"Retry-After": "11"}), DONE],
                      paced=11), id="poll-unknown-429"),
    pytest.param(dict(call="poll", queue=[_answer(GET, JOB, "oops", 500, "text/plain")],
                      outcome="RemoteError"), id="poll-never-comes-back"),
])
def test_an_untyped_edge_or_retried_answer_is_acted_on_by_its_status(
        fake_v1, run, no_sleep, caplog, case):
    '''The edge is never the API; an untyped failure goes by its status, and only a read or
    a keyed write is repeated; a typed refusal ends the run and is never retried.'''
    case = {"outcome": None, "status": None, "slug": None, "said": (), "unsaid": (),
            "unseen": None, "asked": None, "slept": None, "paced": None, "warned": None,
            **case}
    for entry in case["queue"]:
        if isinstance(entry, Exception):
            fake_v1._mock.add(responses.POST, fake_v1.url("jobs"), body=entry)
        else:
            method, path, body, status, content_type, headers = entry
            fake_v1.route(method, path, body, status=status, content_type=content_type,
                          headers=headers)
    client = run.client
    call = {"me": client.me, "create": lambda: client.create_job("gcd", "job0"),
            "artifact": lambda: client.fetch_artifact("J", "A", "a.bin"),
            "job": lambda: client.job("01J9-job")[0]["state"],
            "grant": lambda: client.upload_grant("01J9-job", 1, "sha256:" + "0" * 64),
            "poll": lambda: run._poll("01J9-job")}[case["call"]]

    with caplog.at_level("WARNING"):
        if case["outcome"] is None:
            call()
        else:
            with pytest.raises(RemoteError) as raised:
                call()
            error = raised.value
            assert type(error).__name__ == case["outcome"]
            if case["outcome"] == "ServerProblem":
                assert (error.status, error.slug) == (case["status"], case["slug"])
            assert str(error)
            for fragment in case["said"]:
                assert fragment in str(error)
            assert not any(fragment in str(error) for fragment in case["unsaid"])

    if case["warned"]:
        assert case["warned"] in caplog.text
    if case["paced"]:
        assert case["paced"] in no_sleep
    if case["slept"] is not None:
        assert no_sleep == case["slept"]
    if case["unseen"]:
        assert not any(case["unseen"] in c.request.url for c in fake_v1.calls)
    if case["asked"]:
        path, count = case["asked"]
        sent = [c.request for c in fake_v1.calls if c.request.path_url == path]
        assert len(sent) == count
        if sent[0].method == "POST" and "Idempotency-Key" in sent[0].headers:
            assert len({r.headers["Idempotency-Key"] for r in sent}) == 1


def _failed_poll(fake_v1, run, caplog, level="INFO", **body):
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("failed", **body))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with caplog.at_level(level):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")
    return caplog.text


def test_a_failed_run_explains_itself_briefly_and_still_fetches(fake_v1, run, caplog):
    '''Results are fetched on every terminal state: a failed run's log is
    the one most wanted. The next step is the client's, since the type page
    is the same everywhere.'''
    text = _failed_poll(fake_v1, run, caplog,
                        nodes=[node_body("stepone", "failed"), node_body("steptwo", "cancelled")],
                        error={"type": RUN_FAILED, "title": "The run failed"})

    assert "The run failed" in text
    assert "Read the failing node's log" in text
    assert any("artifacts" in call.request.path_url for call in fake_v1.calls)
    rendered = [r.message for r in caplog.records
                if r.levelname == "ERROR" and "run failed" in r.message.lower()]
    assert rendered and len(rendered[0].splitlines()) <= 4


@pytest.mark.parametrize("nodes,error,said,unsaid", [
    # A node's `error` detail is printed beside the node.
    ([node_body("stepone", "failed", error={"type": RUN_FAILED, "title": "The run failed",
                                            "detail": "the node exceeded its time limit"}),
      node_body("steptwo", "cancelled")],
     {"type": RUN_FAILED, "title": "The run failed",
      "detail": "stepone/0 exceeded its time limit"},
     ["stepone/0 failed: the node exceeded its time limit"], ["steptwo/0 failed"]),
    # A flow that dies before its first node has no log to read: the
    # advice comes from the job, and the server's `detail` survives.
    ([node_body("stepone", "cancelled"), node_body("steptwo", "cancelled")],
     {"type": RUN_FAILED, "title": "The run failed",
      "detail": "RuntimeError: git is required to import GitPython"},
     ["No node failed", "git is required"], ["Read the failing node's log"]),
    # Re-running may succeed; the support reference is the job id.
    (None, {"type": "https://siliconcompiler.com/server-errors/run-interrupted",
            "title": "The run was interrupted"},
     ["resubmitting unchanged may work", "job 01J9-job"], []),
], ids=["node-detail", "no-failed-node", "interrupted"])
def test_a_failure_is_explained_from_the_job(fake_v1, run, caplog, nodes, error, said,
                                             unsaid):
    text = _failed_poll(fake_v1, run, caplog, nodes=nodes, error=error)

    assert all(line in text for line in said)
    assert not any(line in text for line in unsaid)


def test_streamed_lines_are_not_prefixed_a_second_time(fake_v1, run, capsys):
    '''A node's log line already says which node it came from.'''
    from siliconcompiler.remote.client.run import _Tails

    tails = _Tails.__new__(_Tails)
    tails._run = run
    tails._logger = run.logger
    tails._stop = __import__("threading").Event()

    tails._write("| INFO     | job0 | route.detailed       | 0 | Running\n")

    printed = capsys.readouterr().err + capsys.readouterr().out
    assert "remote" not in printed


@pytest.fixture
def board(nop_project):
    class Board:
        def is_running(self):
            return True

    nop_project._Project__dashboard = Board()


def test_each_node_is_told_started_and_finished_once(fake_v1, run):
    '''The start is recorded from `started_at`, so a dashboard's timer survives
    reconnects; a node that never started is only told finished.'''
    from siliconcompiler.scheduler.listener import RunListener
    from siliconcompiler.schema_support.record import RecordTime

    heard = []

    class Listener(RunListener):
        def node_started(self, project, step, index):
            heard.append(("started", step))

        def node_finished(self, project, step, index):
            heard.append(("finished", step))

    run.listener = Listener()
    job = job_body("running", nodes=[
        node_body("stepone", "completed", started_at="2026-09-22T10:00:00.000Z",
                  finished_at="2026-09-22T10:01:30.500Z"),
        node_body("steptwo", "running", started_at="2026-09-22T10:01:31.000Z"),
        node_body("stepthree", "skipped")])
    moved = [("stepone", "0", "completed"), ("steptwo", "0", "running"),
             ("stepthree", "0", "skipped")]
    run._tell(job, moved)
    run._tell(job, moved)

    assert heard == [("started", "stepone"), ("finished", "stepone"),
                     ("started", "steptwo"), ("finished", "stepthree")]
    record = run.project.get("record", field="schema")
    assert record.get_recorded_time("steptwo", "0", RecordTime.START) == 1790071291.0


def test_a_dashboard_run_reports_only_what_moved(fake_v1, run, board, caplog):
    '''The board already shows every state; it cannot show the moment.'''
    with caplog.at_level("INFO"):
        run._report(job_body("running"), changed=[("stepone", "0", "running")])

    assert "stepone/0 -> running" in caplog.text
    assert "Job is still running" not in caplog.text


def test_without_a_dashboard_the_whole_table_is_printed(fake_v1, run, caplog):
    with caplog.at_level("INFO"):
        run._report(job_body("running"), changed=[])

    assert "Job is still running" in caplog.text


@pytest.fixture
def floorplan(logged_in, nop_project):
    '''A flow whose order is not its names' order, as a floorplan's is.'''
    from siliconcompiler import Flowgraph

    flow = Flowgraph("fp")
    for step in ("tapcell", "power_grid", "pin_placement"):
        flow.node(step, NOPTask())
    flow.edge("tapcell", "power_grid")
    flow.edge("power_grid", "pin_placement")
    nop_project.set_flow(flow)
    return RemoteRun(nop_project, logged_in)


def test_what_moved_in_one_poll_is_listed_in_the_order_it_moved(floorplan):
    '''Listed by name, a node would start before the one it waits on finished.'''
    seen = {("tapcell", "0"): "running", ("power_grid", "0"): "pending",
            ("pin_placement", "0"): "pending"}
    job = job_body("running", nodes=[
        node_body("pin_placement", "queued"),
        node_body("power_grid", "running", started_at="2026-09-22T10:00:05.200Z"),
        node_body("tapcell", "completed", started_at="2026-09-22T10:00:01.000Z",
                  finished_at="2026-09-22T10:00:05.100Z")])

    assert floorplan._record(job, seen) == [("tapcell", "0", "completed"),
                                            ("power_grid", "0", "running"),
                                            ("pin_placement", "0", "queued")]


def test_where_nothing_says_when_the_flows_order_decides(fake_v1, floorplan, caplog):
    job = job_body("running", nodes=[node_body(step, "pending") for step in
                                     ("pin_placement", "power_grid", "tapcell")])

    assert [step for step, _, _ in floorplan._record(job, {})] == \
        ["tapcell", "power_grid", "pin_placement"]
    with caplog.at_level("INFO"):
        floorplan._report(job, changed=[])
    assert "Pending (3): tapcell/0, power_grid/0, pin_placement/0" in caplog.text


@pytest.mark.parametrize("quiet,features,enabled", [
    (False, [], False),         # a server with no live tail simply does not tail
    (True, None, False),        # quiet means quiet
    (False, None, True),
])
def test_the_tail_is_on_only_where_the_run_is_loud_and_the_server_serves_it(
        fake_v1, run, capabilities, quiet, features, enabled):
    '''The archived log still arrives with the results; the server sets the tail count.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(quiet)
    if features is not None:
        fake_v1.replace(responses.GET, "", dict(capabilities, features=features))

    tails = _Tails(run)

    assert tails._enabled is enabled
    if enabled:
        assert tails._ceiling == 8


def _running_nodes(*steps):
    return {"nodes": [{"step": step, "index": "0", "state": "running",
                       "terminal": False} for step in steps]}


@pytest.fixture
def tails(run, monkeypatch):
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    opened = []
    monkeypatch.setattr(_Tails, "_tail", lambda self, *args: opened.append(args[1]))
    return _Tails, opened


@pytest.mark.parametrize("limit,followed", [
    ({"concurrent_log_streams": 1}, ["stepone"]),
    ({"concurrent_log_streams": 0}, []),
    ({"concurrent_log_streams": 8}, ["stepone", "steptwo"]),
    ({"concurrent_log_streams": None}, ["stepone", "steptwo"]),
    ({}, ["stepone", "steptwo"])],
    ids=["one", "none-allowed", "under-the-limit", "unlimited", "absent"])
def test_the_stream_limit_is_a_count_and_0_opens_none(fake_v1, run, capabilities, tails,
                                                      limit, followed):
    '''0 is none allowed; null is no limit, and so is absent: no bound is invented.'''
    _Tails, opened = tails
    limits = {name: value for name, value in capabilities["limits"].items()
              if name != "concurrent_log_streams"}
    fake_v1.replace(responses.GET, "", dict(capabilities, features=["logs.stream"],
                                            limits={**limits, **limit}))

    tail = _Tails(run)
    tail.follow("j1", _running_nodes("stepone", "steptwo"))
    tail.finish()

    assert sorted(opened) == followed


def test_with_a_job_stream_one_connection_follows_every_node(fake_v1, run, tails,
                                                             monkeypatch):
    '''One stream however wide the flow.'''
    _Tails, opened = tails
    monkeypatch.setattr(_Tails, "_tail_job", lambda self, job_id: opened.append(job_id))

    tail = _Tails(run)
    tail.follow("j1", _running_nodes("stepone", "steptwo"))
    tail.follow("j1", _running_nodes("stepone", "steptwo", "stepthree"))
    tail.finish()

    assert opened == ["j1"]


JOB_STREAM = ("feature-unsupported", 501, {"feature": "logs.stream.job"})
NODE_STREAM = ("feature-unsupported", 501, {"feature": "logs.stream"})
NOT_READY = ("not-ready", 409, {"artifact_kind": "logs"})
NODE = ("stepone", "0")


@pytest.mark.parametrize("refusal,call,started,kept,whole_job,followed", [
    # `logs.stream.job` unsupported is permanent: each running node is followed instead.
    (JOB_STREAM, "job", set(), set(), False, ["stepone"]),
    # `not-ready` is transient for the job's stream and a node's: asked again.
    (NOT_READY, "job", {"job"}, set(), True, None),
    (NOT_READY, "node", {NODE}, set(), True, None),
    # A final refusal is not asked again.
    (("not-found", 404, {}), "node", {NODE}, {NODE}, True, None),
    # No live log on a node's tail stops tailing for the run, for any node.
    (NODE_STREAM, "node", set(), set(), False, []),
], ids=["no-job-stream", "job-not-ready", "node-not-ready", "final-refusal", "no-live-log"])
def test_a_refused_tail_is_asked_again_or_given_up_as_the_refusal_says(
        fake_v1, run, capabilities, monkeypatch, refusal, call, started, kept, whole_job,
        followed):
    '''Only a refusal that can change is asked again; one that cannot ends that kind of
    tail for the run, and never costs the archived log.'''
    from siliconcompiler.remote.client.run import JOB, _Tails

    run.project.option.set_quiet(False)
    if refusal is NODE_STREAM:
        fake_v1.replace(responses.GET, "", dict(capabilities, features=["logs.stream"]))
    slug, status, members = refusal
    refused(fake_v1, responses.GET, "jobs/j1/logs", slug, status, **members)
    tails = _Tails(run)
    tails._started.update({JOB if one == "job" else one for one in started})

    if call == "job":
        tails._tail_job("j1")
    else:
        tails._tail("j1", *NODE)
    assert tails._started == {JOB if one == "job" else one for one in kept}
    assert tails._whole_job is whole_job

    if followed is not None:
        opened = []
        monkeypatch.setattr(_Tails, "_tail", lambda self, *args: opened.append(args[1]))
        tails.follow("j1", _running_nodes("stepone"))
        tails.finish()
        assert opened == followed
        assert len([c for c in fake_v1.calls if "/logs" in c.request.path_url]) == 1


class DeclaresAVersion(__import__("siliconcompiler").Task):
    '''A task of a tool nothing installs, whose setup says which versions.'''

    def tool(self):
        return "sctesttool"

    def task(self):
        return "run"

    def setup(self):
        super().setup()
        self.set_exe("sctesttool", vswitch="--version")
        self.add_version(">=1.2.0,<2")

    def parse_version(self, stdout):
        return stdout.strip()


@pytest.mark.parametrize("task,wanted", [
    ("yosys", {"yosys": []}),
    ("declared", {"sctesttool": [">=1.2.0,<2"]}),
    ("builtin", {}),
])
def test_the_descriptor_names_the_tools_the_flow_needs(fake_v1, logged_in, gcd_nop_project,
                                                       task, wanted):
    '''The descriptor names each tool the flow needs, at the version setup declared (`[]` where
    setup could not run here), so a deployment with no image for one refuses before the upload.
    SiliconCompiler's own nodes name none, or an operator would register a tool no image can claim.
    '''
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.yosys.syn_asic import ASICSynthesis

    flow = Flowgraph("withtools")
    flow.node("run", {"yosys": ASICSynthesis, "declared": DeclaresAVersion,
                      "builtin": NOPTask}[task]())
    gcd_nop_project.set_flow(flow)

    assert _versions(RemoteRun(gcd_nop_project, logged_in))["tools"] == wanted


@pytest.mark.parametrize("declared,sent", [
    (">=24Q3-2011", ">=24.3.2011"),
    (">=24Q3-2011,<27Q1-0", ">=24.3.2011,<27.1.0"),
    # A part with no operator is `==part`, as `check_exe_version` reads it.
    (">=24Q3-2011,26Q3-2418", ">=24.3.2011,==26.3.2418"),
])
def test_a_declared_requirement_is_normalised_before_it_is_sent(declared, sent):
    '''OpenROAD's `>=24Q3-2011` is not PEP 440, and only the driver can
    make it comparable.'''
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    from siliconcompiler.remote.client.run import _normalize_spec
    from siliconcompiler.tools.openroad import OpenROADTask

    spec = _normalize_spec(OpenROADTask(), declared)

    assert spec == sent
    if spec:
        # What the probe stores for a real OpenROAD satisfies it.
        assert Version("26.3.2418") in SpecifierSet(spec)


def test_a_requirement_that_is_not_pep_440_is_dropped_rather_than_refusing_every_image():
    '''`check_exe_version` reads `whatever` as `==whatever`, which matches nothing.'''
    from siliconcompiler import Task
    from siliconcompiler.remote.client.run import _normalize_spec

    assert _normalize_spec(Task(), "whatever") is None


def test_a_development_client_asks_by_prefix_rather_than_exactly():
    '''A dev build's local segment names a commit no image was built from.
    `.*` attaches to the release segment only: `==0.38.10.dev*` is illegal.'''
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import Version

    from siliconcompiler.remote.client.run import _pin

    spec = _pin("0.38.10.dev43+g20db24fa2.d20260924")
    assert spec == "==0.38.10.*"
    matches = SpecifierSet(spec, prereleases=True)
    assert Version("0.38.10.dev7") in matches
    assert Version("0.38.10") in matches
    assert Version("0.38.9") not in matches

    with pytest.raises(InvalidSpecifier):
        SpecifierSet("==0.38.10.dev*")


@pytest.mark.parametrize("version,pin", [
    ("0.38.9", "==0.38.9"), ("1.0.0-RC1", "==1.0.0rc1"), ("v2.1", "==2.1"),
    ("a-local-build", None)])
def test_an_installed_version_is_pinned_in_pep_440_or_not_at_all(version, pin):
    from siliconcompiler.remote.client.run import _pin

    assert _pin(version) == pin


@pytest.mark.parametrize("declared,sent", [
    ("scfakebits>=1.0.0-RC1,<2.0", "<2.0,>=1.0.0rc1"),
    ("scfakebits==1.0.*", "==1.0.*"),
    ("scfakebits===a-local-build", None)])
def test_a_framework_range_is_sent_in_pep_440_or_not_at_all(monkeypatch, declared, sent):
    from siliconcompiler.remote.client.run import _framework_range

    monkeypatch.setattr("siliconcompiler.remote.client.run.metadata.requires",
                        lambda name: [declared])

    assert _framework_range("scfakebits") == sent


def test_a_version_that_is_not_pep_440_is_dropped_with_a_warning(
        fake_v1, logged_in, gcd_design, monkeypatch, caplog):
    '''Sent, it would match nothing; the name stays, at any version.'''
    from importlib import metadata

    from pytasks import RunsATestbench

    installed = metadata.version
    monkeypatch.setattr("siliconcompiler.remote.client.run.metadata.version",
                        lambda name: "a-local-build" if name == "scfakebits"
                        else installed(name))
    open("tb.py", "w").write("")
    run = RemoteRun(_one_node_project(gcd_design, RunsATestbench()), logged_in)

    with caplog.at_level("WARNING"):
        pins = _versions(run)["python"]

    assert pins["scfakebits"] == []
    assert "Dropping the version requirement on scfakebits" in caplog.text


def _members(run, tmp_path):
    '''The upload's members by name, and each regular file's bytes.'''
    import tarfile

    upload = tmp_path / "upload.tar.gz"
    reads = run._read()
    run._pack(upload, run._plan(reads), reads, [])
    with tarfile.open(upload) as tar:
        return {member.name: member for member in tar.getmembers() if member.name}, \
            {member.name: tar.extractfile(member).read() for member in tar.getmembers()
             if member.isfile()}


def _read_manifest(blob, tmp_path):
    from siliconcompiler import Project

    (tmp_path / "sent.pkg.json").write_bytes(blob)
    return Project.from_manifest(filepath=str(tmp_path / "sent.pkg.json"))


def _leftovers(project):
    '''What a job directory that has run before holds.'''
    from siliconcompiler.utils.paths import collectiondir, jobdir, workdir

    root = jobdir(project)
    os.makedirs(root, exist_ok=True)
    for name in ("sc_remote.pkg.json", "remote-job.log", "job.log",
                 "job.20260925-102810.log"):
        with open(os.path.join(root, name), "w") as f:
            f.write("from the last run\n")
    for step in ("stepone", "steptwo"):
        node = workdir(project, step=step, index="0")
        os.makedirs(os.path.join(node, "outputs"), exist_ok=True)
        with open(os.path.join(node, "outputs", "gcd.pkg.json"), "w") as f:
            f.write("{}")
    os.makedirs(collectiondir(project), exist_ok=True)
    with open(os.path.join(collectiondir(project), "gcd.v"), "w") as f:
        f.write("module gcd; endmodule\n")


def _upstream_node(project, step, *, output=None, fetched_from=None, remoteid=None):
    from siliconcompiler.remote.client.results import record_job
    from siliconcompiler.utils.paths import workdir

    outputs = os.path.join(workdir(project, step=step, index="0"), "outputs")
    os.makedirs(outputs, exist_ok=True)
    manifest = {}
    if remoteid:
        manifest = {"record": {"remoteid": {"node": {"*": {"*": {"value": remoteid}}}}}}
    with open(os.path.join(outputs, "gcd.pkg.json"), "w") as f:
        json.dump(manifest, f)
    if fetched_from:
        record_job(os.path.dirname(outputs), fetched_from)
    if output:
        with open(os.path.join(outputs, output), "w") as f:
            f.write("module gcd; endmodule\n")
    return outputs


def _registered_with_credentials(project):
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("ip", "git+https://alice:TOKEN@example.com/ip.git", "v1")
    design.set_dataroot("secret", "git+https+private://alice:TOKEN@example.com/secret.git",
                        "v1")
    project.set("tool", "builtin", "task", "nop", "dataroot", "scripts", "path",
                "https://example.com/scripts.tar.gz?token=TOKEN")


def test_only_the_manifest_and_the_sources_are_uploaded(run, nop_project, tmp_path):
    '''Not the last run's handle, logs or fetched nodes, nor the open `job.log`.'''
    _leftovers(nop_project)

    names = set(_members(run, tmp_path)[0])

    assert "gcd.pkg.json" in names
    assert "sc_collected_files/gcd.v" in names
    assert not {n for n in names if n.endswith(".log")}
    assert "sc_remote.pkg.json" not in names
    assert not {n for n in names if n.startswith(("stepone", "steptwo"))}


def test_the_uploaded_manifest_carries_no_credential(run, nop_project, tmp_path):
    '''Each dataroot's path -- a library's, a private one, a
    task's, the history's -- goes up without userinfo and with query values
    masked; the user's own project and manifest keep what they registered.'''
    from siliconcompiler.remote import owners
    from siliconcompiler.utils.paths import jobdir

    _registered_with_credentials(nop_project)
    nop_project._record_history()
    _leftovers(nop_project)
    own = os.path.join(jobdir(nop_project), "gcd.pkg.json")
    nop_project.write_manifest(own)

    _, blobs = _members(run, tmp_path)
    sent = _read_manifest(blobs["gcd.pkg.json"], tmp_path)

    assert sent.get("library", "gcd", "dataroot", "ip", "path") == \
        "git+https://example.com/ip.git"
    assert sent.get("library", "gcd", "dataroot", "secret", "path") == \
        "git+https+private://example.com/secret.git"
    assert sent.get("tool", "builtin", "task", "nop", "dataroot", "scripts", "path") == \
        "https://example.com/scripts.tar.gz?token=***"
    assert sent.get("history", "job0", "library", "gcd", "dataroot", "ip", "path") == \
        "git+https://example.com/ip.git"
    assert not [name for name, body in blobs.items() if b"TOKEN" in body]

    # Still the set the archive was filtered by.
    assert owners.required(sent) == owners.required(run._read().manifest)
    assert nop_project.get("library", "gcd", "dataroot", "ip", "path") == \
        "git+https://alice:TOKEN@example.com/ip.git"
    with open(own) as f:
        assert "alice:TOKEN" in f.read()


def test_an_upstream_nodes_manifest_goes_up_without_its_credential(
        run, nop_project, tmp_path, monkeypatch):
    '''A `-from` run carries each upstream node's own manifest too, read
    importing nothing it names.'''
    import sys

    _registered_with_credentials(nop_project)
    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    manifest = os.path.join(outputs, "gcd.pkg.json")
    nop_project.write_manifest(manifest)
    with open(manifest) as f:
        written = json.load(f)
    written["library"]["gcd"]["__meta__"]["class"] = "scfake_untrusted/Design"
    with open(manifest, "w") as f:
        json.dump(written, f)
    with open("scfake_untrusted.py", "w") as f:
        f.write("raise SystemExit('imported')\n")
    monkeypatch.syspath_prepend(os.getcwd())
    nop_project.option.add_from("steptwo")

    _, blobs = _members(run, tmp_path)
    upstream = _read_manifest(blobs["stepone/0/outputs/gcd.pkg.json"], tmp_path)

    assert "scfake_untrusted" not in sys.modules
    assert upstream.get("library", "gcd", "dataroot", "ip", "path") == \
        "git+https://example.com/ip.git"
    assert blobs["stepone/0/outputs/gcd.vg"] == b"module gcd; endmodule\n"
    assert not [name for name, body in blobs.items() if b"TOKEN" in body]
    with open(os.path.join(outputs, "gcd.pkg.json")) as f:
        assert "alice:TOKEN" in f.read()


def test_a_run_from_part_way_sends_the_outputs_it_starts_from_as_they_are(
        run, nop_project, tmp_path):
    '''`-from steptwo`: stepone's outputs, manifest unchanged, and nothing else
    of either node. An upload keeps links: a hard link is a tar hard link to
    the first, a symlink to an archived file a link, and a dangling one is
    left out.'''
    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    os.makedirs(os.path.join(os.path.dirname(outputs), "inputs"), exist_ok=True)
    os.link(os.path.join(outputs, "gcd.vg"), os.path.join(outputs, "hard.vg"))
    os.symlink("gcd.vg", os.path.join(outputs, "soft.vg"))
    os.symlink("nothing-there", os.path.join(outputs, "dangling.vg"))
    nop_project.option.add_from("steptwo")
    with open(os.path.join(outputs, "gcd.pkg.json"), "rb") as f:
        written = f.read()

    members, blobs = _members(run, tmp_path)

    assert blobs["stepone/0/outputs/gcd.pkg.json"] == written
    assert members["stepone/0/outputs/gcd.vg"].isfile()
    assert blobs["stepone/0/outputs/gcd.vg"] == b"module gcd; endmodule\n"
    hard = members["stepone/0/outputs/hard.vg"]
    assert hard.islnk() and hard.linkname == "stepone/0/outputs/gcd.vg"
    soft = members["stepone/0/outputs/soft.vg"]
    assert soft.issym() and soft.linkname == "gcd.vg"
    assert "stepone/0/outputs/dangling.vg" not in members
    assert not {n for n in members if n.startswith(("stepone/0/inputs", "steptwo"))}
    assert run._upstream()[1] == []                  # nothing to continue from


@pytest.mark.parametrize("recorded", [
    {"fetched_from": "01a0e000-0000-7000-8000-000000000001"},
    {},
    {"remoteid": "01a0e000-0000-7000-8000-00000000beef"},
], ids=["fetched", "local-run", "manifest-remoteid"])
def test_an_upstream_node_without_its_outputs_is_continued_from_its_recorded_job(
        run, nop_project, tmp_path, recorded):
    '''Only its manifest is here: the job it was recorded fetched from is
    named, and nothing of it packed. With none recorded it is refused: a
    manifest's own `remoteid` is server-written, never the job continued from.'''
    _leftovers(nop_project)
    _upstream_node(nop_project, "stepone", **recorded)
    nop_project.option.add_from("steptwo")

    if "fetched_from" not in recorded:
        with pytest.raises(RemoteError, match="stepone/0"):
            _members(run, tmp_path)
        return

    names = set(_members(run, tmp_path)[0])
    assert run._upstream()[1] == [{"step": "stepone", "index": "0",
                                   "job_id": recorded["fetched_from"]}]
    assert not {n for n in names if n.startswith("stepone")}


@pytest.mark.parametrize("link,page", [
    ('</server-errors/not-found>; rel="help"', "https://sc-server.test/server-errors/"),
    (None, "https://siliconcompiler.com/server-errors/"),
], ids=["servers-own", "public"])
def test_a_refusal_prints_the_page_the_server_names(fake_v1, logged_in, link, page):
    '''A server serving its own copy of the `type` pages says so; that copy
    is printed, and remembered for a job's own error.'''
    refused(fake_v1, responses.GET, "jobs/01J9-job", "not-found", 404,
            headers={"Link": link} if link else None)

    with pytest.raises(RemoteError) as raised:
        logged_in.job("01J9-job")

    assert f"{page}not-found" in str(raised.value)
    if link:
        assert "siliconcompiler.com/server-errors" not in str(raised.value)
        assert logged_in.transport.help_pages == page


def test_a_failed_jobs_reason_points_at_the_servers_page():
    from siliconcompiler.remote.client.run import _why_it_failed

    job = {"state": "failed", "progress": {"failed_count": 1},
           "error": {"type": RUN_FAILED, "title": "The run failed",
                     "detail": "place/0 exited 1"}}

    said = _why_it_failed(job, "https://sc-server.test/server-errors/")

    assert "https://sc-server.test/server-errors/run-failed" in said


def _acme(project, tag):
    from siliconcompiler import PDK

    pdk = PDK("acme")
    # Remote, so it would not go up on its own. Its own ref: the path cache
    # is process-wide, keyed by source and ref.
    pdk.set_dataroot("acme", "https://gitlab.example/acme/pdk/archive/", tag=tag)
    with pdk.active_dataroot("acme"):
        pdk.set("package", "doc", "datasheet", "notes.txt")
    project.add_dep(pdk)


ASKED_ACME = {"upload_sources": [
    {"kind": "dataroot", "keypath": ["library", "acme", "dataroot", "acme"]}]}


def test_a_source_the_server_asked_for_at_create_goes_up_with_the_job(
        fake_v1, run, nop_project, tmp_path, caplog, monkeypatch):
    '''This machine resolves it with its own credentials -- here, a copy only
    it has -- and puts it in the archive.'''
    import shutil

    from siliconcompiler.package.https import HTTPResolver

    (tmp_path / "ip").mkdir()
    (tmp_path / "ip" / "notes.txt").write_text("private repo contents\n")
    _acme(nop_project, "v1")
    monkeypatch.setattr(HTTPResolver, "resolve_remote", lambda self: shutil.copytree(
        tmp_path / "ip", self.cache_path, dirs_exist_ok=True))
    routes_for_a_submit(fake_v1, **ASKED_ACME)

    with caplog.at_level("INFO"):
        run._start()

    assert "The server asked for the dataroot library,acme,dataroot,acme" in caplog.text
    assert "pdk acme (library,acme,dataroot,acme):" in caplog.text


def test_a_source_this_machine_cannot_reach_either_fails_before_upload(
        fake_v1, run, nop_project, monkeypatch):
    '''Upload nothing, and cancel saying which and why.'''
    from siliconcompiler.package.https import HTTPResolver

    def unreachable(self):
        raise FileNotFoundError("404 from gitlab.example")

    _acme(nop_project, "v9-unreachable")
    monkeypatch.setattr(HTTPResolver, "resolve_remote", unreachable)
    routes_for_a_submit(fake_v1, **ASKED_ACME)
    _cancelled(fake_v1)
    said = ("library,acme,dataroot,acme: it cannot be fetched here either: 404 from "
            "gitlab.example")

    with pytest.raises(RemoteError, match=f"the dataroot {said}"):
        run._start()

    assert not [c for c in fake_v1.calls if "upload-grant" in c.request.path_url]
    cancel, = _cancels(fake_v1)
    assert said in json.loads(cancel.body)["reason"]


GCD_ROOT = {"kind": "dataroot", "keypath": ["library", "gcd", "dataroot", "gcd-pytest-example"]}


def test_a_job_sent_back_is_answered_with_only_what_was_asked(fake_v1, run):
    '''A follow-up archive of the asked-for dataroots alone, its own grant,
    and submit again.'''
    import io
    import tarfile

    route_granted(fake_v1)
    route_submitted(fake_v1)

    run._send_asked("01J9-job", [GCD_ROOT])

    with tarfile.open(fileobj=io.BytesIO(put_body(fake_v1))) as tar:
        names = tar.getnames()
    assert names and all(name.startswith("sc_collected_files") for name in names)
    assert any(name.endswith(".v") for name in names)
    assert not any(name.endswith(".pkg.json") for name in names)


def test_a_follow_up_packed_again_repeats_its_size_and_digest(fake_v1, logged_in,
                                                              nop_project):
    '''A retry must repeat what its first grant fixed, so the archive carries no
    time or owner of its own.'''
    route_granted(fake_v1)
    route_submitted(fake_v1)

    for _ in range(2):
        RemoteRun(nop_project, logged_in)._send_asked("01J9-job", [GCD_ROOT])

    grants = [json.loads(c.request.body) for c in fake_v1.calls
              if c.request.path_url.endswith("/upload-grant")]
    assert len(grants) == 2 and grants[0] == grants[1]


@pytest.mark.parametrize("put,cancelled", [(200, True), (403, False)],
                         ids=["sent", "not-sent"])
def test_asked_again_for_what_was_sent_cancels_the_job(fake_v1, run, put, cancelled):
    '''Sent, this machine has nothing else to send, so the job is never left
    waiting; an answer whose upload failed was not sent, and goes again.'''
    route_granted(fake_v1, put_status=put)
    route_submitted(fake_v1)
    _cancelled(fake_v1)

    for _ in range(2):
        try:
            run._send_asked("01J9-job", [GCD_ROOT])
        except RemoteError as e:
            error = e

    said = "the dataroot library,gcd,dataroot,gcd-pytest-example: it was sent, and " \
        "asked for again"
    assert (said in str(error)) == cancelled
    reasons = [json.loads(cancel.body)["reason"] for cancel in _cancels(fake_v1)]
    assert len(reasons) == cancelled and all(said in reason for reason in reasons)


@pytest.mark.parametrize("owner", ["01J9-user", "01J9-teammate"])
def test_only_its_owner_answers_a_job_sent_back(fake_v1, run, no_sleep, caplog, owner):
    '''Anybody else is told the owner must, and never cancels it. An answer
    waits out the job's `Retry-After` before it is read again.'''
    run.client.credentials.set_user_id("01J9-user")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "awaiting_input", nodes=[], owner={"id": owner, "name": "Someone"},
        upload_sources=[GCD_ROOT]), headers={"Retry-After": "9"})
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))
    route_granted(fake_v1)
    route_submitted(fake_v1)

    with caplog.at_level("WARNING"):
        run._poll("01J9-job")

    mine = owner == "01J9-user"
    assert bool([c for c in fake_v1.calls if c.request.path_url.endswith("/submit")]) == mine
    assert ("waits for its owner to send the dataroot" in caplog.text) != mine
    assert not _cancels(fake_v1)
    assert 9 in no_sleep


@pytest.mark.parametrize("state,polls", [("staging", 2), ("queued", 1)])
def test_leaving_a_job_not_yet_queued_warns_once(run, monkeypatch, caplog, state, polls):
    '''The server may still ask this machine for a source, so
    leaving a job before it is queued warns, and a second interrupt leaves.'''
    import logging

    asked = []

    def poll(job_id):
        asked.append(job_id)
        run._last_state = state
        raise KeyboardInterrupt

    monkeypatch.setattr(run, "_poll", poll)
    run.logger.propagate = True

    with caplog.at_level(logging.WARNING), pytest.raises(KeyboardInterrupt):
        run._watch("01J9-job")

    assert len(asked) == polls
    assert ("not fully submitted" in caplog.text and "Ctrl-C again" in caplog.text) == \
        (state == "staging")


@pytest.mark.parametrize("refusal,said", [
    # A private task root this server does not hold.
    (problem("resource-unavailable", 422, resource="acme_sim",
             keypath=["tool", "acme_sim", "task", "run", "dataroot", "scripts"],
             detail="the private dataroot tool,acme_sim,task,run,dataroot,scripts is not "
                    "held by this server"),
     ["keypath: tool,acme_sim,task,run,dataroot,scripts",
      "the private dataroot tool,acme_sim,task,run,dataroot,scripts is not held by this "
      "server"]),
    (problem("invalid-request", 400,
             detail="a source's keypath is a library's dataroot, [\"library\", name, "
                    "\"dataroot\", root], or a task's"),
     ["a source's keypath is a library's dataroot"]),
    (problem("software-unavailable", 422, reason="unavailable", unresolved=[]),
     ["reason: unavailable"]),
], ids=["private-root", "keypath-shape", "software"])
def test_a_refusal_at_create_packs_nothing(fake_v1, run, monkeypatch, refusal, said):
    '''Created before anything is collected or packed, so a refusal there costs nothing.'''
    monkeypatch.setattr(RemoteRun, "_collect", lambda self, *args, **kwargs:
                        pytest.fail("collected"))
    monkeypatch.setattr(RemoteRun, "_pack", lambda self, *args: pytest.fail("packed"))
    fake_v1.route(responses.POST, "jobs", refusal, status=refusal["status"],
                  content_type="application/problem+json")

    with pytest.raises(RemoteError) as raised:
        run._start()

    assert all(line in str(raised.value) for line in said), str(raised.value)
    assert not any("upload-grant" in call.request.url for call in fake_v1.calls)


@pytest.mark.parametrize("software,versions,said", [
    # A requirement the map meets, or a name or bucket it does not list, goes unsaid.
    ({"python": {"siliconcompiler": ["1.0.0", "1.1.0"]}},
     {"python": {"siliconcompiler": ["==1.1.*"]}}, []),
    ({"python": {"siliconcompiler": ["1.0.0"]}}, {"tools": {"yosys": ["==1.0"]}}, []),
    ({"tools": {"yosys": ["0.40"]}}, {"tools": {"yosys": []}}, []),
    ({"python": {"Scfake_Data": ["2.0"]}}, {"python": {"scfake-data": ["==2.0"]}}, []),
    ({"python": {"siliconcompiler": ["1.0.0"]}}, {"python": {"cocotb": []}}, []),
    # sc-server's own: it lists no tool, and runs what the node has.
    ({"tools": {}}, {"tools": {"yosys": [], "openroad": [">=3"]}}, []),
    # A listed name at no version allowed, in each bucket, said together.
    ({"python": {"siliconcompiler": ["1.0.0"]}}, {"python": {"siliconcompiler": ["==2.0.0"]}},
     ["Python package siliconcompiler ==2.0.0 (offered: 1.0.0)"]),
    ({"tools": {"openroad": ["2.0.1"]}}, {"tools": {"yosys": [], "openroad": [">=3", "<1"]}},
     ["tool openroad >=3 or <1 (offered: 2.0.1)"]),
    ({"interpreter": {"python": ["3.12.4"]}}, {"interpreter": {"python": ["==3.14.*"]}},
     ["interpreter python ==3.14.* (offered: 3.12.4)"]),
], ids=["met", "bucket-unlisted", "any-version", "name-normalised", "name-unlisted",
        "no-tools-listed", "version-unmet", "tools-unmet", "interpreter-unmet"])
def test_a_listed_version_the_run_does_not_allow_is_warned_of(
        fake_v1, run, capabilities, caplog, software, versions, said):
    '''`GET /v1`'s `software` against the run's requirements: said, never refused,
    since the server's answer at create is the binding one.'''
    fake_v1.replace(responses.GET, "", dict(capabilities, software=software))

    run._warn_unmet(versions)

    assert all(line in caplog.text for line in said), caplog.text
    assert ("lists other versions" in caplog.text) is bool(said)
    assert "yosys" not in caplog.text


def test_a_run_the_listed_software_does_not_allow_is_still_submitted(
        fake_v1, run, capabilities, no_sleep, caplog):
    '''This machine's SiliconCompiler is not a version listed: said, and created.'''
    fake_v1.replace(responses.GET, "", dict(
        capabilities, software={"python": {"siliconcompiler": ["0.0.1"]}, "tools": {}}))
    routes_for_a_submit(fake_v1)

    run._start()

    assert "Python package siliconcompiler" in caplog.text
    assert creates(fake_v1)


@pytest.mark.parametrize("reason,detail,said", [
    ("unrequested_member", "stray.txt is not something a first archive carries",
     ["stray.txt"]),
    # The refusal `sc-server` raises for a manifest carrying userinfo.
    ("credential", "the manifest carries userinfo in the path of 1 dataroot(s): "
                   "library,gcd,dataroot,ip",
     ["library,gcd,dataroot,ip", "reason: credential", "through the environment"]),
])
def test_a_202_then_a_rejected_job_reads_the_refusal_from_the_poll(
        fake_v1, run, no_sleep, caplog, reason, detail, said):
    '''Submit only matched the digest; what staging found arrives on the job.'''
    route_created(fake_v1)
    route_granted(fake_v1)
    route_submitted(fake_v1, nodes=[])
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "rejected", nodes=[], error={
            "type": "https://siliconcompiler.com/server-errors/archive-rejected",
            "title": "Archive rejected", "status": 422, "reason": reason, "detail": detail}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with pytest.raises(RemoteError, match="rejected"):
        run.run()

    assert all(line in caplog.text for line in said)


def test_in_progress_and_a_slot_limit_are_waited_out_with_the_same_key(
        fake_v1, run, no_sleep, caplog):
    '''Any `limit` that refills is waited out, not only the two named slots.'''
    refused(fake_v1, responses.POST, "jobs", "job-state-conflict", 409,
            headers={"Retry-After": "2"}, reason="in_progress")
    refused(fake_v1, responses.POST, "jobs", "limit-exceeded", 429,
            headers={"Retry-After": "3"}, limit="pending_uploads", job_ids=["01J9-old"])
    refused(fake_v1, responses.POST, "jobs", "limit-exceeded", 429,
            headers={"Retry-After": "4"}, limit="compute_seconds")
    routes_for_a_submit(fake_v1)

    with caplog.at_level("WARNING"):
        run._start()

    creates = [call.request for call in fake_v1.calls
               if call.request.method == "POST" and call.request.path_url == "/v1/jobs"]
    assert len(creates) == 4
    assert len({request.headers["Idempotency-Key"] for request in creates}) == 1
    assert {2.0, 3.0, 4.0} <= set(no_sleep)
    assert "01J9-old" in caplog.text
    assert "compute_seconds limit is reached" in caplog.text


@pytest.mark.parametrize("second,cancelled", [(200, False), (403, True)],
                         ids=["retried", "failed-twice"])
def test_a_failed_upload_starts_over_under_a_reissued_grant(fake_v1, run, second,
                                                            cancelled):
    '''Once, for the same size and digest. Only an upload that fails again
    cancels the job, which would otherwise hold a slot until abandoned.'''
    route_created(fake_v1)
    route_granted(fake_v1, put_status=403)
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "", status=second,
                      content_type="text/plain")
    route_submitted(fake_v1)
    _cancelled(fake_v1)

    if cancelled:
        with pytest.raises(RemoteError):
            run._start()
    else:
        assert run._start() == "01J9-job"

    grants = [json.loads(c.request.body) for c in fake_v1.calls
              if c.request.path_url.endswith("/upload-grant")]
    assert len(grants) == 2 and grants[0] == grants[1]
    assert len(_cancels(fake_v1)) == cancelled
    assert bool(run.project.get('record', 'remoteid')) != cancelled
    if cancelled:
        assert json.loads(_cancels(fake_v1)[0].body)["reason"].startswith(
            "cancelled from SiliconCompiler")


def test_an_upload_that_does_not_match_its_digest_goes_up_again(fake_v1, run):
    '''The archive whose digest the grant bound, then a second submit with a
    fresh key; the job is kept.'''
    route_created(fake_v1)
    route_granted(fake_v1)
    refused(fake_v1, responses.POST, "jobs/01J9-job/submit", "upload-digest-mismatch", 422)
    route_submitted(fake_v1)

    run._start()

    puts = [c for c in fake_v1.calls if c.request.path_url == "/put"]
    submits = [c.request for c in fake_v1.calls if c.request.path_url.endswith("/submit")]
    assert len(puts) == 2 and len(submits) == 2
    assert submits[0].headers["Idempotency-Key"] != submits[1].headers["Idempotency-Key"]
    assert not _cancels(fake_v1)


@pytest.mark.parametrize("slug,status,state,outcome", [
    ("terms-not-accepted", 403, None, "cancelled"),
    ("brand-new-outage", 503, None, "cancelled"),
    ("job-state-conflict", 409, "staging", "submitted"),
    ("job-state-conflict", 409, "awaiting_input", "cancelled"),
])
def test_a_refused_submit_cancels_the_job_unless_it_was_submitted(
        fake_v1, run, no_sleep, slug, status, state, outcome):
    '''Nothing would submit it later, so it is cancelled rather than left holding a
    slot; a state conflict is read again, and a job already staging was submitted.'''
    route_created(fake_v1)
    route_granted(fake_v1)
    refused(fake_v1, responses.POST, "jobs/01J9-job/submit", slug, status)
    if state:
        fake_v1.route(responses.GET, "jobs/01J9-job", job_body(state, nodes=[]))
    _cancelled(fake_v1)

    if outcome == "submitted":
        assert run._start() == "01J9-job"
    else:
        with pytest.raises(RemoteError):
            run._start()

    assert len(_cancels(fake_v1)) == (outcome == "cancelled")
    assert bool(run.project.get('record', 'remoteid')) == (outcome != "cancelled")


@pytest.mark.parametrize("answer,said", [(202, "Job submitted"), (409, "holds no upload")])
def test_a_resumed_run_submits_the_upload_a_waiting_job_holds(fake_v1, run, no_sleep, caplog,
                                                              answer, said):
    '''Left `awaiting_input` with its upload, as by a run killed before its submit,
    it is submitted by its owner; a 409 means it holds none, and it is not cancelled
    from here.'''
    run.client.credentials.set_user_id("01J9-user")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("awaiting_input", nodes=[]))
    if answer == 202:
        route_submitted(fake_v1)
        fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))
        with caplog.at_level("INFO"):
            run._watch("01J9-job")
        assert said in caplog.text
    else:
        refused(fake_v1, responses.POST, "jobs/01J9-job/submit", "job-state-conflict", 409)
        with pytest.raises(RemoteError, match=said):
            run._watch("01J9-job")

    assert not _cancels(fake_v1)


def test_an_interrupt_before_submit_cancels_the_job(fake_v1, run, monkeypatch):
    route_created(fake_v1)
    _cancelled(fake_v1)

    def interrupted(self, *args):
        raise KeyboardInterrupt

    monkeypatch.setattr(RemoteRun, "_pack", interrupted)

    with pytest.raises(KeyboardInterrupt):
        run._start()

    assert "interrupted" in json.loads(_cancels(fake_v1)[0].body)["reason"]


TYPES = "https://siliconcompiler.com/server-errors/"


def test_an_asic_project_with_no_pdk_stops_before_create(fake_v1, logged_in, gcd_design):
    from siliconcompiler import ASIC

    project = ASIC(gcd_design)
    project.add_fileset("rtl")

    with pytest.raises(RemoteError, match="sets no PDK"):
        RemoteRun(project, logged_in)._start()

    assert not any(call.request.path_url == "/v1/jobs" for call in fake_v1.calls)


def test_a_task_class_no_package_provides_stops_before_create(fake_v1, run, monkeypatch):
    from siliconcompiler.remote import owners

    monkeypatch.setattr(owners, "module_distributions", lambda: {})

    with pytest.raises(RemoteError, match="installed package"):
        run._start()


def _three_nodes(project, both=False, last=NOPTask):
    '''stepone -> steptwo -> stepthree, run from stepthree, which runs ``last``;
    with ``both``, stepthree reads stepone too.'''
    from siliconcompiler import Flowgraph

    flow = Flowgraph("passflow")
    for step in ("stepone", "steptwo", "stepthree"):
        flow.node(step, (last if step == "stepthree" else NOPTask)())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    if both:
        flow.edge("stepone", "stepthree")
    project.set_flow(flow)
    project.option.add_from("stepthree")
    return project


def _passed_through(project, hard=True):
    '''steptwo passed stepone's output through as `link_symlink_copy` does:
    `outputs/x` -> `inputs/x`, a hard link or symlink to the upstream file.'''
    from siliconcompiler.utils.paths import workdir

    upstream = _upstream_node(project, "stepone", output="gcd.vg")
    two = workdir(project, step="steptwo", index="0")
    _upstream_node(project, "steptwo")
    os.makedirs(os.path.join(two, "inputs"), exist_ok=True)
    link = os.link if hard else os.symlink
    link(os.path.join(upstream, "gcd.vg"), os.path.join(two, "inputs", "gcd.vg"))
    os.symlink("../inputs/gcd.vg", os.path.join(two, "outputs", "gcd.vg"))
    return two


@pytest.mark.parametrize("hard", [True, False], ids=["hard-linked", "symlinked"])
def test_a_chain_into_a_node_also_packed_is_one_link(run, nop_project, tmp_path, hard):
    _three_nodes(nop_project, both=True)
    _passed_through(nop_project, hard=hard)

    members, _ = _members(run, tmp_path)

    link = members["steptwo/0/outputs/gcd.vg"]
    assert link.issym()
    assert link.linkname == "../../../stepone/0/outputs/gcd.vg"
    assert members["stepone/0/outputs/gcd.vg"].isfile()


def test_a_chain_into_a_node_not_packed_is_the_file_once(run, nop_project, tmp_path):
    '''Stored at its first appearance (sorted: `again.vg`), and a later link
    points at that copy.'''
    _three_nodes(nop_project)
    two = _passed_through(nop_project, hard=False)
    os.symlink("../../../stepone/0/outputs/gcd.vg", os.path.join(two, "outputs", "again.vg"))

    members, contents = _members(run, tmp_path)

    assert not any(name.startswith("stepone") for name in members)
    again, first = members["steptwo/0/outputs/again.vg"], "steptwo/0/outputs/gcd.vg"
    assert again.isfile() and contents["steptwo/0/outputs/again.vg"] == \
        b"module gcd; endmodule\n"
    assert members[first].issym() and members[first].linkname == "again.vg"


def test_a_link_out_of_the_build_directory_is_stored_once_where_it_first_appears(
        run, nop_project, tmp_path):
    '''To a file or a directory: its home is not in the archive, so the first
    name holds the bytes and a later one points at it.'''
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "cells.lib").write_text("the foundry's own\n")
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    os.symlink(str(outside / "cells.lib"), os.path.join(outputs, "lib"))
    os.symlink(str(outside), os.path.join(outputs, "libs"))
    nop_project.option.add_from("steptwo")

    members, contents = _members(run, tmp_path)

    assert contents["stepone/0/outputs/lib"] == b"the foundry's own\n"
    assert members["stepone/0/outputs/libs"].isdir()
    again = members["stepone/0/outputs/libs/cells.lib"]
    assert again.islnk() and again.linkname == "stepone/0/outputs/lib"


def test_a_link_into_the_archive_points_at_its_home_from_its_place_in_the_archive(
        run, nop_project, tmp_path):
    '''A collected file is not stored again; a link inside a directory stored at
    a link's place is relative to that place, not to where the directory is here.'''
    from siliconcompiler.utils.paths import collectiondir, jobdir

    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    nop_project.option.add_from("steptwo")
    os.symlink(os.path.relpath(os.path.join(collectiondir(nop_project), "gcd.v"), outputs),
               os.path.join(outputs, "top.v"))
    deep = os.path.join(jobdir(nop_project), "elsewhere", "in", "the", "job")
    os.makedirs(deep)
    os.symlink(os.path.relpath(os.path.join(outputs, "gcd.vg"), deep),
               os.path.join(deep, "back.vg"))
    os.symlink(os.path.relpath(deep, outputs), os.path.join(outputs, "d"))

    members, _ = _members(run, tmp_path)

    assert members["stepone/0/outputs/top.v"].linkname == \
        "../../../sc_collected_files/gcd.v"
    assert members["stepone/0/outputs/d/back.vg"].linkname == "../gcd.vg"


@pytest.mark.parametrize("target", ["../../../stepone/0/outputs/gcd.vg", "/nowhere/gcd.vg"],
                         ids=["into-a-node", "out-of-the-build"])
def test_a_dangling_upstream_link_stops_the_run_before_create(run, nop_project, target):
    '''A link to a node this machine never fetched is a missing file.'''
    from siliconcompiler.utils.paths import workdir

    _three_nodes(nop_project)
    two = workdir(nop_project, step="steptwo", index="0")
    _upstream_node(nop_project, "steptwo", output="own.vg")
    os.symlink(target, os.path.join(two, "outputs", "gcd.vg"))

    with pytest.raises(RemoteError, match="steptwo/0/outputs/gcd.vg is a link to"):
        run._check_dangling()


class ReadsTheNetlist(NOPTask):
    '''A task whose setup declares the input it reads.'''

    def task(self):
        return "readsthenetlist"

    def setup(self):
        super().setup()
        self.add_input_file("gcd.vg")


class ReadsTheSuffixedNetlist(ReadsTheNetlist):
    '''A task that declares the input under the name of the node it comes from.'''

    def setup(self):
        NOPTask.setup(self)
        self.add_input_file(self.compute_input_file_node_name("gcd.vg", "steptwo", "0"))


@pytest.mark.parametrize("last,steptwo,refused", [
    (ReadsTheNetlist, {"output": "own.vg"}, True),
    (ReadsTheNetlist, {"output": "gcd.vg"}, False),
    (ReadsTheNetlist, {"fetched_from": "01a0e000-0000-7000-8000-000000000001"}, False),
    (ReadsTheSuffixedNetlist, {"output": "gcd.vg"}, False),
], ids=["lacking", "holding", "continued", "node-suffixed"])
def test_an_input_the_outputs_packed_here_lack_stops_the_run_before_create(
        run, nop_project, last, steptwo, refused):
    '''Read from the setup worked out here; a node reading results continued
    from another job is not checked, since they are not here.'''
    _three_nodes(nop_project, both=True, last=last)
    _upstream_node(nop_project, "stepone", output="own.vg")
    _upstream_node(nop_project, "steptwo", **steptwo)

    if refused:
        with pytest.raises(RemoteError, match="stepthree/0 reads an input"):
            run._check_unfed(run._read().worked.unfed)
    else:
        run._check_unfed(run._read().worked.unfed)


def test_an_asked_dataroot_is_matched_on_its_owner_and_its_name(run, nop_project, tmp_path):
    '''Never the name alone: many objects use the default, `root`.'''
    from siliconcompiler import StdCellLibrary

    for name in ("alib", "blib"):
        lib = StdCellLibrary(name)
        (tmp_path / name).mkdir()
        (tmp_path / name / f"{name}.pdf").write_text(name)
        lib.set_dataroot("root", str(tmp_path / name))
        with lib.active_dataroot("root"):
            lib.set("package", "doc", "datasheet", f"{name}.pdf")
        nop_project.add_dep(lib)

    collection = tmp_path / "collected"
    run._collect(run._read(),
                 [{"kind": "dataroot", "keypath": ["library", "alib", "dataroot", "root"]}],
                 directory=str(collection), only_asked=True)

    found = {name for _, _, names in os.walk(collection) for name in names}
    assert "alib.pdf" in found and "blib.pdf" not in found


def test_the_poll_line_reads_its_time_and_reason_from_transitions():
    '''From the last `transitions` entry; a live staging phase wins.'''
    import time
    from datetime import datetime, timezone

    from siliconcompiler.remote.client.run import _state_line

    entered = datetime.fromtimestamp(time.time() - 300, tz=timezone.utc) \
        .strftime("%Y-%m-%dT%H:%M:%S.000Z")
    line = _state_line({"state": "cancelling", "transitions": [
        {"state": "created", "at": "2026-09-29T10:00:00.000Z"},
        {"state": "cancelling", "at": entered, "reason": "wrong corner"}]})

    assert line.startswith("cancelling for 5m") and line.endswith(", wrong corner")
    assert _state_line({"state": "staging", "state_reason": "fetching sources",
                        "transitions": [{"state": "staging", "at": entered}]}) \
        .endswith(", fetching sources")
    # A node a cancel stopped carries the cancel's reason.
    assert _state_line({"state": "cancelled", "nodes": [{"state_reason": "superseded"}],
                        "transitions": [{"state": "cancelled", "at": entered}]}) \
        .endswith(", superseded")


def test_the_runs_own_lines_print_server_text_without_control_characters(run, caplog):
    from siliconcompiler.remote.client.run import _named

    caplog.set_level("INFO")
    run._report(job_body("running\x1b]0;owned\x07",
                         nodes=[node_body("step\x07one", "running\x1b[2J")]))
    named = _named([{"kind": "dataroot", "keypath": ["library", "a\x1b]0;x\x07"]},
                    {"kind": "python", "name": "pkg\x9b2J"}])

    for text in (caplog.text, named):
        assert not any(c in text for c in ("\x07", "\x1b]", "\x1b[2J", "\x9b")), text


def test_a_deleted_job_says_why_it_stopped_and_fetches_nothing(fake_v1, run, caplog):
    '''Nothing of a deleted job but its object is readable; the cancel's reason
    is its last transition's.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "cancelled", nodes=[],
        transitions=[{"state": "cancelled", "at": "2026-09-22T10:05:00.000Z",
                      "reason": "wrong corner"}],
        deleted_at="2026-09-23T10:00:00.000Z", deleted_reason="deleted by A User",
        archived_at="2026-09-22T11:00:00.000Z"))

    with caplog.at_level("INFO"), pytest.raises(RemoteError):
        run._poll("01J9-job")

    assert "Remote job cancelled: wrong corner" in caplog.text
    assert "deleted at 2026-09-23T10:00:00.000Z (deleted by A User)" in caplog.text
    assert "archived at 2026-09-22T11:00:00.000Z" in caplog.text
    assert not [c for c in fake_v1.calls if "/artifacts" in c.request.path_url]


@pytest.mark.parametrize("text,said", [
    ("404 from https://user:pw@host/x.tgz", "404 from https://host/x.tgz"),
    ("no https://host/x.tgz?token=abc&v=2 here", "no https://host/x.tgz?token=***&v=*** here"),
])
def test_a_scrubbed_message_carries_no_credential(text, said):
    '''Userinfo and query values are masked as a source's are, wherever the URL sits.'''
    from siliconcompiler.remote.client.run import _scrubbed

    assert _scrubbed(text) == said
