import json

import pytest
import responses

from conftest import problem

from siliconcompiler.remote.client.errors import ServerProblem
from siliconcompiler.remote.client.logs import LogTail


# The client's half of the live tail, against canned answers: a server cannot
# be made to expire a stream on demand, send an `end` nobody has invented yet,
# or answer a stream URL with a refusal.

ORIGIN = "https://sc-server.test"


def sse(*events):
    '''An SSE body from (event, id, data) triples.'''
    lines = []
    for event, identifier, data in events:
        if identifier is not None:
            lines.append(f"id: {identifier}")
        lines.append(f"event: {event}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")
    return "\n".join(lines) + "\n"


def log(identifier, text):
    return ("log", identifier, {"step": "place", "index": "0", "text": text,
                                "logged_at": "2026-09-28T10:00:00.000Z"})


def end(reason, **members):
    return ("end", None, {"reason": reason, **members})


def stream(fake_v1, number, body, status=200, content_type="text/event-stream"):
    '''One `/logs` answer: a `303` to a stream URL of its own, as a server
    hands out one URL per request.'''
    target = f"{ORIGIN}/stream/{number}"
    fake_v1.route(responses.GET, "jobs/j1/logs", "", status=303,
                  headers={"Location": target})
    fake_v1.elsewhere(responses.GET, target, body, status=status,
                      content_type=content_type)
    return target


def asked_logs(fake_v1):
    return [c for c in fake_v1.calls if c.request.path_url.startswith("/v1/jobs/j1/logs")]


def streams(fake_v1):
    return [c for c in fake_v1.calls if c.request.path_url.startswith("/stream/")]


@pytest.fixture
def no_wait(monkeypatch):
    slept = []
    monkeypatch.setattr("siliconcompiler.remote.client.logs.time.sleep",
                        lambda seconds: slept.append(seconds))
    return slept


@pytest.mark.parametrize("reason", ["expired", "a-reason-from-a-later-server"])
def test_an_ended_stream_reconnects_with_the_last_event_id(logged_in, fake_v1, no_wait,
                                                           reason):
    '''🔴 `expired`, and any `end` the client does not know, is this
    connection being over: ask `/logs` again, never reuse the target, and hand
    back the last id.'''
    stream(fake_v1, 1, sse(log("7", "one\n"), end(reason)))
    stream(fake_v1, 2, sse(log("8", "two\n"), end("terminal")))

    text = LogTail(logged_in, "j1", "place", "0").follow()

    assert text == "one\ntwo\n"
    assert len(asked_logs(fake_v1)) == 2
    first, second = streams(fake_v1)
    assert "Last-Event-ID" not in first.request.headers
    assert second.request.headers["Last-Event-ID"] == "7"
    assert first.request.url != second.request.url


def test_last_event_id_goes_on_the_stream_and_never_to_logs(logged_in, fake_v1, no_wait):
    '''Surface D306: `Last-Event-ID` goes on the stream request, after
    following the new `303`, and `/logs` never reads it.'''
    stream(fake_v1, 1, sse(log("7", "one\n"), end("expired")))
    stream(fake_v1, 2, sse(log("8", "two\n"), end("terminal")))

    LogTail(logged_in, "j1", "place", "0").follow()

    assert not [c for c in asked_logs(fake_v1) if "Last-Event-ID" in c.request.headers]
    assert streams(fake_v1)[-1].request.headers["Last-Event-ID"] == "7"


def test_empty_reconnects_never_give_up(logged_in, fake_v1, no_wait):
    '''A quiet node is not a broken one: however many streams expire with
    nothing on them, the tail keeps asking until the node is over.'''
    quiet = 12
    for number in range(quiet):
        stream(fake_v1, number, sse(end("expired")))
    stream(fake_v1, quiet, sse(log("1", "at last\n"), end("terminal")))

    text = LogTail(logged_in, "j1", "place", "0").follow()

    assert text == "at last\n"
    assert len(asked_logs(fake_v1)) == quiet + 1
    assert len(no_wait) == quiet


def test_a_refusal_after_the_redirect_is_raised_and_never_printed(
        logged_in, fake_v1, no_wait):
    '''🔴 After the `303` only `text/event-stream` is the log. The stream
    host's `concurrent_log_streams` refusal is a refusal, not log text.'''
    body = problem("limit-exceeded", 429, limit="concurrent_log_streams",
                   detail="you already have 4 logs open")
    stream(fake_v1, 1, json.dumps(body), status=429,
           content_type="application/problem+json")
    written = []

    with pytest.raises(ServerProblem) as raised:
        LogTail(logged_in, "j1", "place", "0").follow(write=written.append)

    assert raised.value.slug == "limit-exceeded"
    assert raised.value.member("limit") == "concurrent_log_streams"
    assert written == []


def test_a_non_stream_success_after_the_redirect_is_not_printed(
        logged_in, fake_v1, no_wait):
    '''A `200` that is not an event stream is not a log either: something in
    the middle answered, and what it said is not the node's output.'''
    stream(fake_v1, 1, "<html>sign in</html>", content_type="text/html")
    written = []

    with pytest.raises(ServerProblem):
        LogTail(logged_in, "j1", "place", "0").follow(write=written.append)

    assert written == []


###########################
# Polling
###########################

def job(state):
    terminal = state in ("completed", "failed", "cancelled", "rejected", "abandoned")
    return {"id": "j1", "state": state, "terminal": terminal, "nodes": []}


@pytest.mark.parametrize("header,waited", [("1", 1), ("0", 1), ("0.25", 1), ("3", 3)])
def test_a_retry_after_is_honoured_down_to_one_second(logged_in, fake_v1, header, waited):
    '''The server's pace in whole seconds, never below 1: a `1` is waited as
    1 with no longer floor of the client's own, and less than 1 as 1.'''
    fake_v1.route(responses.GET, "jobs/j1", job("running"), headers={"Retry-After": header})

    _, retry_after = logged_in.job("j1")

    assert retry_after == waited


def test_the_poll_loop_waits_what_the_server_said(logged_in, fake_v1, nop_project,
                                                  monkeypatch):
    from siliconcompiler.remote.client.run import RemoteRun

    slept = []
    monkeypatch.setattr("siliconcompiler.remote.client.run.time.sleep",
                        lambda seconds: slept.append(seconds))
    fake_v1.route(responses.GET, "jobs/j1", job("running"), headers={"Retry-After": "1"})
    fake_v1.route(responses.GET, "jobs/j1", job("running"), headers={"Retry-After": "0"})
    fake_v1.route(responses.GET, "jobs/j1", job("completed"))

    RemoteRun(nop_project, logged_in)._poll("j1")

    assert slept[:2] == [1, 1]


def test_the_stream_url_is_opaque_to_the_client(logged_in, fake_v1, no_wait):
    """The host's own nonce `n` and unsigned `ended=1` are its business: the
    client follows the URL `/logs` handed it exactly as given, and reads
    neither."""
    target = f"{ORIGIN}/stream/logs/j1/place/0?expires=9&n=abc&sig=S&ended=1"
    fake_v1.route(responses.GET, "jobs/j1/logs", "", status=303,
                  headers={"Location": target})
    fake_v1.elsewhere(responses.GET, f"{ORIGIN}/stream/logs/j1/place/0",
                      sse(log("1", "done\n"), end("terminal")),
                      content_type="text/event-stream")

    assert LogTail(logged_in, "j1", "place", "0").follow() == "done\n"
    followed, = streams(fake_v1)
    assert followed.request.url == target
