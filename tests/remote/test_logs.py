import threading
import time

import pytest


from conftest import call, slug


pytest.importorskip("flask", reason="the server extra is not installed")


# Phase 5's gate: tail a running node, kill the connection mid-run, and resume
# without a gap. The resumption is exact rather than approximate because the
# event id IS the byte offset the reader reached.


@pytest.fixture
def running(server, server_client, key, token):
    '''A job with one running node and a log being written under it.'''
    from siliconcompiler.remote.server.ids import uuid7

    store = server.config["SC_STORE"]
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]

    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
        (job_id, me))
    store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                  "VALUES (?, 'place', '0', 'running')", (job_id,))

    job = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    log = server.config["SC_JOBS"].node_log_path(job, "place", "0")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("")

    return job_id, log


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


def stream_url(server_client, key, token, job_id, step="place", index="0"):
    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job_id}/logs?step={step}&index={index}", token)
    assert response.status_code == 303
    return response.headers["Location"].split("http://localhost", 1)[1]


###########################
# The redirect
###########################

def test_a_running_node_is_a_stream_and_says_so_only_in_its_content_type(
        server, server_client, key, token, running):
    '''🔴 The 303 does not say which it is, deliberately: a node can finish
    between the redirect and the fetch, so anything decided at /logs can be
    stale by the time it is used.'''
    job_id, log = running
    log.write_text("hello\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    response = server_client.get(target)

    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert response.headers["Cache-Control"] == "no-store"
    # Owed by whatever fronts the stream host: a buffered SSE response is not
    # a stream.
    assert response.headers["X-Accel-Buffering"] == "no"


def test_the_capability_url_needs_its_signature(server, server_client, key,
                                                token, running):
    job_id, _ = running

    assert server_client.get(f"/stream/logs/{job_id}/place/0").status_code == 400


def test_a_download_link_cannot_be_presented_as_a_stream(server, server_client,
                                                         key, token, running):
    '''Three grants, three message prefixes: none can be presented as another.'''
    job_id, _ = running
    storage = server.config["SC_STORAGE"]

    expires = int(time.time()) + 300
    wrong = storage.sign_download(job_id, expires)

    response = server_client.get(
        f"/stream/logs/{job_id}/place/0?expires={expires}&sig={wrong}")
    assert response.status_code == 400


def test_the_capability_carries_its_own_lifetime(server, server_client, key,
                                                 token, running):
    '''Independent of the 900-second access token, which is what lets a
    six-hour log outlive the credential that opened it.'''
    job_id, _ = running
    target = stream_url(server_client, key, token, job_id)

    expires = int(target.split("expires=")[1].split("&")[0])
    ceiling = server.config["SC_CONFIG"].limits["max_log_stream_seconds"]

    assert expires - time.time() > 900
    assert expires - time.time() <= ceiling + 5


###########################
# 🔴 The gate
###########################

def test_a_tail_reads_what_is_written_and_ends_when_the_node_does(
        server, server_client, key, token, running):
    job_id, log = running
    log.write_text("one\ntwo\nthree\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    parsed = frames(server_client.get(target))

    text = "".join(data["text"] for event, _, data in parsed if event == "log")
    assert text == "one\ntwo\nthree\n"

    assert [event for event, _, _ in parsed][-2:] == ["node_state", "end"]
    assert parsed[-1][2]["reason"] == "terminal"


def test_resuming_from_the_last_id_has_no_gap_and_no_repeat(
        server, server_client, key, token, running):
    '''🔴 The event id is the byte offset the reader reached, so a reconnect
    continues exactly where it stopped. A line number or a timestamp would both
    need the server to remember something about this caller.'''
    job_id, log = running
    log.write_text("one\ntwo\n")

    target = stream_url(server_client, key, token, job_id)
    second_target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    first = frames(server_client.get(target))

    read_so_far = "".join(d["text"] for e, _, d in first if e == "log")
    last_id = [i for e, i, _ in first if e == "log" and i][-1]

    # More arrived after the first reader stopped.
    with open(log, "a") as f:
        f.write("three\nfour\n")

    again = frames(server_client.get(
        second_target, headers={"Last-Event-ID": last_id}))
    rest = "".join(d["text"] for e, _, d in again if e == "log")

    assert read_so_far + rest == log.read_text()
    assert "one" not in rest


def test_only_log_events_carry_an_id(server, server_client, key, token, running):
    '''An id on `end` would have a reconnect ask to continue from the end of
    the stream.'''
    job_id, log = running
    log.write_text("one\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    parsed = frames(server_client.get(target))

    assert all(i is not None for e, i, _ in parsed if e == "log")
    assert all(i is None for e, i, _ in parsed if e != "log")


def test_an_unreadable_last_event_id_replays_rather_than_skipping(
        server, server_client, key, token, running):
    '''A stream that replays is a nuisance; one that silently skips is a lost
    log.'''
    job_id, log = running
    log.write_text("one\ntwo\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    parsed = frames(server_client.get(
        target, headers={"Last-Event-ID": "not-a-number"}))

    text = "".join(d["text"] for e, _, d in parsed if e == "log")
    assert text == "one\ntwo\n"


def test_a_log_that_shrank_restarts_rather_than_seeking_past_it(
        server, server_client, key, token, running):
    '''The offset points at bytes that are no longer there. Starting over is
    the only honest answer; seeking to the end would drop a log.'''
    job_id, log = running
    log.write_text("short\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    parsed = frames(server_client.get(
        target, headers={"Last-Event-ID": format(10_000, "x")}))

    text = "".join(d["text"] for e, _, d in parsed if e == "log")
    assert text == "short\n"


def test_the_end_event_names_the_archive_it_just_wrote(
        server, server_client, key, token, running):
    '''🔴 Indexed as the tail reaches the end rather than at the next poll,
    so a client that follows `end` straight to /logs is not told there is no
    log for a node whose log it has just finished reading.'''
    job_id, log = running
    log.write_text("done\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    parsed = frames(server_client.get(target))
    artifact_id = parsed[-1][2].get("artifact_id")

    assert artifact_id

    response = call(server_client, key, "GET",
                    f"/v1/jobs/{job_id}/artifacts/{artifact_id}", token)
    assert response.status_code == 303


def test_a_node_that_finishes_mid_stream_is_followed_to_its_end(
        server, server_client, key, token, running):
    '''The tail is live: it must not stop at the bytes that existed when it
    started.'''
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
        parsed = frames(server_client.get(
            stream_url(server_client, key, token, job_id)))
    finally:
        thread.join()

    text = "".join(d["text"] for e, _, d in parsed if e == "log")
    assert text == "first\nsecond\n"


###########################
# concurrent_log_streams
###########################

def test_the_published_stream_limit_is_enforced(server, server_client, key,
                                                token, running):
    '''🔴 A published number that nothing enforces is a promise rather than a
    limit.'''
    job_id, log = running
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


def test_a_finished_stream_gives_its_slot_back(server, server_client, key,
                                               token, running):
    '''The commonest way a tail ends is the reader hanging up, which reaches
    the generator as GeneratorExit -- so the release has to be in a finally or
    the slot leaks for the life of the process.'''
    job_id, log = running
    log.write_text("one\n")

    targets = [stream_url(server_client, key, token, job_id) for _ in range(3)]
    finish(server, job_id)

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    limiter = server.config["SC_STREAMS"]

    for target in targets:
        server_client.get(target)

    assert limiter.held(me) == 0


def test_one_callers_streams_do_not_count_against_another(server, server_client,
                                                          key, token, running):
    limiter = server.config["SC_STREAMS"]
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]

    limiter.acquire(me)
    assert limiter.held("somebody-else") == 0
    limiter.release(me)
    assert limiter.held(me) == 0


###########################
# The client
###########################

def test_the_client_reads_a_stream_to_the_end(server, server_client, key,
                                              token, running, monkeypatch):
    '''The parser, against bytes a real server produced.'''
    from siliconcompiler.remote.client.logs import _frames

    job_id, log = running
    log.write_text("alpha\nbeta\n")

    target = stream_url(server_client, key, token, job_id)
    finish(server, job_id)
    raw = server_client.get(target).get_data()

    class Fake:
        headers = {"Content-Type": "text/event-stream"}

        def iter_lines(self, decode_unicode=True):
            return iter(raw.decode().splitlines())

    tail = type("T", (), {"retry": None})()
    parsed = list(_frames(Fake(), tail))

    text = "".join(d["text"] for e, _, d in parsed if e == "log")
    assert text == "alpha\nbeta\n"
    # The server states its reconnect pace and the client takes it.
    assert tail.retry == 2


###########################
# Over a real socket
###########################
#
# The tests above run against app.test_client(), which builds the whole body
# before returning it -- so they check the frames and not the streaming. These
# use a real server on a real port, where a generator response, chunked
# transfer and a reader hanging up mid-stream are all actually exercised.

@pytest.fixture
def live(tmp_path):
    from werkzeug.serving import make_server

    from siliconcompiler.remote import Client, Credentials
    from siliconcompiler.remote.server.app import create_app
    from siliconcompiler.remote.server.ids import uuid7

    app = create_app(tmp_path / "datadir", cluster="local")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    credentials = Credentials(tmp_path / "sc-home" / "credentials")
    credentials.update(address=f"http://127.0.0.1:{server.server_port}")
    client = Client(credentials)

    store = app.config["SC_STORE"]
    me = client.me()["id"]

    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
        (job_id, me))
    store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                  "VALUES (?, 'place', '0', 'running')", (job_id,))

    job = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    log = app.config["SC_JOBS"].node_log_path(job, "place", "0")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("")

    try:
        yield client, app, job_id, log
    finally:
        server.shutdown()
        thread.join(timeout=10)


def write_then_finish(app, job_id, log, lines, pause=0.25):
    '''Append lines over time, then mark the node done.'''
    def run():
        for line in lines:
            time.sleep(pause)
            with open(log, "a") as f:
                f.write(line)
        time.sleep(pause)
        app.config["SC_STORE"].execute(
            "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))

    thread = threading.Thread(target=run)
    thread.start()
    return thread


def test_the_client_tails_a_live_node_to_the_end(live):
    client, app, job_id, log = live
    lines = [f"line {n}\n" for n in range(1, 6)]
    writer = write_then_finish(app, job_id, log, lines)

    try:
        text = client.tail_log(job_id, "place", "0")
    finally:
        writer.join()

    assert text == "".join(lines)
    assert text == log.read_text()


def test_a_reader_that_hangs_up_resumes_without_a_gap(live):
    '''🔴 Phase 5's gate. The reconnect re-requests /logs rather than reusing
    the target, and hands back the last id it saw.'''
    from siliconcompiler.remote.client.logs import LogTail

    client, app, job_id, log = live
    lines = [f"line {n}\n" for n in range(1, 9)]
    writer = write_then_finish(app, job_id, log, lines, pause=0.2)

    tail = LogTail(client, job_id, "place", "0")
    first = []

    try:
        # Read a couple of frames and then drop the connection, as a laptop
        # closing its lid would.
        response = client.follow_log(job_id, "place", "0")
        assert response.headers["Content-Type"].startswith("text/event-stream")

        from siliconcompiler.remote.client.logs import _frames

        for event, identifier, data in _frames(response, tail):
            if event == "log":
                first.append(data["text"])
                tail.last_event_id = identifier
                if len(first) >= 2:
                    break
        response.close()

        assert tail.last_event_id

        rest = tail.follow()
    finally:
        writer.join()

    whole = "".join(first) + rest
    assert whole == log.read_text()
    # No repeat: the second connection started where the first stopped.
    assert rest.count("line 1") == 0


def test_a_tail_that_starts_after_the_node_finished_gets_the_archive(live):
    '''The same bytes, reached by the other branch of the 303 -- and the client
    tells them apart by the Content-Type it was served, never by the redirect.'''
    client, app, job_id, log = live
    log.write_text("all done\n")
    app.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))

    response = client.follow_log(job_id, "place", "0")
    assert not response.headers["Content-Type"].startswith("text/event-stream")

    assert client.tail_log(job_id, "place", "0") == "all done\n"


def test_the_session_is_not_handed_to_the_stream_target(live):
    '''🔴 requests drops Authorization across hosts and knows nothing about
    DPoP, so an automatically-followed redirect would hand a signed proof to
    whatever storage happens to be. The target carries its own credential.'''
    client, app, job_id, log = live
    log.write_text("x\n")
    app.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))

    response = client.follow_log(job_id, "place", "0")

    sent = response.request.headers
    assert "Authorization" not in sent
    assert "DPoP" not in sent
