import hashlib
import json
import os

import pytest
import responses

from siliconcompiler.remote import RemoteError, ServerProblem
from siliconcompiler.remote.client.run import RemoteRun, node_status
from siliconcompiler.tools.builtin.nop import NOPTask

from conftest import problem


RUN_FAILED = "https://siliconcompiler.com/server-errors/run-failed"


def _node(step, state, **extra):
    node = {"step": step, "index": "0", "state": state,
            "terminal": state in ("completed", "failed", "skipped", "cancelled"),
            "started_at": None, "finished_at": None, "exit_code": None,
            "error": None}
    node.update(extra)
    return node


def job_body(state="running", nodes=None, terminal=None, **extra):
    '''A job object shaped the way the v1 API publishes it.'''
    nodes = nodes if nodes is not None else [_node("stepone", "running"),
                                             _node("steptwo", "pending")]
    if terminal is None:
        terminal = state in ("completed", "failed", "cancelled", "rejected",
                             "abandoned")
    return {
        "id": "01J9-job", "state": state, "terminal": terminal,
        "state_changed_at": "2026-09-22T10:00:00.000Z",
        "design": "gcd", "jobname": "job0", "flow": "nopflow",
        "owner": {"id": "01J9-user", "name": "A User"}, "project": None,
        "created_at": "2026-09-22T10:00:00.000Z",
        "submitted_at": "2026-09-22T10:00:01.000Z",
        "started_at": None, "finished_at": None,
        "archived_at": None, "deleted_at": None, "error": None,
        "nodes": nodes,
        # Derived: the client reads `failed_count` to choose its advice.
        "progress": {
            "total_count": len(nodes),
            "completed_count": sum(1 for n in nodes if n["state"] == "completed"),
            "failed_count": sum(1 for n in nodes if n["state"] == "failed")},
        **extra,
    }


@pytest.fixture
def run(logged_in, nop_project):
    return RemoteRun(nop_project, logged_in)


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    return slept


def _refused(fake_v1, method, path, slug, status, headers=None, **members):
    fake_v1.route(method, path, problem(slug, status, **members), status=status,
                  content_type="application/problem+json", headers=headers)


def _created(fake_v1, **extra):
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z", **extra}, status=201)


def _granted(fake_v1, put_status=200):
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put",
                      "" if put_status == 200 else "denied", status=put_status,
                      content_type="text/plain")


def _submitted(fake_v1, **body):
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging", **body),
                  status=202)


def _routes_for_a_submit(fake_v1, **created):
    _created(fake_v1, **created)
    _granted(fake_v1)
    _submitted(fake_v1)


def _put_body(fake_v1):
    put = next(c for c in fake_v1.calls if c.request.path_url == "/put")
    body = put.request.body
    return body.read() if hasattr(body, "read") else body


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
    _routes_for_a_submit(fake_v1)

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
    sent = _put_body(fake_v1)
    assert grant == {"size_bytes": len(sent),
                     "digest": f"sha256:{hashlib.sha256(sent).hexdigest()}"}

    assert "Uploading" in caplog.text
    assert "design gcd (library,gcd,dataroot,gcd-pytest-example):" in caplog.text


def test_the_create_body_is_two_names_and_a_descriptor(fake_v1, run):
    '''Authoritative at the top, advisory under `descriptor`; no `versions`,
    no `resources` and no `run_hash`; submit has no body.'''
    _routes_for_a_submit(fake_v1)

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


def test_requested_python_is_the_fixed_list(fake_v1, logged_in, gcd_design):
    '''Never every class the manifest names: lambdapdk's PDK and libraries
    are data the job carries.'''
    from importlib.metadata import version

    from siliconcompiler import ASIC
    from siliconcompiler.targets import skywater130_demo

    project = ASIC(gcd_design)
    skywater130_demo(project)

    pins = RemoteRun(project, logged_in)._requested_python()

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
    from siliconcompiler.remote import owners

    entry = ("library", "scfakelib", "scfakedata")
    monkeypatch.setattr(owners, "installed_dataroots",
                        lambda project, required=None: [(entry, distribution)])
    monkeypatch.setattr("siliconcompiler.remote.client.run.metadata.version",
                        lambda name: "1.0.0" if name == "scfakedata"
                        else __import__("importlib.metadata").metadata.version(name))
    published = json.loads(json.dumps(capabilities))
    published["software"]["python"]["scfakedata"] = [listed]
    fake_v1.replace(responses.GET, "", published)

    run = RemoteRun(nop_project, logged_in)

    if named:
        assert run._requested_python()["scfakedata"] == ["==1.0.0"]
        assert not run._uploaded_packages()
    else:
        assert "scfakedata" not in run._requested_python()
        assert run._uploaded_packages() == {entry}


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
    from test_capture import RunsATestbench

    open("tb.py", "w").write("")
    pins = RemoteRun(_one_node_project(gcd_design, RunsATestbench()),
                     logged_in)._requested_python()

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
    assert RemoteRun(project, logged_in)._requested_python()["cocotb"] == declared


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
        nodes=[_node("stepone", "completed", exit_code=0), _node("steptwo", "skipped"),
               {"step": "nowhere", "index": "9", "state": "completed", "terminal": True},
               {"state": "completed", "terminal": True}]))

    run._poll("01J9-job")

    assert nop_project.get('record', 'status', step="stepone", index="0") == "success"
    assert nop_project.get('record', 'status', step="steptwo", index="0") == "skipped"


@pytest.mark.parametrize("slug,status", [
    ("not-found", 404), ("feature-unsupported", 501), ("brand-new-refusal", 400)])
def test_a_refusal_ends_the_run_as_a_failure(fake_v1, run, slug, status):
    '''Falling through would announce a finished job with nothing in it. A type
    this client does not know is acted on by its status class.'''
    _refused(fake_v1, responses.GET, "jobs/01J9-job", slug, status)

    with pytest.raises(RemoteError) as raised:
        run._poll("01J9-job")

    assert "01J9-job" in str(raised.value)


@pytest.mark.parametrize("body,status,content_type,headers,warned,paced", [
    ("<html><body><h1>502 Bad Gateway</h1></body></html>", 502, "text/html", None,
     "Bad Gateway", 5),
    (problem("not-ready", 409), 409, "application/problem+json", None, None, 5),
    (problem("brand-new-outage", 503), 503, "application/problem+json", None,
     "Brand new outage", 5),
    (problem("brand-new-limit", 429), 429, "application/problem+json",
     {"Retry-After": "11"}, None, 11),
], ids=["proxy-502", "not-ready", "unknown-5xx", "unknown-429"])
def test_a_server_error_or_not_ready_is_waited_through(fake_v1, run, no_sleep, caplog,
                                                       body, status, content_type, headers,
                                                       warned, paced):
    '''A proxy's HTML is rendered, never thrown on, and the refusal's own
    `Retry-After` sets the wait.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", body, status=status,
                  content_type=content_type, headers=headers)
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    with caplog.at_level("WARNING"):
        run._poll("01J9-job")

    if warned:
        assert warned in caplog.text
    assert paced in no_sleep


def test_a_server_that_never_comes_back_is_bounded(fake_v1, run, no_sleep):
    for _ in range(40):
        fake_v1.route(responses.GET, "jobs/01J9-job", "oops", status=500,
                      content_type="text/plain")

    with pytest.raises(RemoteError):
        run._poll("01J9-job")


def test_reconnect_re_enters_the_wait(fake_v1, run):
    '''The answer to Ctrl-C, and the only way back to a detached job.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run.reconnect("01J9-job")


SIGN_IN = {"url": "https://sc-server.test/portal/enter?token=t",
           "expires_at": "2026-10-01T18:04:30Z"}


@pytest.fixture
def opened(run, monkeypatch):
    '''What the run opened in a browser, with the tty checks out of the way.'''
    urls = []
    monkeypatch.setattr("siliconcompiler.remote.client.credentials.preference",
                        lambda name, default=None: True if name == "open_portal" else default)
    monkeypatch.setattr(run.client, "open_url",
                        lambda url, what, require_tty=True: urls.append(url) or True)
    return urls


def _pages(fake_v1):
    return [c.request for c in fake_v1.calls if c.request.url.endswith("/v1/auth/browser")]


@pytest.mark.parametrize("which,asked", [("job", {"job_id": "01J9-job"}), ("home", {})])
def test_a_page_is_asked_for_never_built(fake_v1, run, opened, which, asked):
    '''After a submit, the job's page by its id; `sc-remote -portal`, the
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
    _refused(fake_v1, responses.POST, "auth/browser", slug, status)

    run._open_portal("01J9-job")

    assert opened == []
    assert "No page for the job's page" in caplog.text


def test_a_refused_portal_command_fails_and_says_why(fake_v1, run, opened):
    '''Asked for on purpose, so the command fails.'''
    _refused(fake_v1, responses.POST, "auth/browser", "not-permitted", 403)

    with pytest.raises(RemoteError, match="not-permitted|Not permitted"):
        run.client.portal()
    assert opened == []


def test_a_ci_session_never_asks_for_a_page(fake_v1, run, opened):
    from siliconcompiler.remote.client import GRANT_TOKEN_EXCHANGE

    run.client._mode = GRANT_TOKEN_EXCHANGE

    run._open_portal("01J9-job")
    with pytest.raises(RemoteError, match="CI session"):
        run.client.portal()

    assert not _pages(fake_v1)
    assert not opened


@pytest.mark.parametrize("link", [
    "</v1/jobs?limit=1&cursor=abc&kept=1>; rel=next",
    '</v1/jobs?cursor=zzz>; rel="prev", </v1/jobs?limit=1&cursor=abc&kept=1>; rel="next"',
    '<https://sc-server.test/v1/jobs?limit=1&cursor=abc&kept=1>; title="a, b"; rel="next last"',
    "</v1/jobs?limit=1&cursor=abc&kept=1>; REL=Next",
], ids=["unquoted", "second", "absolute", "case"])
def test_the_next_page_is_the_link_target_as_given(fake_v1, logged_in, link):
    '''RFC 8288: the `rel="next"` URL requested unchanged,
    never this request rebuilt around a cursor.'''
    from urllib.parse import urlsplit

    fake_v1.route(responses.GET, "jobs", {"items": [job_body("completed")]},
                  headers={"Link": link})
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("failed")]})

    assert len(logged_in.jobs(archived=True)) == 2

    pages = [c.request.url for c in fake_v1.calls if urlsplit(c.request.url).path == "/v1/jobs"]
    assert pages[-1] == "https://sc-server.test/v1/jobs?limit=1&cursor=abc&kept=1"


@pytest.mark.parametrize("again", [False, True], ids=["restarted", "twice"])
def test_a_cursor_the_server_no_longer_takes_restarts_the_listing_once(
        fake_v1, logged_in, again):
    '''`invalid-cursor` starts the listing again from its first page, keeping
    nothing from before; a second one is the answer.'''
    first = {"headers": {"Link": '</v1/jobs?cursor=stale>; rel="next"'}}
    stale = {"status": 400, "content_type": "application/problem+json"}
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("completed")]}, **first)
    fake_v1.route(responses.GET, "jobs", problem("invalid-cursor", 400), **stale)
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("completed")]}, **first)
    if again:
        fake_v1.route(responses.GET, "jobs", problem("invalid-cursor", 400), **stale)
        with pytest.raises(ServerProblem):
            logged_in.jobs()
    else:
        fake_v1.route(responses.GET, "jobs", {"items": [job_body("failed")]})
        assert [job["state"] for job in logged_in.jobs()] == ["completed", "failed"]


def test_a_next_page_on_another_origin_is_not_followed(fake_v1, logged_in):
    '''The request carries this session.'''
    fake_v1.route(responses.GET, "jobs", {"items": []},
                  headers={"Link": '<https://elsewhere.test/v1/jobs?cursor=a>; rel="next"'})

    with pytest.raises(RemoteError, match="another origin"):
        logged_in.jobs()

    assert not [c for c in fake_v1.calls if "elsewhere" in c.request.url]


def test_a_boolean_filter_goes_as_true_or_false(fake_v1, logged_in):
    '''`true` or `false`, never Python's `True`.'''
    from urllib.parse import parse_qs, urlsplit

    fake_v1.route(responses.GET, "jobs", {"items": []})

    logged_in.jobs(archived=True, terminal=False)
    logged_in.jobs(archived=[True, False])

    first, second = [parse_qs(urlsplit(call.request.url).query)
                     for call in fake_v1.calls if urlsplit(call.request.url).path == "/v1/jobs"]
    assert (first["archived"], first["terminal"]) == (["true"], ["false"])
    assert second["archived"] == ["true", "false"]


@pytest.mark.parametrize("reason,sent", [
    (None, "cancelled from sc-remote"),
    ("wrong constraints", "wrong constraints"),
    ("é" * 300, "é" * 300),
], ids=["default", "own", "300-code-points"])
def test_a_cancel_always_says_why(fake_v1, logged_in, reason, sent):
    '''`reason` is optional on the wire, and this client always sends one:
    the caller's own, or one naming the tool and never the hostname.'''
    import socket

    fake_v1.route(responses.POST, "jobs/01J9-job/cancel", job_body("cancelling"), status=202)

    logged_in.cancel_job("01J9-job", **({"reason": reason} if reason else {}))

    assert json.loads(fake_v1.calls[-1].request.body) == {"reason": sent}
    assert socket.gethostname() not in sent


@pytest.mark.parametrize("reason,said", [("é" * 301, "at most 300 characters"),
                                         ("two\nlines", "control character"),
                                         ("a\x9bb", "control character")])
def test_a_cancel_reason_is_checked_before_it_is_sent(fake_v1, logged_in, reason, said):
    '''Refused here, naming why, never cut; nothing sent.'''
    with pytest.raises(RemoteError, match=said):
        logged_in.cancel_job("01J9-job", reason=reason)

    assert not _cancels(fake_v1)


def test_delete_is_a_204_with_no_body(fake_v1, logged_in):
    fake_v1.route(responses.DELETE, "jobs/01J9-job", "", status=204, content_type="")

    assert logged_in.delete_job("01J9-job") is None


def test_the_grants_content_length_is_not_forwarded(fake_v1, logged_in, tmp_path):
    '''The file's own length: announcing a gigabyte over twenty bytes
    would leave the server waiting for ever.'''
    payload = tmp_path / "upload.tar.gz"
    payload.write_bytes(b"x" * 20)
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")

    logged_in.upload({"url": "https://storage.test/put",
                      "headers": {"content-length": "1073741824"}}, payload)

    assert fake_v1.calls[-1].request.headers["Content-Length"] == "20"


#
# The half the integration rig cannot reach: a working server cannot be
# made to report a limit it does not have or refuse a feature it implements.

@pytest.mark.parametrize("slug,status,members,expected", [
    ("limit-exceeded", 429, {"limit": "pending_uploads"},
     ["limit: pending_uploads", "refills"]),
    ("limit-exceeded", 429, {"limit": "concurrent_jobs"}, ["limit: concurrent_jobs"]),
    ("node-limit-exceeded", 403, {"limit": "max_job_nodes"},
     ["limit: max_job_nodes", "smaller flow"]),
    ("upload-too-large", 413, {"limit": "max_upload_bytes"},
     ["limit: max_upload_bytes", "waiting will not help"]),
    ("feature-unsupported", 501, {"feature": "projects"},
     ["feature: projects", "does not offer that"]),
    ("entitlement-denied", 403, {"resource_kind": "pdk", "resource": "gf12"},
     ["resource: gf12", "resource_kind: pdk", "Ask for a grant"]),
    # Each entry says which requirement failed by its `kind`.
    ("software-unavailable", 422,
     {"reason": "unavailable", "unresolved": [
         {"kind": "tools", "name": "openroad", "requirement": [">=24.3.2011", "==2.0"],
          "available": ["2.1.0"]},
         {"kind": "tools", "name": "magic", "requirement": [], "available": []}]},
     ["reason: unavailable",
      "tool openroad >=24.3.2011 or ==2.0 (available: 2.1.0)",
      "tool magic any version (available: none)",
      "Ask for a version this server has"]),
    ("software-unavailable", 422,
     {"reason": "combination", "unresolved": [
         {"kind": "python", "name": "siliconcompiler", "requirement": ["==0.39.1"],
          "available": ["0.39.1"]},
         {"kind": "python", "name": "za-sclib", "requirement": ["==0.1.80"],
          "available": ["0.1.80"]}]},
     ["reason: combination", "python za-sclib ==0.1.80 (available: 0.1.80)"]),
    ("software-unavailable", 422,
     {"reason": "unavailable", "unresolved": [
         {"kind": "interpreter", "name": "python", "requirement": ["==3.12.*"],
          "available": ["3.11.9"]}]},
     ["interpreter python ==3.12.* (available: 3.11.9)",
      "No image here runs the Python this machine does"]),
    ("software-unavailable", 422,
     {"reason": "unknown_class", "unresolved": [
         {"kind": "class", "name": "mytasks/MyTask", "requirement": [], "available": []}]},
     ["task class mytasks/MyTask"]),
    ("software-unavailable", 422,
     {"reason": "uninstallable", "unresolved": [
         {"kind": "package", "name": "numpy", "requirement": ["==1.*"], "available": []}]},
     ["package numpy ==1.* (available: none)"]),
    ("artifact-not-approved", 403, {}, ["held back from download"]),
    ("resource-unavailable", 422, {"resource_kind": "pdk", "resource": "mypdk"},
     ["resource: mypdk", "resource_kind: pdk", "cannot be sent it"]),
    ("terms-not-accepted", 403, {"blocked_by": ["tos", "export"]},
     ["sign tos", "sign export", "Sign each document"]),
    ("not-permitted", 403, {}, ["You cannot do that to this job"]),
    ("limit-exceeded", 429, {"limit": "pending_uploads", "job_ids": ["a", "b"]},
     ["job_ids: a b"]),
    ("idempotency-key-reuse", 422, {}, ["A retry changed the request"]),
    ("invalid-request", 400, {}, ["Invalid request"]),
    ("rate-limited", 429, {}, []),
    ("insecure-transport", 426, {}, []),
    ("not-ready", 409, {"artifact_kind": "logs"}, []),
    ("invalid-cursor", 400, {}, []),
])
def test_every_refusal_renders(fake_v1, logged_in, slug, status, members, expected):
    '''Branched on its type and members; the page link beside the sentence,
    not instead of it.'''
    _refused(fake_v1, responses.POST, "jobs", slug, status, **members)

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    assert raised.value.slug == slug
    for name, value in members.items():
        assert raised.value.member(name) == value
    rendered = str(raised.value)
    for fragment in expected:
        assert fragment in rendered, rendered
    assert f"server-errors/{slug}" in rendered


def test_a_resource_named_without_its_kind_prints_cleanly(fake_v1, logged_in):
    '''By name, never as `resource_kind: None`.'''
    _refused(fake_v1, responses.POST, "jobs", "resource-unavailable", 422, resource="secret",
             detail="secret (secret) is marked private, and this server holds no copy of it")

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    rendered = str(raised.value)
    assert "resource: secret" in rendered
    assert "resource_kind" not in rendered and "None" not in rendered


def test_a_keyed_create_refused_by_a_gateway_is_retried_then_rendered(fake_v1, logged_in,
                                                                      no_sleep):
    '''A keyed create replays, so a 5xx is retried with the same key; a
    gateway's HTML is then rendered, not thrown on.'''
    fake_v1.route(responses.POST, "jobs",
                  "<html><head><title>502 Bad Gateway</title></head></html>",
                  status=502, content_type="text/html")

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    assert raised.value.slug is None
    assert "502" in str(raised.value)
    creates = [c.request for c in fake_v1.calls if c.request.path_url == "/v1/jobs"]
    assert len(creates) == 3 and len({r.headers["Idempotency-Key"] for r in creates}) == 1


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
                        nodes=[_node("stepone", "failed"), _node("steptwo", "cancelled")],
                        error={"type": RUN_FAILED, "title": "The run failed"})

    assert "The run failed" in text
    assert "Read the failing node's log" in text
    assert any("artifacts" in call.request.path_url for call in fake_v1.calls)
    rendered = [r.message for r in caplog.records
                if r.levelname == "ERROR" and "run failed" in r.message.lower()]
    assert rendered and len(rendered[0].splitlines()) <= 4


@pytest.mark.parametrize("nodes,error,said,unsaid", [
    # A node's `error` detail is printed beside the node.
    ([_node("stepone", "failed", error={"type": RUN_FAILED, "title": "The run failed",
                                        "detail": "the node exceeded its time limit"}),
      _node("steptwo", "cancelled")],
     {"type": RUN_FAILED, "title": "The run failed",
      "detail": "stepone/0 exceeded its time limit"},
     ["stepone/0 failed: the node exceeded its time limit"], ["steptwo/0 failed"]),
    # A flow that dies before its first node has no log to read: the
    # advice comes from the job, and the server's `detail` survives.
    ([_node("stepone", "cancelled"), _node("steptwo", "cancelled")],
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
        _node("stepone", "completed", started_at="2026-09-22T10:00:00.000Z",
              finished_at="2026-09-22T10:01:30.500Z"),
        _node("steptwo", "running", started_at="2026-09-22T10:01:31.000Z"),
        _node("stepthree", "skipped")])
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
        _node("pin_placement", "queued"),
        _node("power_grid", "running", started_at="2026-09-22T10:00:05.200Z"),
        _node("tapcell", "completed", started_at="2026-09-22T10:00:01.000Z",
              finished_at="2026-09-22T10:00:05.100Z")])

    assert floorplan._record(job, seen) == [("tapcell", "0", "completed"),
                                            ("power_grid", "0", "running"),
                                            ("pin_placement", "0", "queued")]


def test_where_nothing_says_when_the_flows_order_decides(fake_v1, floorplan, caplog):
    job = job_body("running", nodes=[_node(step, "pending") for step in
                                     ("pin_placement", "power_grid", "tapcell")])

    assert [step for step, _, _ in floorplan._record(job, {})] == \
        ["tapcell", "power_grid", "pin_placement"]
    with caplog.at_level("INFO"):
        floorplan._report(job, changed=[])
    assert "Pending (3): tapcell/0, power_grid/0, pin_placement/0" in caplog.text


def test_a_server_with_no_live_tail_simply_does_not_tail(fake_v1, run, capabilities):
    '''The archived log still arrives with the results.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.replace(responses.GET, "", dict(capabilities, features=[]))

    assert _Tails(run)._enabled is False


def test_quiet_means_quiet_and_the_server_sets_the_tail_count(fake_v1, run, nop_project):
    '''It is the server's thread and descriptor being held.'''
    from siliconcompiler.remote.client.run import _Tails

    nop_project.option.set_quiet(False)
    tails = _Tails(run)
    assert tails._enabled is True
    assert tails._ceiling == 8

    nop_project.option.set_quiet(True)
    assert _Tails(run)._enabled is False


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
    ({"concurrent_log_streams": None}, ["stepone", "steptwo"]),
    ({}, ["stepone", "steptwo"])], ids=["one", "none-allowed", "unlimited", "absent"])
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


def test_without_one_each_running_node_is_followed(fake_v1, run, capabilities, tails):
    _Tails, opened = tails
    fake_v1.replace(responses.GET, "", dict(capabilities, features=["logs.stream"]))

    tail = _Tails(run)
    tail.follow("j1", _running_nodes("stepone", "steptwo"))
    tail.finish()

    assert sorted(opened) == ["stepone", "steptwo"]


def test_a_refused_job_stream_falls_back_for_good(fake_v1, run, tails):
    '''`feature-unsupported` naming `logs.stream.job` is permanent.'''
    _Tails, opened = tails
    _refused(fake_v1, responses.GET, "jobs/j1/logs", "feature-unsupported", 501,
             feature="logs.stream.job")

    tail = _Tails(run)
    tail._tail_job("j1")
    assert tail._whole_job is False

    tail.follow("j1", _running_nodes("stepone"))
    tail.finish()

    assert opened == ["stepone"]
    asked = [c.request.path_url for c in fake_v1.calls if "/logs" in c.request.path_url]
    assert asked == ["/v1/jobs/j1/logs"]


def test_a_log_asked_too_early_is_asked_again(fake_v1, run):
    '''`not-ready` is transient for the job's stream and a node's; a final
    refusal is not asked again.'''
    from siliconcompiler.remote.client.run import JOB, _Tails

    run.project.option.set_quiet(False)
    _refused(fake_v1, responses.GET, "jobs/j1/logs", "not-ready", 409, artifact_kind="logs")

    tails = _Tails(run)
    tails._started.update({JOB, ("stepone", "0")})
    tails._tail_job("j1")
    assert tails._whole_job is True
    assert JOB not in tails._started
    tails._tail("j1", "stepone", "0")
    assert ("stepone", "0") not in tails._started

    fake_v1.replace(responses.GET, "jobs/j1/logs", problem("not-found", 404),
                    status=404, content_type="application/problem+json")
    tails._started.add(("stepone", "0"))
    tails._tail("j1", "stepone", "0")
    assert ("stepone", "0") in tails._started


def test_no_live_log_on_a_nodes_tail_stops_tailing_for_the_run(fake_v1, run, capabilities):
    '''`feature-unsupported` naming `logs.stream` is not asked again, for any node.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.replace(responses.GET, "", dict(capabilities, features=["logs.stream"]))
    _refused(fake_v1, responses.GET, "jobs/j1/logs", "feature-unsupported", 501,
             feature="logs.stream")

    tails = _Tails(run)
    tails._tail("j1", "stepone", "0")
    tails.follow("j1", _running_nodes("stepone", "steptwo"))
    tails.finish()

    assert len([c for c in fake_v1.calls if "/logs" in c.request.path_url]) == 1


def test_the_software_preflight_warns_and_does_not_stop(fake_v1, run, capabilities,
                                                        monkeypatch):
    '''Create decides, from a `GET /v1` this client may hold stale.'''
    said = []
    monkeypatch.setattr(run.logger, "warning", lambda message, *_, **__: said.append(message))
    fake_v1.replace(responses.GET, "", dict(capabilities, software={
        "python": {"siliconcompiler": ["0.0.1"]}, "tools": {}, "interpreter": {}}))

    run._check_software()

    assert any("siliconcompiler 0.0.1" in message for message in said)


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

    assert RemoteRun(gcd_nop_project, logged_in)._tool_requirements() == wanted


@pytest.mark.parametrize("declared,sent", [
    (">=24Q3-2011", ">=24.3.2011"),
    (">=24Q3-2011,<27Q1-0", ">=24.3.2011,<27.1.0"),
    ("whatever", None),
])
def test_a_declared_requirement_is_normalised_before_it_is_sent(declared, sent):
    '''OpenROAD's `>=24Q3-2011` is not PEP 440, and only the driver can
    make it comparable. Each part of a set on its own; an unreadable one is
    dropped rather than refusing every OpenROAD.'''
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    from siliconcompiler.remote.client.run import _normalize_spec
    from siliconcompiler.tools.openroad import OpenROADTask

    spec = _normalize_spec(OpenROADTask(), declared)

    assert spec == sent
    if spec:
        # What the probe stores for a real OpenROAD satisfies it.
        assert Version("26.3.2418") in SpecifierSet(spec)


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

    from test_capture import RunsATestbench

    installed = metadata.version
    monkeypatch.setattr("siliconcompiler.remote.client.run.metadata.version",
                        lambda name: "a-local-build" if name == "scfakebits"
                        else installed(name))
    open("tb.py", "w").write("")
    run = RemoteRun(_one_node_project(gcd_design, RunsATestbench()), logged_in)

    with caplog.at_level("WARNING"):
        pins = run._requested_python()

    assert pins["scfakebits"] == []
    assert "Dropping the version requirement on scfakebits" in caplog.text


def _members(run, tmp_path):
    '''The upload's members by name, and each regular file's bytes.'''
    import tarfile

    upload = tmp_path / "upload.tar.gz"
    run._pack(upload)
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
    assert owners.required(sent) == owners.required(run._needs()[0])
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
    _refused(fake_v1, responses.GET, "jobs/01J9-job", "not-found", 404,
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
    _routes_for_a_submit(fake_v1, **ASKED_ACME)

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
    _routes_for_a_submit(fake_v1, **ASKED_ACME)
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

    _granted(fake_v1)
    _submitted(fake_v1)

    run._send_asked("01J9-job", [GCD_ROOT])

    with tarfile.open(fileobj=io.BytesIO(_put_body(fake_v1))) as tar:
        names = tar.getnames()
    assert names and all(name.startswith("sc_collected_files") for name in names)
    assert any(name.endswith(".v") for name in names)
    assert not any(name.endswith(".pkg.json") for name in names)


def test_a_follow_up_packed_again_repeats_its_size_and_digest(fake_v1, logged_in,
                                                              nop_project):
    '''A retry must repeat what its first grant fixed, so the archive carries no
    time or owner of its own.'''
    _granted(fake_v1)
    _submitted(fake_v1)

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
    _granted(fake_v1, put_status=put)
    _submitted(fake_v1)
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
    _granted(fake_v1)
    _submitted(fake_v1)

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
    monkeypatch.setattr(RemoteRun, "_pack", lambda self, upload: pytest.fail("packed"))
    fake_v1.route(responses.POST, "jobs", refusal, status=refusal["status"],
                  content_type="application/problem+json")

    with pytest.raises(RemoteError) as raised:
        run._start()

    assert all(line in str(raised.value) for line in said), str(raised.value)
    assert not any("upload-grant" in call.request.url for call in fake_v1.calls)


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
    _created(fake_v1)
    _granted(fake_v1)
    _submitted(fake_v1, nodes=[])
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
    _refused(fake_v1, responses.POST, "jobs", "job-state-conflict", 409,
             headers={"Retry-After": "2"}, reason="in_progress")
    _refused(fake_v1, responses.POST, "jobs", "limit-exceeded", 429,
             headers={"Retry-After": "3"}, limit="pending_uploads", job_ids=["01J9-old"])
    _refused(fake_v1, responses.POST, "jobs", "limit-exceeded", 429,
             headers={"Retry-After": "4"}, limit="compute_seconds")
    _routes_for_a_submit(fake_v1)

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
    _created(fake_v1)
    _granted(fake_v1, put_status=403)
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "", status=second,
                      content_type="text/plain")
    _submitted(fake_v1)
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
            "cancelled from sc-remote")


def test_an_upload_that_does_not_match_its_digest_goes_up_again(fake_v1, run):
    '''The archive whose digest the grant bound, then a second submit with a
    fresh key; the job is kept.'''
    _created(fake_v1)
    _granted(fake_v1)
    _refused(fake_v1, responses.POST, "jobs/01J9-job/submit", "upload-digest-mismatch", 422)
    _submitted(fake_v1)

    run._start()

    puts = [c for c in fake_v1.calls if c.request.path_url == "/put"]
    submits = [c.request for c in fake_v1.calls if c.request.path_url.endswith("/submit")]
    assert len(puts) == 2 and len(submits) == 2
    assert submits[0].headers["Idempotency-Key"] != submits[1].headers["Idempotency-Key"]
    assert not _cancels(fake_v1)


@pytest.mark.parametrize("slug,status,state,outcome", [
    ("terms-not-accepted", 403, None, "kept"),
    ("account-not-provisioned", 403, None, "kept"),
    ("brand-new-outage", 503, None, "kept"),
    ("job-state-conflict", 409, "staging", "submitted"),
    ("job-state-conflict", 409, "awaiting_input", "cancelled"),
])
def test_a_refused_submit_cancels_only_what_cannot_be_submitted_again(
        fake_v1, run, no_sleep, slug, status, state, outcome):
    '''A refusal a person clears, or a server failure, leaves the job waiting with
    its upload for a reconnect; a state conflict is read again, and only a job
    holding no upload is cancelled.'''
    _created(fake_v1)
    _granted(fake_v1)
    _refused(fake_v1, responses.POST, "jobs/01J9-job/submit", slug, status)
    if state:
        fake_v1.route(responses.GET, "jobs/01J9-job", job_body(state, nodes=[]))
    _cancelled(fake_v1)

    if outcome == "submitted":
        assert run._start() == "01J9-job"
    else:
        with pytest.raises(RemoteError) as raised:
            run._start()
    if outcome == "kept":
        assert "sc_remote.pkg.json -reconnect" in str(raised.value)

    assert len(_cancels(fake_v1)) == (outcome == "cancelled")
    assert bool(run.project.get('record', 'remoteid')) == (outcome != "cancelled")


@pytest.mark.parametrize("answer,said", [(202, "Job submitted"), (409, "holds no upload")])
def test_a_reconnect_submits_the_upload_a_waiting_job_holds(fake_v1, run, no_sleep, caplog,
                                                            answer, said):
    '''Left `awaiting_input` by a refused submit, it is submitted again by its
    owner; a 409 means it holds none, and it is not cancelled from here.'''
    run.client.credentials.set_user_id("01J9-user")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("awaiting_input", nodes=[]))
    if answer == 202:
        _submitted(fake_v1)
        fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))
        with caplog.at_level("INFO"):
            run.reconnect("01J9-job")
        assert said in caplog.text
    else:
        _refused(fake_v1, responses.POST, "jobs/01J9-job/submit", "job-state-conflict", 409)
        with pytest.raises(RemoteError, match=said):
            run.reconnect("01J9-job")

    assert not _cancels(fake_v1)


def test_an_interrupt_before_submit_cancels_the_job(fake_v1, run, monkeypatch):
    _created(fake_v1)
    _cancelled(fake_v1)

    def interrupted(self, upload):
        raise KeyboardInterrupt

    monkeypatch.setattr(RemoteRun, "_pack", interrupted)

    with pytest.raises(KeyboardInterrupt):
        run._start()

    assert "interrupted" in json.loads(_cancels(fake_v1)[0].body)["reason"]


TYPES = "https://siliconcompiler.com/server-errors/"


@pytest.mark.parametrize("me,said", [
    ({"can_submit": False, "blocked_type": f"{TYPES}terms-not-accepted", "terms": [
        {"id": "tos", "title": "Terms of Service", "scope": {"applies_to": "service"},
         "accepted_at": None},
        {"id": "nda", "title": "A foundry NDA",
         "scope": {"applies_to": "resource", "resources": []}, "accepted_at": None}]},
     ["sign Terms of Service", "Sign each document below"]),
    ({"can_submit": False, "blocked_type": f"{TYPES}account-not-provisioned"},
     ["Ask an administrator to provision"]),
    ({"can_submit": False}, ["cannot submit jobs on this server"]),
    ({"can_submit": True}, None),
    ({}, None),
], ids=["terms", "unprovisioned", "no-type", "can-submit", "not-said"])
def test_an_account_that_cannot_submit_stops_before_create(fake_v1, run, me, said):
    '''`blocked_type` is the refusal create would give, so its advice is given
    here; where `GET /v1/me` says nothing of it, nothing stops.'''
    fake_v1.route(responses.GET, "me", {"id": "01J9-user", "terms": [], **me})

    if said is None:
        run._check_account()
        return
    with pytest.raises(RemoteError) as raised:
        run._check_account()
    assert all(line in str(raised.value) for line in said), str(raised.value)
    assert "foundry NDA" not in str(raised.value)


def test_an_asic_project_with_no_pdk_stops_before_create(fake_v1, logged_in, gcd_design):
    from siliconcompiler import ASIC

    project = ASIC(gcd_design)
    project.add_fileset("rtl")

    with pytest.raises(RemoteError, match="sets no PDK"):
        RemoteRun(project, logged_in)._preflight()

    assert not any(call.request.path_url == "/v1/jobs" for call in fake_v1.calls)


def test_a_task_class_no_package_provides_stops_before_create(fake_v1, run, monkeypatch):
    from siliconcompiler.remote.client import capture

    monkeypatch.setattr(capture, "_module_distributions", lambda: {})

    with pytest.raises(RemoteError, match="installed package"):
        run._preflight()


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
        run._check_upstream_files()


class ReadsTheNetlist(NOPTask):
    '''A task whose setup declares the input it reads.'''

    def task(self):
        return "readsthenetlist"

    def setup(self):
        super().setup()
        self.add_input_file("gcd.vg")


@pytest.mark.parametrize("steptwo,refused", [
    ({"output": "own.vg"}, True),
    ({"output": "gcd.vg"}, False),
    ({"fetched_from": "01a0e000-0000-7000-8000-000000000001"}, False),
], ids=["lacking", "holding", "continued"])
def test_an_input_the_outputs_packed_here_lack_stops_the_run_before_create(
        run, nop_project, steptwo, refused):
    '''Read from the setup worked out here; a node reading results continued
    from another job is not checked, since they are not here.'''
    _three_nodes(nop_project, both=True, last=ReadsTheNetlist)
    _upstream_node(nop_project, "stepone", output="own.vg")
    _upstream_node(nop_project, "steptwo", **steptwo)

    if refused:
        with pytest.raises(RemoteError, match="stepthree/0 reads gcd.vg"):
            run._check_upstream_files()
    else:
        run._check_upstream_files()


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
    run._collect([{"kind": "dataroot", "keypath": ["library", "alib", "dataroot", "root"]}],
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


def test_the_session_is_shown_from_me_and_nothing_is_refreshed(logged_in, fake_v1, caplog):
    '''`GET /v1/me` rotates nothing.'''
    import logging

    caplog.set_level(logging.INFO)
    logged_in.print_identity({
        "id": "u1", "issuer": "local",
        "session": {"kind": "interactive", "scope": "jobs:read jobs:write",
                    "device_id": "dev-1", "access_expires_at": "2026-09-29T10:15:00.000Z",
                    "refresh_expires_at": "2026-10-06T10:00:00.000Z",
                    "session_expires_at": "2026-10-11T10:00:00.000Z"},
        "usage": {"concurrent_jobs": 2,
                  "compute_seconds": {"used": 3600, "total": 7200, "limit": None,
                                      "window": "calendar_month", "resets_at": "x"},
                  "storage_bytes": {"used": 2048, "total": None, "limit": None,
                                    "window": None, "resets_at": None}}})

    text = caplog.text
    assert "Session: interactive on device dev-1" in text
    assert "scope: jobs:read jobs:write" in text
    assert "refresh token until 2026-10-06T10:00:00.000Z" in text
    assert "ends at 2026-10-11T10:00:00.000Z" in text
    assert "Compute: 1h 00m this month, 2h 00m in all" in text
    assert not [call for call in fake_v1.calls if "auth/token" in call.request.url
                and "refresh_token" in (call.request.body or "")]


def test_a_ci_session_says_it_cannot_refresh(logged_in, caplog):
    import logging

    caplog.set_level(logging.INFO)
    logged_in.print_identity({
        "id": "u1", "issuer": "ci",
        "session": {"kind": "ci", "scope": "jobs:read", "device_id": None,
                    "access_expires_at": "a", "refresh_expires_at": None,
                    "session_expires_at": "s"},
        "usage": {"concurrent_jobs": 0}})

    assert caplog.text.count("Session: ci") == 1
    assert "on device" not in caplog.text
    assert "it cannot refresh" in caplog.text
