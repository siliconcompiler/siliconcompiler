import json

import pytest
import responses

from conftest import problem

from siliconcompiler.remote.client.errors import ServerProblem
from siliconcompiler.remote.client.logs import LogTail


# The client's half of the live tail, against canned answers no server can be
# made to give on demand: an expired stream, an unknown `end`, a refusal.

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


def end(reason):
    return ("end", None, {"reason": reason})


def stream(fake_v1, number, body, status=200, content_type="text/event-stream"):
    '''One `/logs` answer: a `303` to a stream URL of its own.'''
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


def follow(logged_in, **kwargs):
    return LogTail(logged_in, "j1", "place", "0").follow(**kwargs)


@pytest.fixture
def no_wait(monkeypatch):
    slept = []
    monkeypatch.setattr("siliconcompiler.remote.client.logs.time.sleep",
                        lambda seconds: slept.append(seconds))
    return slept


@pytest.mark.parametrize("reason", ["expired", "a-reason-from-a-later-server"])
def test_an_ended_stream_reconnects_with_the_last_event_id(logged_in, fake_v1, no_wait,
                                                           reason):
    '''🔴 An `end` other than `terminal` ends this connection: ask `/logs`
    again and hand the last id to the new stream, never to `/logs` (D306).'''
    stream(fake_v1, 1, sse(log("7", "one\n"), end(reason)))
    stream(fake_v1, 2, sse(log("8", "two\n"), end("terminal")))

    assert follow(logged_in) == "one\ntwo\n"

    assert len(asked_logs(fake_v1)) == 2
    assert not [c for c in asked_logs(fake_v1) if "Last-Event-ID" in c.request.headers]
    first, second = streams(fake_v1)
    assert "Last-Event-ID" not in first.request.headers
    assert second.request.headers["Last-Event-ID"] == "7"
    assert first.request.url != second.request.url


def test_empty_reconnects_never_give_up(logged_in, fake_v1, no_wait):
    '''A quiet node is not a broken one: ask until the node is over.'''
    quiet = 12
    for number in range(quiet):
        stream(fake_v1, number, sse(end("expired")))
    stream(fake_v1, quiet, sse(log("1", "at last\n"), end("terminal")))
    assert follow(logged_in) == "at last\n"
    assert len(asked_logs(fake_v1)) == quiet + 1
    assert len(no_wait) == quiet


@pytest.mark.parametrize("body,status,content_type,refusal", [
    (json.dumps(problem("limit-exceeded", 429, limit="concurrent_log_streams",
                        detail="you already have 4 logs open")),
     429, "application/problem+json", "limit-exceeded"),
    ("<html>sign in</html>", 200, "text/html", None),
], ids=["refusal", "not-a-stream"])
def test_only_an_event_stream_after_the_redirect_is_the_log(
        logged_in, fake_v1, no_wait, body, status, content_type, refusal):
    '''🔴 The stream host's refusal, or a `200` from something in the middle,
    is raised and never printed as log text.'''
    stream(fake_v1, 1, body, status=status, content_type=content_type)
    written = []
    with pytest.raises(ServerProblem) as raised:
        follow(logged_in, write=written.append)
    assert written == []
    if refusal:
        assert raised.value.slug == refusal
        assert raised.value.member("limit") == "concurrent_log_streams"


def test_the_stream_url_is_opaque_to_the_client(logged_in, fake_v1, no_wait):
    '''Followed exactly as given, nonce and `ended=1` included. A last event
    with no closing blank line is still read.'''
    target = f"{ORIGIN}/stream/logs/j1/place/0?expires=9&n=abc&sig=S&ended=1"
    fake_v1.route(responses.GET, "jobs/j1/logs", "", status=303,
                  headers={"Location": target})
    fake_v1.elsewhere(responses.GET, f"{ORIGIN}/stream/logs/j1/place/0",
                      sse(log("1", "done\n"), end("terminal")).rstrip("\n"),
                      content_type="text/event-stream")

    assert follow(logged_in) == "done\n"
    followed, = streams(fake_v1)
    assert followed.request.url == target


def job(state):
    return {"id": "j1", "state": state, "terminal": state == "completed", "nodes": []}


@pytest.mark.parametrize("header,waited", [("1", 1), ("0", 1), ("0.25", 1), ("3", 3)])
def test_a_retry_after_is_honoured_down_to_one_second(logged_in, fake_v1, header, waited):
    '''Whole seconds, never below 1, and no longer floor of the client's own.'''
    fake_v1.route(responses.GET, "jobs/j1", job("running"), headers={"Retry-After": header})
    _, retry_after = logged_in.job("j1")
    assert retry_after == waited
