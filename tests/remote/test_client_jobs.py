import json

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
         "error_type": None},
        {"step": "steptwo", "index": "0", "state": "pending", "terminal": False,
         "started_at": None, "finished_at": None, "exit_code": None,
         "error_type": None},
    ]
    if terminal is None:
        terminal = state in ("completed", "failed", "cancelled", "rejected",
                             "abandoned")
    return {
        "id": "01J9-job", "state": state, "terminal": terminal,
        "state_changed_at": "2026-09-22T10:00:00.000Z",
        "design": "gcd", "jobname": "job0", "flow": "nopflow",
        "owner": "01J9-user", "project": None,
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
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("queued"),
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
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("queued"),
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
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("queued"),
                  status=202)

    run._start()

    posts = {call.request.path_url: call.request
             for call in fake_v1.calls if call.request.method == "POST"}
    assert posts["/v1/jobs"].headers["Idempotency-Key"]
    assert posts["/v1/jobs/01J9-job/submit"].headers["Idempotency-Key"]
    # Two windows, not one: a retry of the create is not a retry of the submit.
    assert posts["/v1/jobs"].headers["Idempotency-Key"] != \
        posts["/v1/jobs/01J9-job/submit"].headers["Idempotency-Key"]


def test_the_descriptor_declares_the_size_before_the_upload(fake_v1, run):
    '''The one descriptor field where sending it costs nothing and omitting it
    costs the whole upload.'''
    fake_v1.route(responses.POST, "jobs",
                  {"id": "01J9-job", "state": "created", "project": None,
                   "created_at": "2026-09-22T10:00:00.000Z"}, status=201)
    fake_v1.route(responses.POST, "jobs/01J9-job/upload-grant",
                  {"method": "PUT", "url": "https://storage.test/put",
                   "headers": {"content-length": "1"},
                   "expires_at": "2026-09-22T10:15:00.000Z"})
    fake_v1.elsewhere(responses.PUT, "https://storage.test/put", "")
    fake_v1.route(responses.POST, "jobs/01J9-job/submit", job_body("queued"),
                  status=202)

    run._start()

    created = [call for call in fake_v1.calls
               if call.request.path_url == "/v1/jobs"][0]
    body = json.loads(created.request.body)
    assert body["resources"]["upload_bytes"] > 0
    assert body["versions"]["siliconcompiler"]
    assert body["flow"]["nodes"] == 2
    # Nothing computes a run hash yet, so nothing claims one.
    assert "run_hash" not in body


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
                "exit_code": 0, "error_type": None},
               {"step": "steptwo", "index": "0", "state": "skipped",
                "terminal": True, "started_at": None, "finished_at": None,
                "exit_code": None, "error_type": None}]))

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

def test_listing_follows_the_link_header(fake_v1, logged_in):
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("completed")]},
                  headers={"Link": '</v1/jobs?limit=1&cursor=abc>; rel="next"'})
    fake_v1.route(responses.GET, "jobs", {"items": [job_body("failed")]})

    assert len(logged_in.jobs()) == 2


def test_a_cancel_with_nothing_to_add_says_who_asked(fake_v1, logged_in):
    """🔴 `reason` is optional on the wire -- requiring it would make a Ctrl-C
    inexpressible -- and this client always sends one anyway. A job page that
    says only "cancelled" cannot answer the owner's own question, which is
    which of their machines did it."""
    import socket

    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  job_body("cancelling"), status=202)

    logged_in.cancel_job("01J9-job")

    body = json.loads(fake_v1.calls[-1].request.body)
    assert "sc-remote" in body["reason"]
    assert socket.gethostname() in body["reason"]


def test_a_cancel_with_a_reason_sends_that_one(fake_v1, logged_in):
    """The caller's own words win: what this client can say for itself is a
    fallback, not a prefix."""
    fake_v1.route(responses.POST, "jobs/01J9-job/cancel",
                  job_body("cancelling"), status=202)

    logged_in.cancel_job("01J9-job", reason="wrong constraints")

    assert json.loads(fake_v1.calls[-1].request.body) == {
        "reason": "wrong constraints"}


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
     ["limit: max_upload_bytes", "Reduce what is collected"]),
    ("feature-unsupported", 501, {"feature": "projects"},
     ["feature: projects", "never will"]),
    ("version-skew", 422, {},
     ["Install a version this server accepts"]),
    ("entitlement-denied", 403, {"resource_kind": "pdk", "resource": "gf12"},
     ["resource: gf12", "resource_kind: pdk", "Ask an operator"]),
    ("terms-not-accepted", 403, {"terms_scope": "service",
                                 "decision_url": "https://example.test/terms"},
     ["terms_scope: service", "Accept the agreement"]),
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
                  problem("archive-rejected", 422, violation="link_member"),
                  status=422, content_type="application/problem+json")

    with pytest.raises(ServerProblem) as raised:
        logged_in.submit_job("01J9-job", "sha256:" + "0" * 64, 10)

    assert "violation: link_member" in str(raised.value)


###########################
# A failed run says why, without opening a URL
###########################

def _node(step, state, **extra):
    node = {"step": step, "index": "0", "state": state,
            "terminal": state in ("completed", "failed", "skipped", "cancelled"),
            "started_at": None, "finished_at": None, "exit_code": None,
            "error_type": None}
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


def test_a_lost_run_is_told_apart_from_a_failed_one(fake_v1, run, caplog):
    '''The hash did not determine it and re-running would succeed: different
    words, and a different next step.'''
    fake_v1.route(responses.GET, "jobs/01J9-job", job_body(
        "failed",
        error={"type": "https://siliconcompiler.com/server-errors/scheduler-lost",
               "title": "The scheduler lost this job"}))
    fake_v1.route(responses.GET, "jobs/01J9-job/artifacts", {"items": []})

    with caplog.at_level("INFO"):
        with pytest.raises(RemoteError):
            run._poll("01J9-job")

    assert "submit it again" in caplog.text


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


def test_a_server_with_no_live_tail_simply_does_not_tail(fake_v1, run,
                                                         capabilities):
    '''Point 2: if the logs cannot be streamed, what we already print is fine.
    The archived log still arrives with the results.'''
    from siliconcompiler.remote.client.run import _Tails

    run.project.option.set_quiet(False)
    fake_v1.replace(responses.GET, "", dict(capabilities, features=["logs"]))

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
