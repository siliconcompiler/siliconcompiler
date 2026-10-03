import contextlib
import threading
import time

import pytest


from conftest import call, slug


pytest.importorskip("flask", reason="the server extra is not installed")


# Phase 5's gate: tail a running node, drop the connection, resume without a
# gap -- exact, since the event id IS the byte offset reached.


def make_job(app, user, steps=("place",)):
    '''A running job of ``user``'s, each of ``steps`` running at index 0 with
    an empty log. Returns the job id and each step's log path.'''
    import uuid

    store = app.config["SC_STORE"]
    job_id = str(uuid.uuid4())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
        (job_id, user))
    row = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    logs = {}
    for step in steps:
        store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                      "VALUES (?, ?, '0', 'running')", (job_id, step))
        logs[step] = app.config["SC_JOBS"].node_log_path(row, step, "0")
        logs[step].parent.mkdir(parents=True, exist_ok=True)
        logs[step].write_text("")
    return job_id, logs


@contextlib.contextmanager
def live_server(tmp_path, steps=("place",)):
    '''A server on a real port and a client of it, with `make_job`'s job.
    Yields the client, the app, the job id and its logs by step.'''
    from werkzeug.serving import make_server

    from siliconcompiler.remote import Client, Credentials
    from siliconcompiler.remote.server.app import create_app

    app = create_app(tmp_path / "datadir", cluster="local")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    app.config["SC_PUBLIC_ORIGINS"] = [f"http://127.0.0.1:{server.server_port}"]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    credentials = Credentials(tmp_path / "sc-home" / "auth" / "remote.json")
    credentials.set_server(f"http://127.0.0.1:{server.server_port}")
    client = Client(credentials)

    try:
        yield (client, app, *make_job(app, client.me()["id"], steps))
    finally:
        server.shutdown()
        thread.join(timeout=10)


@pytest.fixture
def running(server, server_client, key, token):
    '''A job with one running node and a log being written under it.'''
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    job_id, logs = make_job(server, me)
    return job_id, logs["place"]


def finish(server, job_id):
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))


def frames(response, limit=None):
    '''Parse an SSE body into (event, id, data) triples.'''
    import json

    out = []
    event, identifier, payload = "message", None, []

    for raw in response.get_data(as_text=True).splitlines():
        if not raw:
            if payload:
                out.append((event, identifier, json.loads("\n".join(payload))))
                if limit and len(out) >= limit:
                    return out
            event, identifier, payload = "message", None, []
            continue
        if raw.startswith(":"):
            continue
        name, _, value = raw.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if name == "event":
            event = value
        elif name == "id":
            identifier = value
        elif name == "data":
            payload.append(value)
    return out


def logged(parsed):
    '''The text of every `log` event.'''
    return "".join(data["text"] for event, _, data in parsed if event == "log")


def stream_url(server_client, key, token, job_id, step="place", index="0", headers=None):
    '''The stream path `/logs` redirects to; ``step=None`` is the whole job.'''
    query = "" if step is None else f"?step={step}&index={index}"
    response = call(server_client, key, "GET", f"/v1/jobs/{job_id}/logs{query}", token,
                    headers=headers or {})
    assert response.status_code == 303, response.get_json()
    return response.headers["Location"].split("http://localhost", 1)[1]


def test_a_stream_url_is_its_own_grant_for_one_connection(server, server_client, key,
                                                          token, running):
    '''Unsigned, or signed as a download, is refused. It lasts no longer
    than the access token that obtained it, and serves one connection.'''
    import jwt

    job_id, _ = running
    expires = int(time.time()) + 300
    wrong = server.config["SC_STORAGE"].sign_download(job_id, expires)
    assert server_client.get(f"/stream/logs/{job_id}/place/0").status_code == 400
    assert server_client.get(
        f"/stream/logs/{job_id}/place/0?expires={expires}&sig={wrong}").status_code == 400

    target = stream_url(server_client, key, token, job_id)
    expires = int(target.split("expires=")[1].split("&")[0])
    assert expires <= jwt.decode(token, options={"verify_signature": False})["exp"]

    finish(server, job_id)
    assert server_client.get(target).status_code == 200
    assert server_client.get(target).status_code == 400


def test_a_running_node_is_a_stream_read_to_its_end_naming_the_archive(
        server, server_client, key, token, running):
    '''Only the content type says it is a stream (it can finish before the
    fetch); ids only on `log` events; `end` names the archive just indexed.'''
    job_id, log = running
    log.write_text("one\ntwo\nthree\n")

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job_id}/logs?step=place&index=0", token)
    assert response.headers["Location"].startswith("http://localhost/")
    finish(server, job_id)
    streamed = server_client.get(response.headers["Location"].split("http://localhost", 1)[1])
    parsed = frames(streamed)

    assert streamed.headers["Content-Type"].startswith("text/event-stream")
    assert streamed.headers["Cache-Control"] == "no-store"
    # Owed by whatever fronts the stream host: a buffered SSE response is not one.
    assert streamed.headers["X-Accel-Buffering"] == "no"
    assert logged(parsed) == "one\ntwo\nthree\n"
    assert [event for event, _, _ in parsed][-2:] == ["node_state", "end"]
    assert parsed[-1][2]["reason"] == "terminal"
    assert all(i is not None for e, i, _ in parsed if e == "log")
    assert all(i is None for e, i, _ in parsed if e != "log")

    artifact_id = parsed[-1][2].get("artifact_id")
    assert artifact_id
    assert call(server_client, key, "GET", f"/v1/jobs/{job_id}/artifacts/{artifact_id}",
                token).status_code == 303


def test_resuming_from_the_last_id_has_no_gap_and_no_repeat(
        server, server_client, key, token, running):
    '''The id is the byte offset: no server state about the caller.'''
    job_id, log = running
    log.write_text("one\ntwo\n")

    target = stream_url(server_client, key, token, job_id)
    second_target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    first = frames(server_client.get(target))
    last_id = [i for e, i, _ in first if e == "log" and i][-1]

    with open(log, "a") as f:
        f.write("three\nfour\n")

    rest = logged(frames(server_client.get(second_target,
                                           headers={"Last-Event-ID": last_id})))

    assert logged(first) + rest == log.read_text()
    assert "one" not in rest


@pytest.mark.parametrize("to_logs,last_id", [
    # The header belongs on the stream; sent to `/logs` it changes nothing.
    (True, "4"),
    (False, "not-a-number"),
    (False, format(10_000, "x")),
], ids=["sent-to-logs", "unreadable", "past-a-log-that-shrank"])
def test_a_last_event_id_that_does_not_apply_replays_from_the_start(
        server, server_client, key, token, running, to_logs, last_id):
    '''Replaying is a nuisance; skipping, or seeking past the end, loses a log.'''
    job_id, log = running
    log.write_text("one\ntwo\n")
    header = {"Last-Event-ID": last_id}
    target = stream_url(server_client, key, token, job_id, headers=header if to_logs else None)
    finish(server, job_id)
    assert logged(frames(server_client.get(
        target, headers=None if to_logs else header))) == "one\ntwo\n"


def test_a_node_that_finishes_mid_stream_is_followed_to_its_end(
        server, server_client, key, token, running):
    '''Live: not only the bytes that existed when it started.'''
    job_id, log = running
    log.write_text("first\n")

    def later():
        time.sleep(0.6)
        with open(log, "a") as f:
            f.write("second\n")
        time.sleep(0.4)
        finish(server, job_id)

    thread = threading.Thread(target=later)
    thread.start()
    try:
        parsed = frames(server_client.get(stream_url(server_client, key, token, job_id)))
    finally:
        thread.join()

    assert logged(parsed) == "first\nsecond\n"


def test_the_published_stream_limit_is_enforced_per_caller_and_given_back(
        server, server_client, key, token, running):
    '''A published number nothing enforces is a promise. A finished stream
    releases its slot in a finally: a hang-up arrives as GeneratorExit.'''
    job_id, log = running
    log.write_text("one\n")
    limiter = server.config["SC_STREAMS"]
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    ceiling = server.config["SC_CONFIG"].limits["concurrent_log_streams"]

    for _ in range(ceiling):
        assert limiter.acquire(me)
    response = server_client.get(stream_url(server_client, key, token, job_id))

    assert response.status_code == 429
    assert slug(response) == "limit-exceeded"
    assert response.get_json()["limit"] == "concurrent_log_streams"
    assert response.headers["Retry-After"]
    assert limiter.held("somebody-else") == 0

    for _ in range(ceiling):
        limiter.release(me)
    targets = [stream_url(server_client, key, token, job_id) for _ in range(3)]
    finish(server, job_id)
    for target in targets:
        server_client.get(target)
    assert limiter.held(me) == 0


@pytest.fixture
def live(tmp_path):
    with live_server(tmp_path) as (client, app, job_id, logs):
        yield client, app, job_id, logs["place"]


def write_then_finish(app, job_id, log, lines, pause=0.25):
    '''Append lines over time, then mark the node done.'''
    def run():
        for line in lines:
            time.sleep(pause)
            with open(log, "a") as f:
                f.write(line)
        time.sleep(pause)
        finish(app, job_id)

    thread = threading.Thread(target=run)
    thread.start()
    return thread


def test_a_reader_that_hangs_up_resumes_without_a_gap(live):
    '''Phase 5's gate: the reconnect asks /logs again and hands back the
    last id it saw. The client takes the server's stated reconnect pace.'''
    from siliconcompiler.remote.client.logs import LogTail, _frames

    client, app, job_id, log = live
    writer = write_then_finish(app, job_id, log, [f"line {n}\n" for n in range(1, 9)],
                               pause=0.2)
    tail = LogTail(client, job_id, "place", "0")
    first = []

    try:
        # Two frames, then drop the connection as a closing lid would.
        response = client.follow_log(job_id, "place", "0")
        assert response.headers["Content-Type"].startswith("text/event-stream")
        for event, identifier, data in _frames(response, tail):
            if event == "log":
                first.append(data["text"])
                tail.last_event_id = identifier
                if len(first) >= 2:
                    break
        response.close()
        assert tail.last_event_id
        assert tail.retry == 2

        rest = tail.follow()
    finally:
        writer.join()

    assert "".join(first) + rest == log.read_text()
    assert rest.count("line 1") == 0


def test_a_reader_that_hangs_up_frees_its_slot(live):
    '''A slot outliving its connection locks its owner out for the life of the process.'''
    client, app, job_id, log = live
    limiter = app.config["SC_STREAMS"]
    limiter._ceiling = 1
    me = client.me()["id"]
    log.write_text("first\n")

    response = client.follow_log(job_id, "place", "0")
    assert response.headers["Content-Type"].startswith("text/event-stream")
    # Held: dropping the iterator would close the connection too early.
    lines = response.iter_lines(decode_unicode=True)
    assert next(lines)
    assert limiter.held(me) == 1

    refused = client.follow_log(job_id, "place", "0")
    assert refused.status_code == 429
    refused.close()

    del lines
    response.close()
    # The server learns of the hang-up on its next write.
    deadline = time.monotonic() + 20
    while limiter.held(me) and time.monotonic() < deadline:
        with open(log, "a") as f:
            f.write("more\n")
        time.sleep(0.1)
    assert limiter.held(me) == 0

    second = client.follow_log(job_id, "place", "0")
    try:
        assert second.headers["Content-Type"].startswith("text/event-stream")
    finally:
        second.close()


def test_a_tail_after_the_node_finished_gets_the_archive_and_no_session(live):
    '''A finished node's stream ends at once naming its `logs` artifact.
    No Authorization or DPoP proof reaches the stream target.'''
    client, app, job_id, log = live
    log.write_text("all done\n")
    finish(app, job_id)
    jobs = app.config["SC_JOBS"]
    jobs._index_node(jobs._row(job_id), "place", "0")

    response = client.follow_log(job_id, "place", "0")
    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert "Authorization" not in response.request.headers
    assert "DPoP" not in response.request.headers
    response.close()

    assert client.tail_log(job_id, "place", "0") == "all done\n"


def test_a_skipped_node_is_settled_as_skipped_and_published_at_once(nop_project,
                                                                    monkeypatch):
    '''A skipped node is never launched, so still pending: settled from the
    record (not `cancelled`, an error) and published at once; a verdict stands.'''
    from siliconcompiler.remote.server.running import runner

    published = []
    monkeypatch.setattr(runner, "_publish",
                        lambda: published.append(runner._progress["nodes"]["steptwo/0"]["state"]))
    nop_project.set('record', 'status', 'skipped', step="steptwo", index="0")
    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "failed"},
                                  "steptwo/0": {"state": "pending"}}}

    runner._settle(nop_project)

    assert runner._progress["nodes"]["steptwo/0"]["state"] == "skipped"
    assert runner._progress["nodes"]["stepone/0"]["state"] == "failed"
    assert published == ["skipped"]


def test_a_run_grown_past_its_window_fails_naming_the_node(nop_project):
    '''Where `-from` widens to rebuild an upstream, the run fails before
    any node starts, naming it.'''
    from siliconcompiler.remote.server.running import runner
    nop_project.option.add_from("steptwo")
    runner._progress = {"nodes": {"steptwo/0": {"state": "pending"}}}
    runner._hold_the_window(nop_project)
    nop_project.option.add_from("stepone", clobber=True)
    with pytest.raises(RuntimeError, match="would rebuild stepone/0"):
        runner._hold_the_window(nop_project)


def test_settling_changes_and_writes_nothing_the_record_does_not_say(
        nop_project, monkeypatch):
    '''The common case. A node with no recorded status is left to the sweep
    at the end: `cancelled` if it never started, `failed` if it was running.'''
    from siliconcompiler.remote.server.running import runner

    published = []
    monkeypatch.setattr(runner, "_publish", lambda: published.append(1))
    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "running"},
                                  "steptwo/0": {"state": "pending"}}}
    nop_project.set('record', 'status', 'running', step="stepone", index="0")

    runner._settle(nop_project)
    assert not published
    assert runner._progress["nodes"]["steptwo/0"]["state"] == "pending"

    runner._sweep()
    assert runner._progress["nodes"]["steptwo/0"]["state"] == "cancelled"
    assert runner._progress["nodes"]["stepone/0"]["state"] == "failed"


def test_the_verdict_is_taken_before_the_record_is_reset(nop_project):
    '''Project.run() resets `record,status` on its way out, so settling is a
    post_run callback and not something done after run() returns.'''
    from siliconcompiler.remote.server.running import runner
    from siliconcompiler.scheduler.taskscheduler import TaskScheduler
    from siliconcompiler.utils.multiprocessing import MPManager

    nop_project.option.set_builddir("build")
    runner._progress_path = None
    runner._progress = {"nodes": {"stepone/0": {"state": "pending"},
                                  "steptwo/0": {"state": "pending"}}}

    TaskScheduler.register_callback("post_run", runner._settle)
    nop_project.run()

    assert runner._progress["nodes"]["stepone/0"]["state"] == "completed"
    assert runner._progress["nodes"]["steptwo/0"]["state"] == "completed"
    assert nop_project.get("record", "status", step="stepone", index="0") is None
    MPManager.get_transient_settings().set("TaskScheduler", "post_run",
                                           lambda project: None)


def test_quiet_is_left_as_the_caller_set_it(nop_project, tmp_path):
    '''`quiet` mutes only the console sink; rewriting it handed back a
    manifest that did not describe the caller's run.'''
    from siliconcompiler.remote.server.running import runspec
    for quiet in (False, True):
        nop_project.option.set_quiet(quiet)
        runspec.normalize(nop_project, "job-1", tmp_path / "builds", tmp_path / "cache")
        assert nop_project.option.get_quiet() is quiet


def test_the_runner_silences_the_console_with_a_filter(nop_project):
    '''Not detached: TaskScheduler hands this handler OBJECT to the listener
    that re-emits every node's records. Twice is not an error.'''
    import logging
    from siliconcompiler.remote.server.running import runner
    console = nop_project._logger_console
    runner._silence_console(nop_project)
    runner._silence_console(nop_project)
    assert console in nop_project.logger.handlers
    record = logging.LogRecord("x", logging.INFO, "f", 1, "hello", None, None)
    assert not all(f.filter(record) for f in console.filters)
