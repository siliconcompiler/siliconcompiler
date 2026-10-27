import json
import time

from urllib.parse import urlsplit

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.outputs import logstream  # noqa: E402

from conftest import finish, slug, write_progress  # noqa: E402


def frames(response):
    '''An SSE body as (event, id, data) triples.'''
    found = []
    for block in response.get_data(as_text=True).split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            found.append((fields["event"], fields.get("id"), json.loads(fields["data"])))
    return found


def stream(server_client, redirect, **headers):
    target = urlsplit(redirect.headers["Location"])
    return server_client.get(f"{target.path}?{target.query}", headers=headers)


def logs(api, job, query="?step=stepone&index=0"):
    return api("GET", f"/v1/jobs/{job['id']}/logs{query}")


@pytest.mark.parametrize("nodes, status, problem", [
    ({"stepone/0": "pending", "steptwo/0": "pending"}, 409, "not-ready"),
    ({"stepone/0": "queued", "steptwo/0": "pending"}, 409, "not-ready"),
    ({"stepone/0": "running", "steptwo/0": "pending"}, 303, None),
])
def test_a_node_answers_by_how_far_it_has_got(server, api, dispatcher, tree, nodes, status,
                                              problem):
    write_progress(server, tree[0], "running", nodes)

    answer = logs(api, tree[0])

    assert answer.status_code == status
    if problem:
        assert slug(answer) == problem and answer.get_json()["artifact_kind"] == "logs"
        assert answer.headers["Retry-After"]
    else:
        assert "/stream/logs/" in answer.headers["Location"]


@pytest.mark.parametrize("query, status, problem", [
    ("?step=stepone", 400, "invalid-request"),
    ("?index=0", 400, "invalid-request"),
    ("", 501, "feature-unsupported"),
    ("?step=nowhere&index=0", 404, "not-found"),
])
def test_a_request_the_server_cannot_serve_is_named(server, api, dispatcher, tree, query,
                                                    status, problem):
    write_progress(server, tree[0], "running", {"stepone/0": "running"})
    answer = logs(api, tree[0], query)
    assert (answer.status_code, slug(answer)) == (status, problem)


def test_a_finished_node_is_a_stream_that_sends_its_log_and_names_the_archive(
        server, server_client, api, stranger, dispatcher, tree):
    job, _ = tree
    finish(server, api, dispatcher, job)
    archived, = [a for a in api("GET", f"/v1/jobs/{job['id']}/artifacts?kind=logs&step=stepone")
                 .get_json()["items"]]

    redirect = logs(api, job)
    assert redirect.status_code == 303
    response = stream(server_client, redirect)

    assert response.mimetype == "text/event-stream"
    log, state, end = frames(response)
    assert log[0] == "log" and log[2]["text"] == "stepone ran\n" and log[1] == "c"
    assert state[2] == {"step": "stepone", "index": "0", "state": "completed",
                        "terminal": True, "artifact_id": archived["id"]}
    assert end[:2] == ("end", None)
    assert end[2] == {"reason": "terminal", "artifact_id": archived["id"]}
    assert logs(stranger, job).status_code == 404


def test_a_resumed_stream_sends_only_what_follows_the_id(server, server_client, api, dispatcher,
                                                         tree):
    job, root = tree
    (root / "stepone" / "0" / "sc_stepone_0.log").write_text("one\ntwo\nthree\n")
    finish(server, api, dispatcher, job)

    resumed = frames(stream(server_client, logs(api, job), **{"Last-Event-ID": "8"}))

    assert resumed[0][2]["text"] == "three\n" and resumed[0][1] == "e"


@pytest.mark.parametrize("header", [None, "", "not hex", "-5"])
def test_an_id_that_cannot_be_read_starts_over(header):
    assert logstream.resume_from(header) == 0


def test_a_finished_node_with_no_log_is_not_found(server, api, dispatcher, tree):
    job, root = tree
    (root / "stepone" / "0" / "sc_stepone_0.log").unlink()
    finish(server, api, dispatcher, job)

    answer = logs(api, job)

    assert (answer.status_code, slug(answer)) == (404, "not-found")


@pytest.fixture
def log(tmp_path, monkeypatch):
    # Asked on every pass, so a test's states are seen in turn.
    monkeypatch.setattr(logstream, "STATE_SECONDS", 0)
    path = tmp_path / "sc_place_0.log"
    path.write_bytes(b"")
    return tmp_path, path


def run_stream(tree, path, states, start=0, deadline=None):
    '''The stream's frames while the node reports each of ``states`` in turn.'''
    # The last state stays: a node that ended does not start again.
    return frames_of(logstream.events(
        tree, path, "place", "0", lambda: states.pop(0) if len(states) > 1 else states[0],
        lambda: "art",
        start, deadline if deadline is not None else time.time() - 1))


def frames_of(generator):
    class Body:
        def get_data(self, as_text):
            return b"".join(generator).decode()
    return frames(Body())


def test_a_running_node_sends_whole_lines_and_leaves_the_rest_for_later(log):
    tree, path = log
    path.write_bytes("na\u00efve\nhalf a li".encode())

    found = run_stream(tree, path, ["running"])

    assert [(event, ident) for event, ident, _ in found] == [("log", "7"), ("end", None)]
    assert found[0][2]["text"] == "na\u00efve\n"
    assert found[1][2] == {"reason": "expired"}


def test_a_node_that_ends_is_drained_to_its_last_unterminated_line(log):
    tree, path = log
    path.write_bytes(b"one\nlast")

    found = run_stream(tree, path, ["running", "completed"], deadline=time.time() + 60)

    assert [(e, i) for e, i, _ in found] == [("log", "4"), ("log", "8"), ("node_state", None),
                                             ("end", None)]
    assert "".join(d["text"] for e, _, d in found if e == "log") == "one\nlast"


def test_a_line_longer_than_a_chunk_is_never_split_inside_a_character(log, monkeypatch):
    tree, path = log
    monkeypatch.setattr(logstream, "MAX_CHUNK", 8)
    path.write_bytes("\u00e9".encode() * 9)

    found = run_stream(tree, path, ["completed"])

    assert [d["text"] for e, _, d in found if e == "log"] == ["\u00e9" * 4, "\u00e9" * 4,
                                                              "\u00e9"]


def test_a_stream_asks_the_nodes_state_at_its_own_pace_not_each_poll(log, monkeypatch):
    '''Each ask reconciles the job, which on Slurm runs `squeue`.'''
    tree, path = log
    monkeypatch.setattr(logstream, "STATE_SECONDS", 60)
    asked = []

    def node_state():
        asked.append("running")
        return "running"

    frames_of(logstream.events(tree, path, "place", "0", node_state, lambda: "art", 0,
                               time.time() + 0.6))

    assert asked == ["running"]
