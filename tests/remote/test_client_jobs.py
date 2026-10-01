import hashlib
import json
import os

import pytest
import responses

from siliconcompiler.remote import RemoteError
from siliconcompiler.remote.client.run import RemoteRun, node_status

from conftest import problem


# The conformance rig: the client against canned answers. It is the only place
# most of the contract can be reached from -- a working server cannot be made to
# hand back an HTML 502, a node in `preparing`, or a state nobody has invented
# yet, and the client branches on all three.


def job_body(state="running", nodes=None, terminal=None, **extra):
    '''A job object shaped the way the contract publishes it.'''
    nodes = nodes if nodes is not None else [
        {"step": "stepone", "index": "0", "state": "running", "terminal": False,
         "started_at": None, "finished_at": None, "exit_code": None,
         "error": None},
        {"step": "steptwo", "index": "0", "state": "pending", "terminal": False,
         "started_at": None, "finished_at": None, "exit_code": None,
         "error": None},
    ]
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
        # Derived rather than fixed, because the client now reads
        # `failed_count` to decide what advice to print.
        "progress": {
            "total_count": len(nodes),
            "completed_count": sum(1 for n in nodes if n["state"] == "completed"),
            "failed_count": sum(1 for n in nodes if n["state"] == "failed")},
        **extra,
    }


@pytest.fixture
def run(logged_in, nop_project):
    return RemoteRun(nop_project, logged_in)


###########################
# The node state mapping
###########################

def test_every_published_node_state_maps(logged_in):
    '''The contract's eight as SiliconCompiler's seven, at the boundary.'''
    assert node_status("pending", False) == "pending"
    assert node_status("queued", False) == "queued"
    assert node_status("running", False) == "running"
    assert node_status("completed", True) == "success"
    assert node_status("failed", True) == "error"
    assert node_status("skipped", True) == "skipped"
    assert node_status("cancelled", True) == "error"


def test_preparing_is_waiting_not_running():
    '''Dispatched and fetching its image. Without the distinction, a node
    pulling a tool image for six minutes is indistinguishable from a hang -- and
    reading it as running would put a timer on it that means nothing.'''
    assert node_status("preparing", False) == "queued"


def test_an_unrecognised_state_reads_terminal_rather_than_the_name():
    '''🔴 The rule the contract states, and the reason `terminal` is published:
    the sets have already grown twice.'''
    assert node_status("quiescing", False) == "pending"
    assert node_status("evaporated", True) == "error"


###########################
# The three-call submit
###########################

def test_submit_is_four_calls_in_order(fake_v1, run, nop_project):
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z"}, status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"),
                  status=202)

    job_id = run._start()

    assert job_id == "01J9-job"
    paths = [call.request.path_url for call in fake_v1.calls]
    assert paths[-4:] == ["/v1/jobs", "/v1/jobs/01J9-job/upload-grant",
                          "/put", "/v1/jobs/01J9-job/submit"]


def test_the_upload_carries_no_session(fake_v1, run):
    '''🔴 It addresses storage, not the API. Attaching this session's token and
    a proof would hand them to a party that never asked -- and on a deployment
    whose storage is a bucket, that party is somebody else.'''
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z"}, status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"),
                  status=202)

    run._start()

    upload = [call for call in fake_v1.calls
              if call.request.url == "https://storage.test/put"][0]
    assert "Authorization" not in upload.request.headers
    assert "DPoP" not in upload.request.headers


def test_both_posts_carry_an_idempotency_key(fake_v1, run):
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z"}, status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"),
                  status=202)

    run._start()

    posts = {call.request.path_url: call.request
             for call in fake_v1.calls if call.request.method == "POST"}
    assert posts["/v1/jobs"].headers["Idempotency-Key"]
    assert posts["/v1/jobs/01J9-job/submit"].headers["Idempotency-Key"]
    # Two windows, not one: a retry of the create is not a retry of the submit.
    assert posts["/v1/jobs"].headers["Idempotency-Key"] != \
        posts["/v1/jobs/01J9-job/submit"].headers["Idempotency-Key"]


def test_the_create_body_is_two_names_and_a_descriptor(fake_v1, run):
    '''🔴 Authoritative at the top, advisory under `descriptor` -- and no
    `versions` and no `resources`: `requested_versions` pins what this machine runs,
    and the grant carries the size.'''
    fake_v1.route(responses.POST, "jobs", job_body("created"), status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"),
                  status=202)

    run._start()

    created = [call for call in fake_v1.calls
               if call.request.path_url == "/v1/jobs"][0]
    body = json.loads(created.request.body)
    assert set(body) == {"design", "jobname", "descriptor"}
    descriptor = body["descriptor"]
    assert "versions" not in descriptor and "resources" not in descriptor
    # Every value a list, and the framework pinned exactly.
    pins = descriptor["requested_versions"]["python"]["siliconcompiler"]
    assert isinstance(pins, list) and pins[0].startswith("==")
    # The flowgraph's name, as the job object carries it, and its node count
    # beside it (surface D289).
    assert isinstance(descriptor["flow"], str) and descriptor["flow"]
    assert descriptor["node_count"] == 2
    # Nothing computes a run hash yet, so nothing claims one -- at the top,
    # where it would go, or in the descriptor.
    assert "run_hash" not in body and "run_hash" not in descriptor
    # No node runs the user's own Python, so no interpreter is named: the
    # images' Pythons do not matter to it (surface D293).
    assert "interpreter" not in descriptor["requested_versions"]

    submitted = [call for call in fake_v1.calls
                 if call.request.path_url.endswith("/submit")][0]
    # No body (surface §15; D277): the grant bound the digest.
    assert json.loads(submitted.request.body) == {}


@pytest.mark.parametrize("advertised", [True, False])
def test_a_hash_goes_only_to_a_server_that_reuses_jobs(fake_v1, run, capabilities,
                                                       monkeypatch, advertised):
    '''Top level, and only where `GET /v1` advertises `jobs.reuse`: anywhere
    else the member is validated and ignored. A hit is the job already there,
    so nothing is granted or uploaded.'''
    import copy

    published = copy.deepcopy(capabilities)
    if advertised:
        published["features"] = list(published.get("features") or []) + ["jobs.reuse"]
    fake_v1.replace(responses.GET, "", published)
    monkeypatch.setattr(type(run), "_run_hash", lambda self: "the-hash")
    fake_v1.route(responses.POST, "jobs", job_body("completed"),
                  status=200 if advertised else 201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})

    run._start()

    created = [call for call in fake_v1.calls if call.request.path_url == "/v1/jobs"][0]
    body = json.loads(created.request.body)
    assert body.get("run_hash") == ("the-hash" if advertised else None)
    assert "run_hash" not in body.get("descriptor", {})
    assert not [call for call in fake_v1.calls if "upload-grant" in call.request.path_url]


def test_requested_python_is_the_fixed_list(fake_v1, logged_in, gcd_design):
    '''🔴 Exactly: `siliconcompiler`, the distribution behind each executed
    node's task class, and -- where they apply -- a framework distribution,
    an installed-package dataroot the server supplies at this version, and a
    distribution holding a private dataroot. Never every class the manifest
    names: lambdapdk's PDK and libraries are data the job carries.'''
    from importlib.metadata import version

    from siliconcompiler import ASIC
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.targets import skywater130_demo

    project = ASIC(gcd_design)
    skywater130_demo(project)

    pins = RemoteRun(project, logged_in)._requested_python()

    assert list(pins) == ["siliconcompiler"]
    assert version("lambdapdk")          # there to be left out


@pytest.fixture
def installed_data(monkeypatch, nop_project):
    '''A library whose dataroot is a package installed normally, as
    `scfakedata` 1.0.0 -- and the flow reads it.'''
    from siliconcompiler.remote import owners

    entry = ("library", "scfakelib", "scfakedata")
    monkeypatch.setattr(owners, "installed_dataroots",
                        lambda project, required=None: [(entry, "scfakedata")])
    monkeypatch.setattr("siliconcompiler.remote.client.run.metadata.version",
                        lambda name: "1.0.0" if name == "scfakedata"
                        else __import__("importlib.metadata").metadata.version(name))
    return entry


def test_an_installed_package_the_server_lists_at_this_version_is_named(
        fake_v1, logged_in, nop_project, capabilities, installed_data):
    '''Named exactly, and supplied: its dataroots do not upload.'''
    from siliconcompiler.remote.client.run import RemoteRun

    published = json.loads(json.dumps(capabilities))
    published["software"]["python"]["scfakedata"] = ["1.0.0"]
    fake_v1.replace(responses.GET, "", published)

    run = RemoteRun(nop_project, logged_in)

    assert run._requested_python()["scfakedata"] == ["==1.0.0"]
    assert not run._uploaded_packages()


def test_an_installed_package_the_server_does_not_list_here_uploads(
        fake_v1, logged_in, nop_project, capabilities, installed_data):
    '''Where `software` lists it at another version, or not at all, it is
    not named, and its files go up with the job.'''
    from siliconcompiler.remote.client.run import RemoteRun

    published = json.loads(json.dumps(capabilities))
    published["software"]["python"]["scfakedata"] = ["0.9.0"]
    fake_v1.replace(responses.GET, "", published)

    run = RemoteRun(nop_project, logged_in)

    assert "scfakedata" not in run._requested_python()
    assert run._uploaded_packages() == {installed_data}


def test_a_framework_distribution_carries_the_range_siliconcompiler_declares(
        fake_v1, logged_in, gcd_design):
    '''cocotb, for a cocotb task, at SiliconCompiler's own range: the
    image's version within it runs.'''
    from importlib import metadata

    from packaging.requirements import Requirement

    from siliconcompiler import Flowgraph, Project
    from siliconcompiler.remote.client.run import RemoteRun
    from test_capture import RunsATestbench

    open("tb.py", "w").write("")
    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("framework")
    flow.node("sim", RunsATestbench())
    project.set_flow(flow)

    declared = next((str(Requirement(line).specifier)
                     for line in metadata.requires("siliconcompiler") or []
                     if Requirement(line).name == "scfakebits"), None)
    pins = RemoteRun(project, logged_in)._requested_python()

    # scfakebits is RunsATestbench's framework distribution; nothing declares
    # a range for it, so it is pinned where installed and left out where not.
    assert declared is None
    assert "scfakebits" in pins
    assert pins["siliconcompiler"]


def test_a_cocotb_node_names_cocotb_even_where_its_setup_cannot_run(
        fake_v1, logged_in, gcd_design):
    '''Declared on the task's class, so Verilator's compile step -- which
    runs none of the user's Python, and needs Verilator's setup -- still
    lands where cocotb is.'''
    from importlib import metadata

    from packaging.requirements import Requirement

    from siliconcompiler import Flowgraph, Project
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.tools.verilator.cocotb_compile import CocotbCompileTask

    project = Project(gcd_design)
    project.add_fileset("rtl")
    flow = Flowgraph("cocotbcompile")
    flow.node("compile", CocotbCompileTask())
    project.set_flow(flow)

    declared = [str(Requirement(line).specifier)
                for line in metadata.requires("siliconcompiler") or []
                if Requirement(line).name == "cocotb"]
    assert RemoteRun(project, logged_in)._requested_python()["cocotb"] == declared


def test_cocotbs_range_is_siliconcompilers():
    from importlib import metadata

    from packaging.requirements import Requirement

    from siliconcompiler.remote.client.run import _framework_range

    declared = [str(Requirement(line).specifier)
                for line in metadata.requires("siliconcompiler") or []
                if Requirement(line).name == "cocotb"]
    assert declared
    assert _framework_range("cocotb") == declared[0]


def test_a_reused_job_skips_the_upload(fake_v1, run):
    '''The prize is the upload: a hit skips the presigned PUT entirely.'''
    fake_v1.route(responses.POST, "jobs", job_body("completed"), status=200)

    job_id = run._start()

    assert job_id == "01J9-job"
    assert not [call for call in fake_v1.calls
                if "upload-grant" in call.request.path_url]


###########################
# Polling
###########################

def test_the_loop_ends_on_terminal_and_not_on_the_name(fake_v1, run, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("running"))
    fake_v1.route(responses.GET, "jobs/01J9-job",
                  job_body("quiescing", terminal=True))

    with pytest.raises(RemoteError):
        run._poll("01J9-job")

    # It stopped rather than polling a state it has never heard of for ever.
    assert len([c for c in fake_v1.calls if c.request.method == "GET"]) >= 2


def test_the_server_sets_the_pace(fake_v1, run, monkeypatch):
    '''`Retry-After` per response, rather than one number read at the start of
    the run and used to the end.'''
    slept = []
    monkeypatch.setattr("time.sleep", lambda s: slept.append(s))

    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("running"),
                  headers={"Retry-After": "17"})
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run._poll("01J9-job")

    assert 17 in slept


def test_an_unreadable_retry_after_is_not_a_failed_poll(fake_v1, run, monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", lambda s: slept.append(s))

    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("running"),
                  headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run._poll("01J9-job")

    assert slept


def test_node_states_are_recorded(fake_v1, run, nop_project):
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "completed",
        nodes=[{"step": "stepone", "index": "0", "state": "completed",
                "terminal": True, "started_at": None, "finished_at": None,
                "exit_code": 0, "error": None},
               {"step": "steptwo", "index": "0", "state": "skipped",
                "terminal": True, "started_at": None, "finished_at": None,
                "exit_code": None, "error": None}]))

    run._poll("01J9-job")

    assert nop_project.get('record', 'status', step="stepone", index="0") == "success"
    assert nop_project.get('record', 'status', step="steptwo", index="0") == "skipped"


def test_a_node_the_project_has_never_heard_of_does_not_end_the_run(
        fake_v1, run, monkeypatch):
    '''A body that is not the documented shape must not end a run that is still
    going.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "completed",
        nodes=[{"step": "nowhere", "index": "9", "state": "completed",
                "terminal": True},
               {"state": "completed", "terminal": True}]))

    run._poll("01J9-job")


###########################
# 🔴 A refusal ends the wait; a server error does not
###########################

def test_a_refusal_ends_the_run_as_a_failure(fake_v1, run):
    '''🔴 The difference between "your job failed" and "your job is done and
    empty". Falling through would announce a finished job with nothing in it.'''
    fake_v1.route(responses.GET, "jobs/01J9-job",
                  problem("not-found", 404), status=404,
                  content_type="application/problem+json")

    with pytest.raises(RemoteError) as raised:
        run._poll("01J9-job")

    assert "01J9-job" in str(raised.value)


def test_a_server_error_is_a_hiccup_and_the_wait_continues(fake_v1, run, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    fake_v1.route(responses.GET, "jobs/01J9-job", "<html>Bad Gateway</html>",
                  status=502, content_type="text/html")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run._poll("01J9-job")


def test_a_proxys_html_502_is_rendered_not_thrown_on(fake_v1, run, monkeypatch, caplog):
    '''🔴 problem+json is promised only for what a handler produced, so
    resp.json()["type"] throws on exactly the errors production serves most.'''
    monkeypatch.setattr("time.sleep", lambda *_: None)

    fake_v1.route(responses.GET, "jobs/01J9-job",
                  "<html><body><h1>502 Bad Gateway</h1></body></html>",
                  status=502, content_type="text/html")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    with caplog.at_level("WARNING"):
        run._poll("01J9-job")

    assert "Bad Gateway" in caplog.text


def test_a_server_that_never_comes_back_is_bounded(fake_v1, run, monkeypatch):
    '''A bounded retry, not an infinite one.'''
    monkeypatch.setattr("time.sleep", lambda *_: None)

    for _ in range(40):
        fake_v1.route(responses.GET, "jobs/01J9-job", "oops", status=500,
                      content_type="text/plain")

    with pytest.raises(RemoteError):
        run._poll("01J9-job")


def test_not_ready_is_a_wait_rather_than_a_refusal(fake_v1, run, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    fake_v1.route(responses.GET, "jobs/01J9-job",
                  problem("not-ready", 409), status=409,
                  content_type="application/problem+json")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run._poll("01J9-job")


def test_a_failed_job_ends_the_run(fake_v1, run):
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        error={"type": "https://siliconcompiler.com/server-errors/run-failed",
               "title": "The run failed"}))

    with pytest.raises(RemoteError):
        run._poll("01J9-job")


###########################
# Reconnect
###########################

def test_reconnect_needs_a_job_to_reconnect_to(run):
    with pytest.raises(RemoteError) as raised:
        run.reconnect()

    assert "never submitted" in str(raised.value)


def test_reconnect_re_enters_the_wait(fake_v1, run, nop_project):
    '''🔴 The answer to Ctrl-C, and the only way back to a detached job.'''
    nop_project.set('record', 'remoteid', "01J9-job")
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body("completed"))

    run.reconnect()


###########################
# The rest of the surface
###########################

###########################
# A page for a person's browser: POST /v1/auth/browser (surface D309)
###########################

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


def test_after_a_submit_the_jobs_page_is_asked_for_by_its_id(fake_v1, run, opened):
    '''🔴 Asked for, never built: the body names the job, and the client opens
    what comes back.'''
    fake_v1.route(responses.POST, "auth/browser", SIGN_IN)

    run._open_portal("01J9-job")

    page, = _pages(fake_v1)
    assert json.loads(page.body) == {"job_id": "01J9-job"}
    assert page.headers["Authorization"].startswith("DPoP ")
    assert opened == [SIGN_IN["url"]]


def test_a_sign_in_is_printed_only_where_no_browser_opened_and_never_logged(
        fake_v1, run, monkeypatch, caplog, capsys):
    '''A sign-in link is a bearer secret for its page: opened, printed to the
    terminal only where no browser opened, and never through the logger.'''
    import logging

    caplog.set_level(logging.DEBUG)
    fake_v1.route(responses.POST, "auth/browser", SIGN_IN)

    monkeypatch.setattr(run.client, "open_url",
                        lambda url, what, require_tty=True: True)
    assert run.client.open_page("the job's page", job_id="01J9-job") is True
    assert "token=t" not in capsys.readouterr().out

    monkeypatch.setattr(run.client, "open_url",
                        lambda url, what, require_tty=True: False)
    assert run.client.open_page("the job's page", job_id="01J9-job") is False
    assert SIGN_IN["url"] in capsys.readouterr().out

    assert "token=t" not in caplog.text


def test_a_plain_page_is_printed_and_opened(fake_v1, run, opened, caplog):
    '''`expires_at: null` is the page itself, crucible's answer: it needs no
    secrecy, so it is printed as well as opened.'''
    import logging

    caplog.set_level(logging.INFO)
    fake_v1.route(responses.POST, "auth/browser",
                  {"url": "https://crucible.test/jobs/01J9-job", "expires_at": None})

    run._open_portal("01J9-job")

    assert opened == ["https://crucible.test/jobs/01J9-job"]
    assert "https://crucible.test/jobs/01J9-job" in caplog.text


@pytest.mark.parametrize("status", [404, 403])
def test_a_refused_page_is_said_and_the_run_carries_on(fake_v1, run, opened, caplog,
                                                       status):
    '''Nothing is opened in its place, and nothing is built: the reason is
    said rather than swallowed, and the run goes on.'''
    fake_v1.route(responses.POST, "auth/browser",
                  problem("not-found" if status == 404 else "not-permitted", status),
                  status=status, content_type="application/problem+json")

    run._open_portal("01J9-job")

    assert opened == []
    assert "No page for the job's page" in caplog.text


def test_a_ci_session_never_asks_for_a_page(fake_v1, run, opened):
    from siliconcompiler.remote.client import GRANT_TOKEN_EXCHANGE

    run.client._mode = GRANT_TOKEN_EXCHANGE

    run._open_portal("01J9-job")

    assert not _pages(fake_v1)
    assert not opened
    with pytest.raises(RemoteError, match="CI session"):
        run.client.portal()
    assert not _pages(fake_v1)


def test_sc_remote_portal_asks_for_the_home_page(fake_v1, run, opened):
    fake_v1.route(responses.POST, "auth/browser", SIGN_IN)

    run.client.portal()

    page, = _pages(fake_v1)
    assert json.loads(page.body) == {}
    assert opened == [SIGN_IN["url"]]


def test_a_refused_portal_command_fails_and_says_why(fake_v1, run, opened):
    '''Asked for on purpose, so the command fails rather than carrying on.'''
    fake_v1.route(responses.POST, "auth/browser", problem("not-permitted", 403),
                  status=403, content_type="application/problem+json")

    with pytest.raises(RemoteError, match="not-permitted|Not permitted"):
        run.client.portal()
    assert opened == []


def test_listing_follows_the_link_header(fake_v1, logged_in):
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("completed")]},
                  headers={"Link": '</v1/jobs?limit=1&cursor=abc>; rel="next"'})
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("failed")]})

    assert len(logged_in.jobs()) == 2


@pytest.mark.parametrize("link", [
    "</v1/jobs?limit=1&cursor=abc&kept=1>; rel=next",
    '</v1/jobs?cursor=zzz>; rel="prev", </v1/jobs?limit=1&cursor=abc&kept=1>; rel="next"',
    '<https://sc-server.test/v1/jobs?limit=1&cursor=abc&kept=1>; title="a, b"; rel="next last"',
], ids=["unquoted", "second", "absolute"])
def test_the_next_page_is_the_link_target_as_given(fake_v1, logged_in, link):
    '''Surface D306 and RFC 8288: whichever link-value says `rel="next"`,
    quoted or not, and its URL requested unchanged -- never this request
    rebuilt around a cursor, which would drop what the server put there and
    re-add the filters it already carries.'''
    from urllib.parse import urlsplit

    fake_v1.route(responses.GET, "jobs", {"items": [job_body("completed")]},
                  headers={"Link": link})
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("failed")]})

    assert len(logged_in.jobs(archived=True)) == 2

    pages = [c.request.url for c in fake_v1.calls if urlsplit(c.request.url).path == "/v1/jobs"]
    assert pages[-1] == "https://sc-server.test/v1/jobs?limit=1&cursor=abc&kept=1"


def test_a_next_page_on_another_origin_is_not_followed(fake_v1, logged_in):
    '''The request carries this session: only to the API's own origin.'''
    fake_v1.route(responses.GET, "jobs", {"items": []},
                  headers={"Link": '<https://elsewhere.test/v1/jobs?cursor=a>; rel="next"'})

    with pytest.raises(RemoteError, match="another origin"):
        logged_in.jobs()

    assert not [c for c in fake_v1.calls if "elsewhere" in c.request.url]


def test_a_boolean_filter_goes_as_true_or_false(fake_v1, logged_in):
    '''S §16's spelling, never Python's `True`, which a strict server refuses
    and a lax one reads as false.'''
    from urllib.parse import parse_qs, urlsplit

    fake_v1.route(responses.GET, "jobs", {"items": []})
    fake_v1.route(responses.GET, "jobs", {"items": []})

    logged_in.jobs(archived=True, terminal=False)
    logged_in.jobs(archived=[True, False])

    first, second = [parse_qs(urlsplit(call.request.url).query)
                     for call in fake_v1.calls if urlsplit(call.request.url).path == "/v1/jobs"]
    assert (first["archived"], first["terminal"]) == (["true"], ["false"])
    assert second["archived"] == ["true", "false"]


def test_a_cancel_with_nothing_to_add_says_where_it_came_from(fake_v1, logged_in):
    """🔴 `reason` is optional on the wire -- requiring it would make a Ctrl-C
    inexpressible -- and this client always sends one anyway. It names the
    tool and nothing about the machine: a hostname is not the client's to
    publish on a job page."""
    import socket

    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  job_body("cancelling"), status=202)

    logged_in.cancel_job("01J9-job")

    body = json.loads(fake_v1.calls[-1].request.body)
    assert body["reason"] == "cancelled from sc-remote"
    assert socket.gethostname() not in body["reason"]


def test_a_cancel_with_a_reason_sends_that_one(fake_v1, logged_in):
    """The caller's own words win: what this client can say for itself is a
    fallback, not a prefix."""
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  job_body("cancelling"), status=202)

    logged_in.cancel_job("01J9-job", reason="wrong constraints")

    assert json.loads(fake_v1.calls[-1].request.body) == {
        "reason": "wrong constraints"}


@pytest.mark.parametrize("reason,said", [("é" * 301, "at most 300 characters"),
                                         ("two\nlines", "control character"),
                                         ("a\x9bb", "control character")])
def test_a_cancel_reason_is_checked_before_it_is_sent(fake_v1, logged_in, reason, said):
    '''Surface D306: at most 300 Unicode code points and no control
    character, checked here, naming which, and nothing sent.'''
    with pytest.raises(RemoteError, match=said):
        logged_in.cancel_job("01J9-job", reason=reason)

    assert not [c for c in fake_v1.calls if c.request.url.endswith("/cancel")]


def test_a_cancel_reason_of_300_code_points_is_sent(fake_v1, logged_in):
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  job_body("cancelling"), status=202)

    logged_in.cancel_job("01J9-job", reason="é" * 300)

    assert json.loads(fake_v1.calls[-1].request.body) == {"reason": "é" * 300}


def test_delete_is_a_204_with_no_body(fake_v1, logged_in):
    fake_v1.route(responses.DELETE, "jobs/01J9-job", "", status=204,
                  content_type="")

    assert logged_in.delete_job("01J9-job") is None


def test_the_grants_content_length_is_not_forwarded(fake_v1, logged_in, tmp_path):
    '''🔴 The grant publishes the byte count it was issued for, and where the
    descriptor carried no size that is the server's ceiling rather than this
    archive's length. Forwarding it announces a gigabyte and sends twenty
    kilobytes, and the server waits for the rest for ever.'''
    payload = tmp_path / "upload.tar.gz"
    payload.write_bytes(b"x" * 20)

    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")

    logged_in.upload({"url": "https://storage.test/put",
                      "headers": {"content-length": "1073741824"}}, payload)

    sent = fake_v1.calls[-1].request
    assert sent.headers["Content-Length"] == "20"


###########################
# Every refusal POST /v1/jobs can make
###########################
#
# 🔴 This is the half the integration rig cannot reach. A working server can be
# made to exceed its own node limit, but not to report a limit it does not have,
# refuse a feature it implements, or answer with a proxy's HTML -- and a client
# that renders one of these badly is found by a user, at the end of a long day,
# with a gigabyte half uploaded.

@pytest.mark.parametrize("slug,status,members,expected", [
    ("limit-exceeded", 429, {"limit": "pending_uploads"},
     ["limit: pending_uploads", "refills"]),
    ("node-limit-exceeded", 403, {"limit": "max_job_nodes"},
     ["limit: max_job_nodes", "smaller flow"]),
    ("upload-too-large", 413, {"limit": "max_upload_bytes"},
     ["limit: max_upload_bytes", "waiting will not help"]),
    ("feature-unsupported", 501, {"feature": "projects"},
     ["feature: projects", "does not offer that"]),
    ("entitlement-denied", 403, {"resource_kind": "pdk", "resource": "gf12"},
     ["resource: gf12", "resource_kind: pdk", "Ask for a grant"]),
    # Each entry says which requirement failed by its `kind` (surface D311).
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
    ("idempotency-key-reuse", 422, {},
     ["A retry changed the request"]),
    ("invalid-request", 400, {}, ["Invalid request"]),
])
def test_every_create_refusal_renders(fake_v1, logged_in, slug, status, members,
                                      expected):
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.POST, "jobs", problem(slug, status, **members),
                  status=status, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    assert raised.value.slug == slug
    rendered = str(raised.value)
    for fragment in expected:
        assert fragment in rendered, rendered
    # The page link is beside the trace, not instead of the sentence: most
    # people never open it.
    assert f"server-errors/{slug}" in rendered


def test_a_resource_named_without_its_kind_prints_cleanly(fake_v1, logged_in):
    '''A deployment with no catalogue names the resource alone (surface
    D285): printed by name, and never as `resource_kind: None`.'''
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.POST, "jobs",
                  problem("resource-unavailable", 422, resource="secret",
                          detail="secret (secret) is marked private, and this server "
                                 "holds no copy of it"),
                  status=422, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    rendered = str(raised.value)
    assert "resource: secret" in rendered
    assert "resource_kind" not in rendered and "None" not in rendered


def test_a_cancel_reason_over_300_is_refused_before_it_is_sent(fake_v1, logged_in):
    '''The server would refuse it, never cut it (surface D288): so the client
    says so first, naming the limit, and sends nothing.'''
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel", job_body("cancelling"),
                  status=202)

    with pytest.raises(RemoteError, match="at most 300 characters"):
        logged_in.cancel_job("01J9-job", reason="x" * 301)
    assert not [c for c in fake_v1.calls if c.request.path_url.endswith("/cancel")]

    logged_in.cancel_job("01J9-job", reason="x" * 300)
    cancel, = [c for c in fake_v1.calls if c.request.path_url.endswith("/cancel")]
    assert json.loads(cancel.request.body)["reason"] == "x" * 300


def test_a_refusal_carrying_a_trace_id_shows_it(fake_v1, logged_in):
    '''What an operator asks for when a user reports it.'''
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.POST, "jobs",
                  problem("limit-exceeded", 429, limit="concurrent_jobs",
                          trace_id="0af7651916cd43dd8448eb211c80319c"),
                  status=429, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    assert "trace 0af7651916cd43dd8448eb211c80319c" in str(raised.value)


def test_a_create_refused_by_something_that_is_not_the_handler(fake_v1, logged_in):
    '''🔴 problem+json is promised only for what a handler produced. A gateway
    in front of the server answers in its own shape, and those are the errors
    production serves most.'''
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.POST, "jobs",
                  "<html><head><title>502 Bad Gateway</title></head></html>",
                  status=502, content_type="text/html")

    with pytest.raises(ServerProblem) as raised:
        logged_in.create_job("gcd", "job0")

    assert raised.value.slug is None
    assert "502" in str(raised.value)


def test_an_archive_refusal_names_the_rule_that_was_broken(fake_v1, logged_in):
    '''One slug and six discriminators: the registry is frozen, so the thing
    that says WHICH has to be a member.'''
    from siliconcompiler.remote import ServerProblem

    fake_v1.route(responses.POST, "jobs/01J9-job/submit",
                  problem("archive-rejected", 422, reason="link_member"),
                  status=422, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        logged_in.submit_job("01J9-job", "sha256:" + "0" * 64)

    assert "reason: link_member" in str(raised.value)


###########################
# A failed run says why, without opening a URL
###########################

def _node(step, state, **extra):
    node = {"step": step, "index": "0", "state": state,
            "terminal": state in ("completed", "failed", "skipped", "cancelled"),
            "started_at": None, "finished_at": None, "exit_code": None,
            "error": None}
    node.update(extra)
    return node


def test_a_failed_run_explains_itself_and_still_fetches(fake_v1, run, caplog):
    '''🔴 Results are retrieved on EVERY terminal state. A failed run is the one
    whose log and manifest a user most wants, and a client that fetches nothing
    when a job fails has hidden the evidence at the moment it became useful.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        nodes=[_node("stepone", "failed"), _node("steptwo", "cancelled")],
        error={"type": "https://siliconcompiler.com/server-errors/run-failed",
               "title": "The run failed"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts",
                  {"items": []})

    with caplog.at_level("INFO"):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")

    assert "The run failed" in caplog.text
    # The next step is in the client, because the type page is static and
    # identical on every deployment -- so the server cannot say anything
    # specific through it.
    assert "Read the failing node's log" in caplog.text
    # It asked for the results rather than giving up on them.
    assert any("artifacts" in call.request.path_url for call in fake_v1.calls)


def test_a_failed_node_says_why(fake_v1, run, caplog):
    '''A node's `error` has the job's shape (surface §17): its `detail` names
    the limit it ran into, or the image that would not pull, and is printed
    beside the node, where nothing was before.'''
    run_failed = "https://siliconcompiler.com/server-errors/run-failed"
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        nodes=[_node("stepone", "failed",
                     error={"type": run_failed, "title": "The run failed",
                            "detail": "the node exceeded its time limit"}),
               _node("steptwo", "cancelled")],
        error={"type": run_failed, "title": "The run failed",
               "detail": "stepone/0 exceeded its time limit"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with caplog.at_level("INFO"):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")

    assert "stepone/0 failed: the node exceeded its time limit" in caplog.text
    assert "steptwo/0 failed" not in caplog.text


def test_a_run_that_failed_with_no_failed_node_says_so(fake_v1, run, caplog):
    '''🔴 A flow that dies before its first node fails with every node
    `cancelled` and none of them `failed`, and *read the failing node's log*
    then names a file nobody can open. The advice is chosen from the job, not
    from the slug.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        nodes=[_node("stepone", "cancelled"), _node("steptwo", "cancelled")],
        error={"type": "https://siliconcompiler.com/server-errors/run-failed",
               "title": "The run failed",
               "detail": "RuntimeError: git is required to import GitPython"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with caplog.at_level("INFO"):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")

    assert "Read the failing node's log" not in caplog.text
    assert "No node failed" in caplog.text
    # And the server's `detail` is the only part of the body that is about THIS
    # run, so it has to survive the render.
    assert "git is required" in caplog.text


def test_an_interrupted_run_is_told_apart_from_a_failed_one(fake_v1, run, caplog):
    '''The environment ended it and re-running may succeed: different words,
    and a different next step.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        error={"type": "https://siliconcompiler.com/server-errors/run-interrupted",
               "title": "The run was interrupted"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with caplog.at_level("INFO"):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")

    assert "resubmitting unchanged may work" in caplog.text
    # The support reference for a job's failure is the job id.
    assert "job 01J9-job" in caplog.text


def test_the_failure_render_needs_no_url(fake_v1, run, caplog):
    '''Short enough to read in a terminal, and self-contained.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        error={"type": "https://siliconcompiler.com/server-errors/run-failed",
               "title": "The run failed"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with caplog.at_level("ERROR"):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")

    rendered = [r.message for r in caplog.records if "run failed" in r.message.lower()]
    assert rendered
    assert len(rendered[0].splitlines()) <= 4


###########################
# Watching a run
###########################

def test_streamed_lines_are_not_prefixed_a_second_time(fake_v1, run, nop_project,
                                                       capsys):
    '''🔴 A node's log already carries `job | step | index` on every line.
    Logging it normally stamped this run's own prefix on top:

      | INFO | job0 | remote | - | | INFO | job0 | route.detailed | 0 | Running

    The line that says which node it came from is the one that matters, so the
    lines go out with a blank formatter.
    '''
    from siliconcompiler.remote.client.run import _Tails

    tails = _Tails.__new__(_Tails)
    tails._run = run
    tails._logger = run.logger
    tails._stop = __import__("threading").Event()

    tails._write("| INFO     | job0 | route.detailed       | 0 | Running\n")

    printed = capsys.readouterr().err + capsys.readouterr().out
    assert "remote" not in printed


def test_the_dashboard_is_given_the_states_and_the_clocks(fake_v1, run,
                                                          nop_project):
    '''🔴 Without this the dashboard renders whatever it had when the run
    started -- the record is updated on the project and nothing tells the board
    to look again. `starttimes` is what makes the per-node timer run.'''
    painted = []

    class Board:
        def is_running(self):
            return True

        def update_manifest(self, payload=None):
            painted.append(payload)

    nop_project._Project__dashboard = Board()

    run._paint(job_body("running", nodes=[
        {"step": "stepone", "index": "0", "state": "running", "terminal": False,
         "started_at": "2026-09-22T10:00:00.000Z"},
        {"step": "steptwo", "index": "0", "state": "pending", "terminal": False,
         "started_at": None}]))

    assert painted
    starttimes = painted[0]["starttimes"]
    assert starttimes == {("stepone", "0"): 1790071200.0}


def test_a_finished_node_has_a_time_before_its_manifest_arrives(
        fake_v1, run, nop_project):
    '''🔴 The job object says when each node started and ended, so the time
    column need not wait for the manifest -- which a deployment may withhold.
    A running node keeps its ticking clock; one that never ran has no time.'''
    painted = []

    class Board:
        def is_running(self):
            return True

        def update_manifest(self, payload=None):
            painted.append(payload)

    nop_project._Project__dashboard = Board()

    run._paint(job_body("running", nodes=[
        {"step": "stepone", "index": "0", "state": "completed", "terminal": True,
         "started_at": "2026-09-22T10:00:00.000Z",
         "finished_at": "2026-09-22T10:01:30.500Z"},
        {"step": "steptwo", "index": "0", "state": "running", "terminal": False,
         "started_at": "2026-09-22T10:01:31.000Z", "finished_at": None},
        {"step": "stepthree", "index": "0", "state": "skipped", "terminal": True,
         "started_at": None, "finished_at": None}]))

    assert painted[0]["durations"] == {("stepone", "0"): 90.5}


def test_a_dashboard_run_reports_only_what_moved(fake_v1, run, nop_project, caplog):
    '''The dashboard is already showing every node's state, so the full table
    underneath it is the same information twice. What it cannot show is the
    moment something moved.'''
    class Board:
        def is_running(self):
            return True

        def update_manifest(self, payload=None):
            pass

    nop_project._Project__dashboard = Board()

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
    from siliconcompiler.tools.builtin.nop import NOPTask

    flow = Flowgraph("fp")
    for step in ("tapcell", "power_grid", "pin_placement"):
        flow.node(step, NOPTask())
    flow.edge("tapcell", "power_grid")
    flow.edge("power_grid", "pin_placement")
    nop_project.set_flow(flow)
    return RemoteRun(nop_project, logged_in)


def test_what_moved_in_one_poll_is_listed_in_the_order_it_moved(floorplan):
    '''🔴 A poll carries a node finishing and the one it unblocked starting,
    and the server lists nodes by name: listed so, a node would start before
    the one it waits on finished.'''
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


def test_where_nothing_says_when_the_flows_order_decides(floorplan):
    job = job_body("running", nodes=[_node(step, "pending") for step in
                                     ("pin_placement", "power_grid", "tapcell")])

    assert [step for step, _, _ in floorplan._record(job, {})] == \
        ["tapcell", "power_grid", "pin_placement"]


def test_the_whole_table_lists_each_state_in_the_flows_order(fake_v1, floorplan, caplog):
    job = job_body("running", nodes=[_node(step, "pending") for step in
                                     ("pin_placement", "power_grid", "tapcell")])

    with caplog.at_level("INFO"):
        floorplan._report(job, changed=[])

    assert "Pending (3): tapcell/0, power_grid/0, pin_placement/0" in caplog.text


def test_a_server_with_no_live_tail_simply_does_not_tail(fake_v1, run,
                                                         capabilities):
    '''Point 2: if the logs cannot be streamed, what we already print is fine.
    The archived log still arrives with the results.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.replace(responses.GET, "", dict(capabilities, features=[]))

    assert _Tails(run)._enabled is False


def test_quiet_means_quiet(fake_v1, run, nop_project):
    '''The same thing it means locally: do not put tool output on my
    terminal.'''
    from siliconcompiler.remote.client.run import _Tails

    nop_project.option.set_quiet(False)
    assert _Tails(run)._enabled is True

    nop_project.option.set_quiet(True)
    assert _Tails(run)._enabled is False


def test_the_tail_count_is_the_servers_published_ceiling(fake_v1, run):
    '''It is the server's thread and file descriptor being held, so the server
    says how many.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)

    tails = _Tails(run)
    assert tails._enabled is True
    assert tails._ceiling == 8


def _running_nodes(*steps):
    return {"nodes": [{"step": step, "index": "0", "state": "running",
                       "terminal": False} for step in steps]}


def test_with_a_job_stream_one_connection_follows_every_node(fake_v1, run,
                                                             monkeypatch):
    '''🔴 One stream however wide the flow -- which is what lets a flow wider
    than `concurrent_log_streams` be watched in full.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    opened = []
    monkeypatch.setattr(_Tails, "_tail_job", lambda self, job_id: opened.append(job_id))
    monkeypatch.setattr(_Tails, "_tail", lambda self, *node: opened.append(node))

    tails = _Tails(run)
    tails.follow("j1", _running_nodes("stepone", "steptwo"))
    tails.follow("j1", _running_nodes("stepone", "steptwo", "stepthree"))
    tails.finish()

    assert opened == ["j1"]


def test_without_one_each_running_node_is_followed(fake_v1, run, capabilities,
                                                   monkeypatch):
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.replace(responses.GET, "",
                    dict(capabilities, features=["logs.stream"]))
    opened = []
    monkeypatch.setattr(_Tails, "_tail", lambda self, *args: opened.append(args[1]))

    tails = _Tails(run)
    tails.follow("j1", _running_nodes("stepone", "steptwo"))
    tails.finish()

    assert sorted(opened) == ["stepone", "steptwo"]


def test_a_refused_job_stream_falls_back_for_good(fake_v1, run, monkeypatch):
    '''🔴 `feature-unsupported` naming `logs.stream.job` is permanent: follow
    each node from the next poll, and never ask for the job form again.'''
    from conftest import problem
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.route(responses.GET, "jobs/j1/logs",
                  problem("feature-unsupported", 501, feature="logs.stream.job"),
                  status=501, content_type="application/problem+json")

    tails = _Tails(run)
    tails._tail_job("j1")
    assert tails._whole_job is False

    opened = []
    monkeypatch.setattr(_Tails, "_tail", lambda self, *args: opened.append(args[1]))
    tails.follow("j1", _running_nodes("stepone"))
    tails.finish()

    assert opened == ["stepone"]
    asked = [c.request.path_url for c in fake_v1.calls if "/logs" in c.request.path_url]
    assert asked == ["/v1/jobs/j1/logs"]


def test_a_job_stream_asked_too_early_is_asked_again(fake_v1, run, monkeypatch):
    '''`not-ready` is transient: nothing had started when it was asked.'''
    from conftest import problem
    from siliconcompiler.remote.client.run import JOB, _Tails

    run.project.option.set_quiet(False)
    fake_v1.route(responses.GET, "jobs/j1/logs",
                  problem("not-ready", 409, artifact_kind="logs"),
                  status=409, content_type="application/problem+json")

    tails = _Tails(run)
    tails._started.add(JOB)
    tails._tail_job("j1")

    assert tails._whole_job is True
    assert JOB not in tails._started


def test_a_node_log_asked_too_early_is_asked_again(fake_v1, run):
    '''Review row 54: `409 not-ready` on a node's `/logs` is transient, as on
    the job's: the node is followed again from the next poll, and a refusal
    that is final is not.'''
    from conftest import problem
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.route(responses.GET, "jobs/j1/logs",
                  problem("not-ready", 409, artifact_kind="logs"),
                  status=409, content_type="application/problem+json")

    tails = _Tails(run)
    tails._started.add(("stepone", "0"))
    tails._tail("j1", "stepone", "0")
    assert ("stepone", "0") not in tails._started

    fake_v1.replace(responses.GET, "jobs/j1/logs", problem("not-found", 404),
                    status=404, content_type="application/problem+json")
    tails._started.add(("stepone", "0"))
    tails._tail("j1", "stepone", "0")
    assert ("stepone", "0") in tails._started


###########################
# What the flow will reach for
###########################

def test_the_software_preflight_warns_and_does_not_stop(fake_v1, run, capabilities,
                                                        monkeypatch):
    '''Client-v1-migration D16: create decides, from a `GET /v1` this client
    may hold stale, and its refusal costs no packing -- so a requirement
    nothing advertised satisfies is a warning here, never a stop.'''
    said = []
    monkeypatch.setattr(run.logger, "warning", lambda message, *_, **__: said.append(message))
    fake_v1.replace(responses.GET, "", dict(capabilities, software={
        "python": {"siliconcompiler": ["0.0.1"]}, "tools": {}, "interpreter": {}}))

    run._check_software()

    assert any("siliconcompiler 0.0.1" in message for message in said)


def test_the_descriptor_names_the_tools_the_flow_needs(fake_v1, logged_in,
                                                       gcd_nop_project):
    '''🔴 The point is the refusal BEFORE the upload. The server derives the
    same list from the manifest at submit, so this changes no placement -- it
    changes when a deployment that curates images for a tool and has none says
    so.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.tools.yosys.syn_asic import ASICSynthesis

    flow = Flowgraph("withtools")
    flow.node("syn", ASICSynthesis())
    gcd_nop_project.set_flow(flow)

    wanted = RemoteRun(gcd_nop_project, logged_in)._tool_requirements()

    # ⚠️ An empty list is *any version of this*: what a node whose setup could
    # not run here says -- this one needs a PDK -- and it still names the tool.
    assert wanted == {"yosys": []}


def test_a_tool_requirement_is_the_version_its_setup_declared(
        fake_v1, logged_in, gcd_nop_project):
    '''🔴 From the worked-out copy, where setup ran: a fresh task declares
    nothing, which is why this was dropped before.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.remote.client.run import RemoteRun

    flow = Flowgraph("declared")
    flow.node("run", DeclaresAVersion())
    gcd_nop_project.set_flow(flow)

    assert RemoteRun(gcd_nop_project, logged_in)._tool_requirements() == \
        {"sctesttool": [">=1.2.0,<2"]}


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


def test_a_builtin_node_names_no_tool(fake_v1, logged_in, nop_project):
    '''🔴 SiliconCompiler's own joins and nops run in its process. Treating
    `builtin` as a tool invites an operator to register a name no image can
    honestly claim, which then refuses every flow that has a join in it.'''
    from siliconcompiler.remote.client.run import RemoteRun

    assert RemoteRun(nop_project, logged_in)._tool_requirements() == {}


def test_a_declared_requirement_is_normalised_before_it_is_sent():
    '''🔴 OpenROAD declares `>=24Q3-2011`, which is not a PEP 440 specifier at
    all. Sent raw the server cannot parse it, falls back to comparing the
    string, and refuses an image that plainly satisfies it. The driver is the
    only thing that knows how to make it comparable, and the client is the side
    that has the driver.'''
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    from siliconcompiler.remote.client.run import _normalize_spec
    from siliconcompiler.tools.openroad import OpenROADTask

    spec = _normalize_spec(OpenROADTask(), ">=24Q3-2011")

    assert spec == ">=24.3.2011"
    # And what the probe stores for a real OpenROAD satisfies it, which is the
    # whole round trip.
    assert Version("26.3.2418") in SpecifierSet(spec)


def test_a_comma_separated_set_keeps_all_of_its_parts():
    '''A set's commas are AND and each part is normalised on its own.'''
    from siliconcompiler.remote.client.run import _normalize_spec
    from siliconcompiler.tools.openroad import OpenROADTask

    assert _normalize_spec(OpenROADTask(), ">=24Q3-2011,<27Q1-0") == \
        ">=24.3.2011,<27.1.0"


def test_an_unreadable_requirement_is_dropped_rather_than_sent():
    '''An unparsable requirement matches nothing on the far side, so passing it
    on turns *no version I can read* into *no OpenROAD at all*.'''
    from siliconcompiler.remote.client.run import _normalize_spec
    from siliconcompiler.tools.openroad import OpenROADTask

    assert _normalize_spec(OpenROADTask(), "whatever") is None


def test_a_development_client_asks_by_prefix_rather_than_exactly():
    '''🔴 `0.38.10.dev43+g20db24fa2` carries a commit in its local segment, so
    an exact pin from a checkout can only ever match an image built from that
    same commit -- which is nobody's image.

    ⚠️ The spelling is `==0.38.10.*`: a `.*` attaches to the release segment
    and nothing after it, so `==0.38.10.dev*` is rejected outright. The legal
    one matches every build of that release line, dev ones included.
    '''
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import Version

    import siliconcompiler.remote.client.run as run

    before = run.sc_version
    try:
        run.sc_version = "0.38.10.dev43+g20db24fa2.d20260924"
        spec = run._framework_requirement()
        assert spec == "==0.38.10.*"

        matches = SpecifierSet(spec, prereleases=True)
        assert Version("0.38.10.dev7") in matches
        assert Version("0.38.10") in matches
        assert Version("0.38.9") not in matches

        run.sc_version = "0.38.9"
        assert run._framework_requirement() == "==0.38.9"
    finally:
        run.sc_version = before

    with pytest.raises(InvalidSpecifier):
        SpecifierSet("==0.38.10.dev*")


###########################
# What is uploaded
###########################

def _packed(run, tmp_path):
    import tarfile

    upload = tmp_path / "upload.tar.gz"
    run._pack(upload)
    with tarfile.open(upload) as tar:
        return {name for name in tar.getnames() if name}


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


def test_only_the_manifest_and_the_sources_are_uploaded(run, nop_project, tmp_path):
    '''🔴 Not the whole job directory. One that has run before holds the last
    run's handle, its logs, and every node it fetched back -- none of which a
    full run reads -- and `job.log`, which this run has open.'''
    _leftovers(nop_project)

    names = _packed(run, tmp_path)

    assert "gcd.pkg.json" in names
    assert "sc_collected_files/gcd.v" in names
    assert not {n for n in names if n.endswith(".log")}
    assert "sc_remote.pkg.json" not in names
    assert not {n for n in names if n.startswith(("stepone", "steptwo"))}


def _sent(run, tmp_path, member="gcd.pkg.json"):
    '''A manifest the archive carries, read back, and every member's bytes.'''
    import tarfile

    from siliconcompiler import Project

    upload = tmp_path / "upload.tar.gz"
    run._pack(upload)
    with tarfile.open(upload) as tar:
        blobs = {info.name: tar.extractfile(info).read()
                 for info in tar.getmembers() if info.isfile()}
    (tmp_path / "sent.pkg.json").write_bytes(blobs[member])
    return Project.from_manifest(filepath=str(tmp_path / "sent.pkg.json")), blobs


def _registered_with_credentials(project):
    design = project.get("library", "gcd", field="schema")
    design.set_dataroot("ip", "git+https://alice:TOKEN@example.com/ip.git", "v1")
    design.set_dataroot("secret", "git+https+private://alice:TOKEN@example.com/secret.git",
                        "v1")
    project.set("tool", "builtin", "task", "nop", "dataroot", "scripts", "path",
                "https://example.com/scripts.tar.gz?token=TOKEN")


def test_the_uploaded_manifest_carries_no_credential(run, nop_project, tmp_path):
    '''🔴 Surface D302: every dataroot's path goes up without its userinfo and
    with every query value masked -- a library's, a private one, a task's and
    the history's -- and the user's own project and manifest keep what they
    registered.'''
    from siliconcompiler.remote import owners
    from siliconcompiler.utils.paths import jobdir

    _registered_with_credentials(nop_project)
    nop_project._record_history()
    _leftovers(nop_project)
    own = os.path.join(jobdir(nop_project), "gcd.pkg.json")
    nop_project.write_manifest(own)

    sent, blobs = _sent(run, tmp_path)

    paths = dict(owners.dataroot_paths(sent))
    assert paths[("library", "gcd", "dataroot", "ip")] == "git+https://example.com/ip.git"
    assert paths[("library", "gcd", "dataroot", "secret")] == \
        "git+https+private://example.com/secret.git"
    assert paths[("tool", "builtin", "task", "nop", "dataroot", "scripts")] == \
        "https://example.com/scripts.tar.gz?token=***"
    assert ("history", "job0", "library", "gcd", "dataroot", "ip") in paths
    assert not [name for name, body in blobs.items() if b"TOKEN" in body]

    # The manifest still carries the set the archive was filtered by.
    assert owners.required(sent) == owners.required(run._needs()[0])
    assert nop_project.get("library", "gcd", "dataroot", "ip", "path") == \
        "git+https://alice:TOKEN@example.com/ip.git"
    with open(own) as f:
        assert "alice:TOKEN" in f.read()


def test_an_upstream_nodes_manifest_goes_up_without_its_credential(
        run, nop_project, tmp_path):
    '''A `-from` run carries each upstream node's own manifest in its
    `outputs/`, and it records every dataroot's path as the root one does.'''
    from siliconcompiler.remote import owners

    _registered_with_credentials(nop_project)
    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    nop_project.write_manifest(os.path.join(outputs, "gcd.pkg.json"))
    nop_project.option.add_from("steptwo")

    upstream, blobs = _sent(run, tmp_path, member="stepone/0/outputs/gcd.pkg.json")

    assert dict(owners.dataroot_paths(upstream))[("library", "gcd", "dataroot", "ip")] == \
        "git+https://example.com/ip.git"
    assert blobs["stepone/0/outputs/gcd.vg"] == b"module gcd; endmodule\n"
    assert not [name for name, body in blobs.items() if b"TOKEN" in body]
    with open(os.path.join(outputs, "gcd.pkg.json")) as f:
        assert "alice:TOKEN" in f.read()


def test_an_upstream_manifest_that_holds_none_goes_as_it_is(run, nop_project, tmp_path):
    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    nop_project.option.add_from("steptwo")
    with open(os.path.join(outputs, "gcd.pkg.json"), "rb") as f:
        written = f.read()

    _, blobs = _sent(run, tmp_path)

    assert blobs["stepone/0/outputs/gcd.pkg.json"] == written


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


def test_a_run_from_part_way_sends_the_results_it_starts_from(
        run, nop_project, tmp_path):
    '''`-from steptwo`: stepone's results are on this machine, and steptwo
    reads them -- its outputs and nothing else of the node. steptwo's own are
    replaced by the run.'''
    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    os.makedirs(os.path.join(os.path.dirname(outputs), "inputs"), exist_ok=True)
    nop_project.option.add_from("steptwo")

    names = _packed(run, tmp_path)

    assert {"stepone/0/outputs/gcd.pkg.json", "stepone/0/outputs/gcd.vg"} <= names
    assert not {n for n in names if n.startswith("stepone/0/inputs")}
    assert not {n for n in names if n.startswith("steptwo")}
    assert run._upstream()[1] == []                  # nothing to continue from


def test_linked_outputs_are_sent_as_links_and_each_file_once(run, nop_project, tmp_path):
    '''🔴 Links stay links, and a file is stored once (contract.md, *An upload
    keeps links*): a hard link is a tar hard link to the first, a symlink to a
    file the archive holds is a link to it, and a link to nothing is left
    out.'''
    import tarfile

    _leftovers(nop_project)
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    os.link(os.path.join(outputs, "gcd.vg"), os.path.join(outputs, "hard.vg"))
    os.symlink("gcd.vg", os.path.join(outputs, "soft.vg"))
    os.symlink("nothing-there", os.path.join(outputs, "dangling.vg"))
    nop_project.option.add_from("steptwo")

    upload = tmp_path / "upload.tar.gz"
    run._pack(upload)

    with tarfile.open(upload) as tar:
        members = {member.name: member for member in tar.getmembers()}
        first = members["stepone/0/outputs/gcd.vg"]
        assert first.isfile() and tar.extractfile(first).read() == b"module gcd; endmodule\n"
        hard = members["stepone/0/outputs/hard.vg"]
        assert hard.islnk() and hard.linkname == "stepone/0/outputs/gcd.vg"
        soft = members["stepone/0/outputs/soft.vg"]
        assert soft.issym() and soft.linkname == "gcd.vg"
    assert "stepone/0/outputs/dangling.vg" not in members


def test_a_node_whose_outputs_never_came_back_is_continued_from_its_job(
        run, nop_project, tmp_path):
    '''Only its manifest is here: the job this client recorded fetching it
    from is named, and nothing of the node is packed.'''
    _leftovers(nop_project)
    _upstream_node(nop_project, "stepone", fetched_from="01a0e000-0000-7000-8000-000000000001")
    nop_project.option.add_from("steptwo")

    names = _packed(run, tmp_path)

    assert run._upstream()[1] == [{"step": "stepone", "index": "0",
                                   "job_id": "01a0e000-0000-7000-8000-000000000001"}]
    assert not {n for n in names if n.startswith("stepone")}


def test_a_manifests_own_remoteid_is_never_the_job_continued_from(
        run, nop_project, tmp_path):
    '''🔴 The server wrote the manifest, and an upload can name anything in
    it: a node whose job was never recorded here has no job id.'''
    _leftovers(nop_project)
    _upstream_node(nop_project, "stepone", remoteid="01a0e000-0000-7000-8000-00000000beef")
    nop_project.option.add_from("steptwo")

    with pytest.raises(RemoteError, match="stepone/0"):
        _packed(run, tmp_path)


def test_a_node_with_neither_is_refused_before_anything_moves(run, nop_project, tmp_path):
    '''A node from a local run has no job id, so its results must be here.'''
    _leftovers(nop_project)
    _upstream_node(nop_project, "stepone")
    nop_project.option.add_from("steptwo")

    with pytest.raises(RemoteError, match="stepone/0"):
        _packed(run, tmp_path)


###########################
# The server's own page for an error
###########################

def test_a_refusal_prints_the_page_the_server_names(fake_v1, logged_in):
    '''Where the server serves its own copy of the `type` pages it says so,
    and that copy -- on the server this client called -- is what is printed.'''
    fake_v1.route(responses.GET, "jobs/01J9-job",
                  problem("not-found", 404), status=404,
                  content_type="application/problem+json",
                  headers={"Link": '</server-errors/not-found>; rel="help"'})

    with pytest.raises(RemoteError) as raised:
        logged_in.job("01J9-job")

    message = str(raised.value)
    assert "https://sc-server.test/server-errors/not-found" in message
    assert "siliconcompiler.com/server-errors" not in message
    # And remembered, so a job's own error can point there later.
    assert logged_in.transport.help_pages == "https://sc-server.test/server-errors/"


def test_without_one_the_public_type_is_printed(fake_v1, logged_in):
    fake_v1.route(responses.GET, "jobs/01J9-job",
                  problem("not-found", 404), status=404,
                  content_type="application/problem+json")

    with pytest.raises(RemoteError) as raised:
        logged_in.job("01J9-job")

    assert "https://siliconcompiler.com/server-errors/not-found" in str(raised.value)


def test_a_failed_jobs_reason_points_at_the_servers_page():
    from siliconcompiler.remote.client.run import _why_it_failed

    job = {"state": "failed", "progress": {"failed_count": 1},
           "error": {"type": "https://siliconcompiler.com/server-errors/run-failed",
                     "title": "The run failed", "detail": "place/0 exited 1"}}

    said = _why_it_failed(job, "https://sc-server.test/server-errors/")

    assert "https://sc-server.test/server-errors/run-failed" in said


###########################
# What the server cannot supply, it asks for (D114, D124)
###########################

def _routes_for_a_submit(fake_v1, created=None):
    fake_v1.route(responses.POST, "jobs", dict(
        {"id": "01J9-job", "state": "created", "project": None,
         "created_at": "2026-09-22T10:00:00.000Z"}, **(created or {})), status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"),
                  status=202)


def test_the_grant_asks_for_the_archives_size(fake_v1, run):
    '''🔴 D125: the size is the grant's, and it is the archive's own.'''
    _routes_for_a_submit(fake_v1)

    run._start()

    grant = next(c for c in fake_v1.calls if "upload-grant" in c.request.path_url)
    put = next(c for c in fake_v1.calls if c.request.path_url == "/put")
    body = json.loads(grant.request.body)
    sent = put.request.body.read() if hasattr(put.request.body, "read") \
        else put.request.body
    assert body["size_bytes"] == len(sent)
    assert body["digest"] == f"sha256:{hashlib.sha256(sent).hexdigest()}"
    assert set(body) == {"size_bytes", "digest"}


def test_what_goes_up_is_said_per_dataroot_with_sizes(fake_v1, run, caplog):
    _routes_for_a_submit(fake_v1)

    with caplog.at_level("INFO"):
        run._start()

    assert "Uploading" in caplog.text
    assert "design gcd (gcd-pytest-example):" in caplog.text


def test_a_source_the_server_asked_for_at_create_goes_up_with_the_job(
        fake_v1, run, nop_project, tmp_path, caplog):
    '''The server answered create with what it cannot supply; this machine
    resolves it with its own credentials and puts it in the archive.'''
    from siliconcompiler import PDK

    (tmp_path / "ip").mkdir()
    (tmp_path / "ip" / "notes.txt").write_text("private repo contents\n")
    pdk = PDK("acme")
    # Remote, so it would not go up on its own; the server asks for it.
    pdk.set_dataroot("acme", "https://gitlab.example/acme/pdk/archive/", tag="v1")
    with pdk.active_dataroot("acme"):
        pdk.set("package", "doc", "datasheet", "notes.txt")
    nop_project.add_dep(pdk)

    from siliconcompiler.package.https import HTTPResolver
    real = HTTPResolver.resolve_remote

    def resolve_remote(self):
        # "With the user's own credentials": here, a copy only this machine has.
        import shutil
        shutil.copytree(tmp_path / "ip", self.cache_path, dirs_exist_ok=True)

    HTTPResolver.resolve_remote = resolve_remote
    try:
        _routes_for_a_submit(fake_v1, created={"upload_sources": [
            {"kind": "dataroot", "keypath": ["library", "acme", "dataroot", "acme"]}]})
        with caplog.at_level("INFO"):
            run._start()
    finally:
        HTTPResolver.resolve_remote = real

    assert "The server asked for the dataroot library,acme,dataroot,acme" in caplog.text
    assert "pdk acme (acme):" in caplog.text


def test_a_source_this_machine_cannot_reach_either_fails_before_upload(
        fake_v1, run, nop_project, caplog):
    '''🔴 Fail locally, naming it -- upload nothing, and cancel the job with a
    reason saying which and why (surface D287).'''
    from siliconcompiler import PDK

    pdk = PDK("acme")
    # Its own ref: the path cache is process-wide, keyed by source and ref.
    pdk.set_dataroot("acme", "https://gitlab.example/acme/pdk/archive/", tag="v9-unreachable")
    with pdk.active_dataroot("acme"):
        pdk.set("package", "doc", "datasheet", "notes.txt")
    nop_project.add_dep(pdk)

    from siliconcompiler.package.https import HTTPResolver
    real = HTTPResolver.resolve_remote

    def unreachable(self):
        raise FileNotFoundError("404 from gitlab.example")

    HTTPResolver.resolve_remote = unreachable
    try:
        _routes_for_a_submit(fake_v1, created={"upload_sources": [
            {"kind": "dataroot", "keypath": ["library", "acme", "dataroot", "acme"]}]})
        fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                      job_body("cancelled"), status=202)
        with pytest.raises(RemoteError, match="the dataroot library,acme,dataroot,acme: it "
                                              "cannot be fetched here either: 404 from "
                                              "gitlab.example"):
            run._start()
    finally:
        HTTPResolver.resolve_remote = real

    assert not [c for c in fake_v1.calls if "upload-grant" in c.request.path_url]
    cancel, = [c for c in fake_v1.calls if c.request.path_url.endswith("/cancel")]
    assert ("library,acme,dataroot,acme: it cannot be fetched here either: 404 from "
            "gitlab.example") in json.loads(cancel.request.body)["reason"]


def test_a_job_sent_back_is_answered_with_only_what_was_asked(fake_v1, run,
                                                              nop_project, tmp_path):
    '''A follow-up archive of the asked-for dataroots alone, its own grant, and
    submit again.'''
    import io
    import tarfile

    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"),
                  status=202)

    run._send_asked("01J9-job", [{"kind": "dataroot", "keypath": [
        "library", "gcd", "dataroot", "gcd-pytest-example"]}])

    put = next(c for c in fake_v1.calls if c.request.path_url == "/put")
    body = put.request.body.read() if hasattr(put.request.body, "read") else put.request.body
    with tarfile.open(fileobj=io.BytesIO(body)) as tar:
        names = tar.getnames()
    assert names and all(name.startswith("sc_collected_files") for name in names)
    assert any(name.endswith(".v") for name in names)
    assert not any(name.endswith(".pkg.json") for name in names)


def test_asked_again_for_what_was_sent_is_a_failure_not_a_loop(fake_v1, run):
    run._sent.add((("dataroot", "library,gcd,dataroot,gcd-pytest-example", ""),))

    with pytest.raises(RemoteError, match="asked again"):
        run._send_asked("01J9-job", [{"kind": "dataroot", "keypath": [
            "library", "gcd", "dataroot", "gcd-pytest-example"]}])


def test_leaving_a_job_not_yet_queued_warns_once(run, monkeypatch, caplog):
    '''🔴 Surface D166: the server may still ask this machine for a source, and
    with nobody to send it the job waits until it is abandoned. A second
    interrupt leaves.'''
    import logging

    polls = []

    def poll(job_id):
        polls.append(job_id)
        run._last_state = "staging"
        raise KeyboardInterrupt

    monkeypatch.setattr(run, "_poll", poll)
    run.logger.propagate = True

    with caplog.at_level(logging.WARNING), pytest.raises(KeyboardInterrupt):
        run._watch("01J9-job")

    assert len(polls) == 2
    assert "not fully submitted" in caplog.text and "Ctrl-C again" in caplog.text


def test_leaving_a_queued_job_does_not_ask_twice(run, monkeypatch):
    polls = []

    def poll(job_id):
        polls.append(job_id)
        run._last_state = "queued"
        raise KeyboardInterrupt

    monkeypatch.setattr(run, "_poll", poll)

    with pytest.raises(KeyboardInterrupt):
        run._watch("01J9-job")

    assert len(polls) == 1


###########################
# Create before pack, 202 in staging, and what will not be submitted
###########################

def _created(fake_v1, **extra):
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z", **extra}, status=201)


def _granted(fake_v1):
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")


@pytest.mark.parametrize("refusal,said", [
    # A private task root this server does not hold (surface D298): the
    # owner's name, and which of its dataroots.
    (problem("resource-unavailable", 422, resource="acme_sim",
             keypath=["tool", "acme_sim", "task", "run", "dataroot", "scripts"],
             detail="the private dataroot tool,acme_sim,task,run,dataroot,scripts is not "
                    "held by this server"),
     ["keypath: tool,acme_sim,task,run,dataroot,scripts",
      "the private dataroot tool,acme_sim,task,run,dataroot,scripts is not held by this "
      "server"]),
    # A keypath of any other shape, from a client this one is not.
    (problem("invalid-request", 400,
             detail="a source's keypath is a library's dataroot, [\"library\", name, "
                    "\"dataroot\", root], or a task's"),
     ["a source's keypath is a library's dataroot"]),
])
def test_a_refused_dataroot_is_said_by_its_keypath(fake_v1, run, monkeypatch, refusal, said):
    monkeypatch.setattr(RemoteRun, "_pack", lambda self, upload: pytest.fail("packed"))
    fake_v1.route(responses.POST, "jobs", refusal, status=refusal["status"],
                  content_type="application/problem+json")

    with pytest.raises(RemoteError) as raised:
        run._start()

    assert all(line in str(raised.value) for line in said), str(raised.value)
    assert not any("upload-grant" in call.request.url for call in fake_v1.calls)


def test_a_refusal_at_create_packs_nothing(fake_v1, run, monkeypatch):
    '''🔴 Created before anything is packed: a refusal there costs nothing.'''
    packed = []
    monkeypatch.setattr(RemoteRun, "_pack", lambda self, upload: packed.append(upload))
    fake_v1.route(responses.POST, "jobs",
                  problem("software-unavailable", 422, reason="unavailable", unresolved=[]),
                  status=422, content_type="application/problem+json")

    with pytest.raises(RemoteError):
        run._start()

    assert not packed
    assert not any("upload-grant" in call.request.url for call in fake_v1.calls)


def test_a_202_then_a_rejected_job_reads_the_refusal_from_the_poll(
        fake_v1, run, monkeypatch, caplog):
    '''Submit only matched the digest; what staging found arrives on the job.'''
    monkeypatch.setattr("time.sleep", lambda *_: None)
    _created(fake_v1)
    _granted(fake_v1)
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging", nodes=[]),
                  status=202)
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "rejected", nodes=[], error={
            "type": "https://siliconcompiler.com/server-errors/archive-rejected",
            "title": "Archive rejected", "status": 422, "reason": "unrequested_member",
            "detail": "stray.txt is not something a first archive carries"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with pytest.raises(RemoteError, match="rejected"):
        run.run()

    assert "stray.txt" in caplog.text


def test_a_manifest_refused_for_a_credential_says_what_to_do(
        fake_v1, run, monkeypatch, caplog):
    '''The conformance rig serves the refusal `sc-server` raises for a
    manifest carrying userinfo: the keypath, and never a value, and the next
    step for a client bug.'''
    monkeypatch.setattr("time.sleep", lambda *_: None)
    _created(fake_v1)
    _granted(fake_v1)
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging", nodes=[]),
                  status=202)
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "rejected", nodes=[], error={
            "type": "https://siliconcompiler.com/server-errors/archive-rejected",
            "title": "Archive rejected", "status": 422, "reason": "credential",
            "detail": "the manifest carries userinfo in the path of 1 dataroot(s): "
                      "library,gcd,dataroot,ip"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with pytest.raises(RemoteError, match="rejected"):
        run.run()

    assert "library,gcd,dataroot,ip" in caplog.text
    assert "reason: credential" in caplog.text
    assert "through the environment" in caplog.text


def test_in_progress_and_a_slot_limit_are_waited_out_with_the_same_key(
        fake_v1, run, monkeypatch, caplog):
    slept = []
    monkeypatch.setattr("time.sleep", slept.append)
    fake_v1.route(responses.POST, "jobs",
                  problem("job-state-conflict", 409, reason="in_progress"), status=409,
                  content_type="application/problem+json", headers={"Retry-After": "2"})
    fake_v1.route(responses.POST, "jobs",
                  problem("limit-exceeded", 429, limit="pending_uploads",
                          job_ids=["01J9-old"]),
                  status=429, content_type="application/problem+json",
                  headers={"Retry-After": "3"})
    _created(fake_v1)
    _granted(fake_v1)
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("staging"), status=202)

    with caplog.at_level("WARNING"):
        run._start()

    creates = [call.request for call in fake_v1.calls
               if call.request.method == "POST" and call.request.path_url == "/v1/jobs"]
    assert len(creates) == 3
    assert len({request.headers["Idempotency-Key"] for request in creates}) == 1
    assert 2.0 in slept and 3.0 in slept
    assert "01J9-old" in caplog.text


def test_a_failed_upload_cancels_the_job(fake_v1, run):
    '''It will not be submitted, so it must not hold a slot until abandoned.'''
    _created(fake_v1)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {}, "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "denied", status=403,
                      content_type="text/plain")
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel", job_body("cancelled"),
                  status=202)

    with pytest.raises(RemoteError):
        run._start()

    cancel = [call.request for call in fake_v1.calls if call.request.url.endswith("/cancel")]
    assert len(cancel) == 1
    assert json.loads(cancel[0].body)["reason"].startswith("cancelled from sc-remote")
    assert not run.project.get('record', 'remoteid')


def test_an_interrupt_before_submit_cancels_the_job(fake_v1, run, monkeypatch):
    _created(fake_v1)
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel", job_body("cancelled"),
                  status=202)

    def interrupted(self, upload):
        raise KeyboardInterrupt

    monkeypatch.setattr(RemoteRun, "_pack", interrupted)

    with pytest.raises(KeyboardInterrupt):
        run._start()

    cancel = [call.request for call in fake_v1.calls if call.request.url.endswith("/cancel")]
    assert "interrupted" in json.loads(cancel[0].body)["reason"]


def test_an_asic_project_with_no_pdk_stops_before_create(fake_v1, logged_in, gcd_design):
    from siliconcompiler import ASIC

    project = ASIC(gcd_design)
    project.add_fileset("rtl")

    with pytest.raises(RemoteError, match="sets no PDK"):
        RemoteRun(project, logged_in)._preflight()

    assert not any(call.request.path_url == "/v1/jobs" for call in fake_v1.calls)


def test_a_task_class_no_package_provides_stops_before_create(
        fake_v1, run, nop_project, monkeypatch):
    monkeypatch.setattr("importlib.metadata.packages_distributions", lambda: {})

    with pytest.raises(RemoteError, match="installed package"):
        run._preflight()


###########################
# Links in what goes up (contract.md, *An upload keeps links*; client-v1-migration D4)
###########################

def _three_nodes(project, both=False):
    '''stepone -> steptwo -> stepthree, run from stepthree: it reads steptwo,
    and -- with ``both`` -- stepone too.'''
    from siliconcompiler import Flowgraph
    from siliconcompiler.tools.builtin.nop import NOPTask

    flow = Flowgraph("passflow")
    for step in ("stepone", "steptwo", "stepthree"):
        flow.node(step, NOPTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    if both:
        flow.edge("stepone", "stepthree")
    project.set_flow(flow)
    project.option.add_from("stepthree")
    return project


def _passed_through(project, hard=True):
    '''steptwo passed stepone's output through, as `link_symlink_copy`
    leaves it: `outputs/x` -> `inputs/x`, the input a hard link (or a
    symlink) to the upstream file.'''
    from siliconcompiler.utils.paths import workdir

    upstream = _upstream_node(project, "stepone", output="gcd.vg")
    two = workdir(project, step="steptwo", index="0")
    _upstream_node(project, "steptwo")
    os.makedirs(os.path.join(two, "inputs"), exist_ok=True)
    if hard:
        os.link(os.path.join(upstream, "gcd.vg"), os.path.join(two, "inputs", "gcd.vg"))
    else:
        os.symlink(os.path.join(upstream, "gcd.vg"), os.path.join(two, "inputs", "gcd.vg"))
    os.symlink("../inputs/gcd.vg", os.path.join(two, "outputs", "gcd.vg"))
    return two


def _members(run, tmp_path):
    import tarfile

    upload = tmp_path / "upload.tar.gz"
    run._pack(upload)
    with tarfile.open(upload) as tar:
        return {member.name: member for member in tar.getmembers()}, \
            {member.name: tar.extractfile(member).read() for member in tar.getmembers()
             if member.isfile()}


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
    '''stepone is not in the archive: the file is stored at its first
    appearance, and a later link to it points at that copy.'''
    _three_nodes(nop_project)
    two = _passed_through(nop_project, hard=False)
    os.symlink("../../../stepone/0/outputs/gcd.vg", os.path.join(two, "outputs", "again.vg"))

    members, contents = _members(run, tmp_path)

    assert not any(name.startswith("stepone") for name in members)
    again, first = members["steptwo/0/outputs/again.vg"], "steptwo/0/outputs/gcd.vg"
    # Sorted: `again.vg` comes first, so it holds the bytes.
    assert again.isfile() and contents["steptwo/0/outputs/again.vg"] == \
        b"module gcd; endmodule\n"
    assert members[first].issym() and members[first].linkname == "again.vg"


def test_a_link_out_of_the_build_directory_is_left_out_and_named(
        run, nop_project, tmp_path, caplog):
    '''To a file or a directory: never followed, never sent.'''
    import logging

    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "secret.lib").write_text("the foundry's own\n")
    outputs = _upstream_node(nop_project, "stepone", output="gcd.vg")
    os.symlink(str(outside / "secret.lib"), os.path.join(outputs, "lib"))
    os.symlink(str(outside), os.path.join(outputs, "libs"))
    nop_project.option.add_from("steptwo")
    caplog.set_level(logging.WARNING)

    members, _ = _members(run, tmp_path)

    assert "stepone/0/outputs/lib" not in members
    assert not any(name.startswith("stepone/0/outputs/libs") for name in members)
    assert "stepone/0/outputs/lib is a link out of the build directory" in caplog.text


def test_a_dangling_upstream_link_stops_the_run_before_create(run, nop_project):
    '''A link to a node this machine never fetched is a missing file.'''
    _three_nodes(nop_project)
    from siliconcompiler.utils.paths import workdir

    two = workdir(nop_project, step="steptwo", index="0")
    _upstream_node(nop_project, "steptwo", output="own.vg")
    os.symlink("../../../stepone/0/outputs/gcd.vg", os.path.join(two, "outputs", "gcd.vg"))

    with pytest.raises(RemoteError, match="steptwo/0/outputs/gcd.vg is a link to"):
        run._check_upstream_files()


###########################
# The v1 API changes of 2026-09-29, the client's half
###########################

def test_an_asked_dataroot_is_matched_on_its_owner_and_its_name(run, nop_project, tmp_path):
    '''🔴 Never the dataroot's name alone: many objects use SiliconCompiler's
    default, `root` (surface D282). Asked for one owner's, the other's stays.'''
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
    '''How long the job has been in its state, from the last entry of
    `transitions`, and why it entered it (surface §17; D278).'''
    import time
    from datetime import datetime, timezone

    from siliconcompiler.remote.client.run import _state_line

    entered = datetime.fromtimestamp(time.time() - 300, tz=timezone.utc) \
        .strftime("%Y-%m-%dT%H:%M:%S.000Z")
    line = _state_line({"state": "cancelling", "transitions": [
        {"state": "created", "at": "2026-09-29T10:00:00.000Z"},
        {"state": "cancelling", "at": entered, "reason": "wrong corner"}]})

    assert line.startswith("cancelling for 5m") and line.endswith(", wrong corner")
    # A live staging phase is the job's own, and wins.
    assert _state_line({"state": "staging", "state_reason": "fetching sources",
                        "transitions": [{"state": "staging", "at": entered}]}) \
        .endswith(", fetching sources")


def test_the_session_is_shown_from_me_and_nothing_is_refreshed(logged_in, fake_v1, caplog):
    '''`sc-remote` shows the session this machine holds -- from `GET /v1/me`,
    which rotates nothing -- and what it has used, this month and in all.'''
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

    assert "Session: ci\n" in caplog.text or caplog.text.count("Session: ci") == 1
    assert "on device" not in caplog.text
    assert "it cannot refresh" in caplog.text
