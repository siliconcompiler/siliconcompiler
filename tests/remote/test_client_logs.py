import hashlib
import io
import json
import tarfile

import pytest
import responses

from conftest import problem

from siliconcompiler.remote.client.errors import ServerProblem
from siliconcompiler.remote.client.logs import LogTail, _IN_FULL, _lines


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


def end(reason, **members):
    return ("end", None, {"reason": reason, **members})


def stream(fake_v1, number, body, status=200, content_type="text/event-stream",
           headers=None):
    '''One `/logs` answer: a `303` to a stream URL of its own.'''
    target = f"{ORIGIN}/stream/{number}"
    fake_v1.route(responses.GET, "jobs/j1/logs", "", status=303,
                  headers={"Location": target})
    fake_v1.elsewhere(responses.GET, target, body, status=status,
                      content_type=content_type, headers=headers)
    return target


def archive(fake_v1, text):
    '''The node's `logs` artifact, listed with its size and digest and served
    as the gzip tar of its log the server stores.'''
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("sc_place_0.log")
        info.size = len(text.encode())
        tar.addfile(info, io.BytesIO(text.encode()))
    body = buffer.getvalue()
    fake_v1.route(responses.GET, "jobs/j1/artifacts", {"items": [
        {"id": "log1", "step": "place", "index": "0", "kind": "logs", "fetchable": True,
         "size_bytes": len(body), "digest": f"sha256:{hashlib.sha256(body).hexdigest()}"}]})
    fake_v1.route(responses.GET, "jobs/j1/artifacts/log1", body,
                  content_type="application/gzip")


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
    '''An `end` other than `terminal` ends this connection: ask `/logs`
    again and hand the last id to the new stream, never to `/logs`.'''
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
    '''The stream host's refusal, or a `200` from something in the middle,
    is raised and never printed as log text.'''
    stream(fake_v1, 1, body, status=status, content_type=content_type)
    written = []
    with pytest.raises(ServerProblem) as raised:
        follow(logged_in, write=written.append)
    assert written == []
    if refusal:
        assert raised.value.slug == refusal
        assert raised.value.member("limit") == "concurrent_log_streams"


def test_a_stream_slot_refused_for_now_is_waited_for(logged_in, fake_v1, no_wait):
    '''A `429` from the stream host with `Retry-After` refills: wait, then ask
    `/logs` again for a fresh target.'''
    stream(fake_v1, 1, json.dumps(problem("limit-exceeded", 429,
                                          limit="concurrent_log_streams")),
           status=429, content_type="application/problem+json",
           headers={"Retry-After": "7"})
    stream(fake_v1, 2, sse(log("1", "in\n"), end("terminal")))

    assert follow(logged_in) == "in\n"
    assert no_wait == [7]
    assert len(asked_logs(fake_v1)) == 2


@pytest.mark.parametrize("archived,shown", [
    ("one\ntwo\n", "one\ntwo\n"),
    ("rotated\n", "one\n" + _IN_FULL + "rotated\n"),
], ids=["placed", "not-placed"])
def test_a_resumed_stream_that_ends_at_once_is_finished_from_the_archive(
        logged_in, fake_v1, no_wait, archived, shown):
    '''Once the node is over a resumed stream replays nothing: what it did not
    show comes from the archive, or all of the archive, said so.'''
    stream(fake_v1, 1, sse(log("7", "one\n"), end("expired")))
    stream(fake_v1, 2, sse(end("terminal", artifact_id="log1")))
    archive(fake_v1, archived)

    assert follow(logged_in) == shown


def test_a_line_ends_at_crlf_lf_or_cr_wherever_the_reads_split_it():
    '''A CRLF split across two reads ends one line, not two, and the text is
    UTF-8 even where a read splits a character.'''
    body = 'event: log\r\nid: 1\rdata: {"text": "5 \u00b5m"}\n\r\n'.encode()
    for cut in range(len(body) + 1):
        assert list(_lines([body[:cut], body[cut:]])) == \
            ["event: log", "id: 1", 'data: {"text": "5 \u00b5m"}', ""]


def test_an_event_stream_is_utf8_with_no_charset_named(logged_in, fake_v1, no_wait):
    '''`text/event-stream` is always UTF-8, though HTTP's default for text is not.'''
    body = 'id: 1\nevent: log\ndata: {"text": "5 \u00b5m\\n"}\n\n'
    stream(fake_v1, 1, (body + sse(end("terminal"))).encode())
    assert follow(logged_in) == "5 \u00b5m\n"


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
