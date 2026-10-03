import threading
import time

import pytest

from conftest import call, slug
from test_logs import frames, live_server, make_job, stream_url


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.outputs import logstream                  # noqa: E402


# `GET /v1/jobs/{id}/logs` with no step and no index: every node's live log in
# one stream. The rule an implementation gets wrong is that the id is the JOB's.


class Job:
    '''Nodes' logs on disk, and the states a stream asks about.'''

    def __init__(self, root, nodes=(("place", "0"), ("route", "0"))):
        self.nodes = list(nodes)
        self.root = root
        self.states = {node: "running" for node in self.nodes}
        self.over = False
        for step, index in self.nodes:
            self.path(step, index).write_text("")

    def path(self, step, index):
        return self.root / f"{step}.{index}.log"

    def write(self, step, text):
        with open(self.path(step, "0"), "a") as f:
            f.write(text)

    def complete(self):
        '''Every node done; the job ends with them.'''
        self.states = {node: "completed" for node in self.nodes}

    def finish(self):
        self.complete()
        self.over = True

    def index(self):
        '''A reader's view of the job's one event index.'''
        return logstream.EventIndex(self.root / "stream.idx", len(self.nodes))

    def resume(self, given):
        return logstream.resume_job(given, None, self.index())

    def events(self, start=0, deadline=None):
        return logstream.job_events(
            self.nodes, self.path, node_states=lambda: dict(self.states),
            job_over=lambda: self.over, start=start,
            deadline=deadline or time.monotonic() + 30, keepalive=15,
            artifact_id=lambda step, index: f"art-{step}", index=self.index())


def parse(chunks):
    class Body:
        def get_data(self, as_text=False):
            return b"".join(chunks).decode()
    return frames(Body())


def run_to_end(job, **kwargs):
    '''Consume a job stream whose nodes have all finished.'''
    return parse(list(job.events(**kwargs)))


def read_until(job, stop):
    '''Read a live stream until ``stop(chunks)``, then hang up.'''
    chunks = []
    stream = job.events()
    for chunk in stream:
        chunks.append(chunk)
        if stop(chunks):
            break
    stream.close()
    return parse(chunks)


def text(events, step):
    return "".join(d["text"] for e, _, d in events if e == "log" and d["step"] == step)


def test_every_node_is_in_one_stream_in_its_own_order_naming_its_own_archive(tmp_path):
    '''Per-event coordinates. No archive for a job: each node names its own, and `end` none.'''
    job = Job(tmp_path)
    job.write("place", "".join(f"line {n}\n" for n in range(200)))
    job.write("route", "routing\n")
    job.complete()

    events = run_to_end(job)
    states = {(d["step"], d["index"]): d.get("artifact_id")
              for e, _, d in events if e == "node_state"}

    assert text(events, "place") == job.path("place", "0").read_text()
    assert text(events, "route") == "routing\n"
    assert states == {("place", "0"): "art-place", ("route", "0"): "art-route"}
    assert events[-1] == ("end", None, {"reason": "terminal"})


def test_the_id_is_the_jobs_only_goes_up_and_is_the_same_for_every_reader(tmp_path):
    '''A per-node offset resumes every other node at a position not its
    own. An id means the same bytes whoever hands it back.'''
    job = Job(tmp_path)
    job.write("place", "a\n")
    job.write("route", "bb\n")
    job.write("place", "ccc\n")
    job.complete()

    def logs(events):
        return [(i, d["step"], d["text"]) for e, i, d in events if e == "log"]

    first, second = logs(run_to_end(job)), logs(run_to_end(job))
    positions = [int(i[1:], 16) for i, _, _ in first]

    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    assert first and first == second


def test_the_id_does_not_grow_with_the_node_count(tmp_path):
    '''`Last-Event-ID` is a request header; a vector of per-node
    positions can pass what proxies accept on a thousand-node flow.'''
    job = Job(tmp_path, nodes=[(f"n{i}", "0") for i in range(1000)])
    for i in range(0, 1000, 3):
        job.write(f"n{i}", "hello\n")
    job.complete()
    ids = [i for e, i, _ in run_to_end(job) if e == "log"]
    assert len(ids) == 334
    assert max(len(i) for i in ids) <= 4
    assert job.resume(ids[-1]) == 334


def test_resuming_from_a_job_id_has_no_gap_and_no_repeat(tmp_path):
    job = Job(tmp_path)
    job.write("place", "p1\np2\n")
    job.write("route", "r1\n")

    seen = read_until(job, lambda chunks: sum(c.startswith(b"event: log")
                                              for c in chunks) == 2)
    last = [i for e, i, _ in seen if e == "log"][-1]

    # More from both, then they finish: the job is open, so the reconnect drains.
    job.write("place", "p3\n")
    job.write("route", "r2\n")
    job.complete()

    rest = run_to_end(job, start=job.resume(last))

    for step in ("place", "route"):
        assert text(seen, step) + text(rest, step) == job.path(step, "0").read_text()


def test_a_job_already_over_ends_at_once_and_replays_nothing(tmp_path):
    '''Late or resumed, the same path: what was unread is in the archives,
    which the client reads from the `kind=logs` listing.'''
    job = Job(tmp_path)
    job.write("place", "p1\n")
    job.finish()
    assert run_to_end(job) == [("end", None, {"reason": "terminal"})]
    assert run_to_end(job, start=job.resume("e0")) == [("end", None, {"reason": "terminal"})]


def test_a_node_that_never_ran_is_reported_and_ends_nothing(tmp_path):
    job = Job(tmp_path)
    job.states = {("place", "0"): "skipped", ("route", "0"): "running"}
    job.write("route", "still going\n")
    events = read_until(job, lambda chunks: b"node_state" in chunks[-1])
    assert ("node_state", {"step": "place", "index": "0", "state": "skipped",
                           "terminal": True, "artifact_id": "art-place"}) \
        in [(e, d) for e, _, d in events]
    assert not any(e == "end" for e, _, _ in events)


def test_a_line_longer_than_a_chunk_is_never_split_inside_a_character(tmp_path):
    job = Job(tmp_path)
    job.write("place", "é" * logstream.MAX_CHUNK + "\n")
    job.complete()
    texts = [d["text"] for e, _, d in run_to_end(job) if e == "log" and d["step"] == "place"]
    assert len(texts) > 1
    assert "\ufffd" not in "".join(texts)
    assert "".join(texts) == job.path("place", "0").read_text()


def indexed(tmp_path):
    '''A job whose index holds three entries, one per node.'''
    job = Job(tmp_path, nodes=[("a", "0"), ("b", "0"), ("c", "0")])
    for step in ("a", "b", "c"):
        job.write(step, f"{step}\n")
    job.complete()
    run_to_end(job)
    assert job.index().count() == 3
    return job


@pytest.mark.parametrize("given", [
    None, "not-an-id",
    "1a",                                  # a per-node id: a byte offset
    "5-0:2.1:3",                           # the per-node vector this used to emit
    "e4",                                  # past the end of this job's index
    "e-1",
])
def test_an_id_that_is_not_this_jobs_starts_from_the_beginning(tmp_path, given):
    '''A stream that replays is a nuisance; one that skips is a lost log.'''
    assert indexed(tmp_path).resume(given) == 0


def test_a_good_id_is_a_seek_into_the_index(tmp_path):
    job = indexed(tmp_path)
    assert job.resume("e2") == 2
    assert logstream.resume_job(None, "e3", job.index()) == 3
    rest = [(i, d["text"]) for e, i, d in run_to_end(job, start=2) if e == "log"]
    assert rest == [("e3", "c\n")]


@pytest.fixture
def job(server, server_client, key, token):
    '''A running job with two nodes, both logging.'''
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    job_id, logs = make_job(server, me, ("place", "route"))
    for step, log in logs.items():
        log.write_text(f"{step} says hello\n")
    return job_id


def end_job(server, job_id, state="completed"):
    store = server.config["SC_STORE"]
    store.execute("UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))
    store.execute("UPDATE jobs SET state = ? WHERE id = ?", (state, job_id))


def test_no_coordinates_is_the_whole_job_under_its_own_signature(server, server_client,
                                                                 key, token, job):
    '''Own signature prefixes: a job link cannot be edited into a node link.'''
    target = stream_url(server_client, key, token, job, step=None)
    assert target.startswith(f"/stream/logs/{job}?")
    query = target.split("?", 1)[1]
    assert server_client.get(f"/stream/logs/{job}/place/0?{query}").status_code == 400
    assert server_client.get(f"/stream/logs/{job}?expires=1&sig=x").status_code == 400

    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job,))
    response = server_client.get(target)

    assert response.headers["Content-Type"].startswith("text/event-stream")
    events = frames(response)
    assert {d["step"] for e, _, d in events if e == "log"} == {"place", "route"}
    assert events[-1][0] == "end"
    assert "artifact_id" not in events[-1][2]


@pytest.mark.parametrize("half", ["?step=place", "?index=0"])
def test_one_coordinate_without_the_other_is_a_bad_request(server_client, key,
                                                           token, job, half):
    response = call(server_client, key, "GET", f"/v1/jobs/{job}/logs{half}", token)
    assert response.status_code == 400
    assert slug(response) == "invalid-request"


def test_before_any_node_starts_it_is_not_ready(server, server_client, key, token, job):
    '''Transient, as for a node that has not started.'''
    store = server.config["SC_STORE"]
    store.execute("UPDATE job_nodes SET state = 'pending' WHERE job_id = ?", (job,))
    store.execute("UPDATE jobs SET state = 'queued' WHERE id = ?", (job,))
    response = call(server_client, key, "GET", f"/v1/jobs/{job}/logs", token)
    assert response.status_code == 409
    assert slug(response) == "not-ready"
    assert response.get_json()["artifact_kind"] == "logs"
    assert response.headers["Retry-After"]


@pytest.mark.parametrize("state", ["completed", "failed", "cancelled"])
def test_a_finished_job_is_a_stream_that_ends_at_once(server, server_client, key,
                                                      token, job, state):
    '''Not a refusal: it is the race case arriving late.'''
    end_job(server, job, state)
    events = frames(server_client.get(stream_url(server_client, key, token, job, step=None)))
    assert events == [("end", None, {"reason": "terminal"})]


@pytest.mark.parametrize("features,missing", [
    ([], "logs.stream"),
    (["logs.stream"], "logs.stream.job"),
])
def test_the_refusal_names_the_broadest_missing_capability(
        server, server_client, key, token, job, features, missing):
    server.config["SC_CONFIG"]._values["features"] = features
    response = call(server_client, key, "GET", f"/v1/jobs/{job}/logs", token)
    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"
    assert response.get_json()["feature"] == missing


def test_the_job_stream_holds_one_slot(server, server_client, key, token, job):
    '''A flow wider than `concurrent_log_streams` can be watched in full on one connection.'''
    streams = server.config["SC_STREAMS"]
    streams._ceiling = 1
    end_job(server, job)
    owner = server.config["SC_STORE"].one(
        "SELECT user_id FROM jobs WHERE id = ?", (job,))["user_id"]
    assert streams.acquire(owner)
    try:
        response = server_client.get(stream_url(server_client, key, token, job, step=None))
        assert response.status_code == 429
        assert response.get_json()["limit"] == "concurrent_log_streams"
    finally:
        streams.release(owner)

    frames(server_client.get(stream_url(server_client, key, token, job, step=None)))
    assert streams.held(owner) == 0


def test_the_job_stream_implies_the_others(tmp_path):
    '''Never advertised alone: a client falls back to per-node streams.'''
    import json
    from siliconcompiler.remote.server.config import Config
    (tmp_path / "config.json").write_text(json.dumps({"features": ["logs.stream.job"]}))
    with pytest.raises(ValueError, match="logs.stream.job without logs.stream"):
        Config.load(tmp_path)


@pytest.fixture
def live(tmp_path):
    with live_server(tmp_path, ("place", "route")) as served:
        yield served


def test_the_client_follows_the_whole_job_to_its_end(live):
    from siliconcompiler.remote.client.logs import LogTail

    client, app, job_id, logs = live

    def run():
        for n in range(4):
            time.sleep(0.15)
            for step, log in logs.items():
                with open(log, "a") as f:
                    f.write(f"{step} {n}\n")
        time.sleep(0.2)
        end_job(app, job_id)

    writer = threading.Thread(target=run)
    writer.start()
    try:
        text = LogTail(client, job_id).follow()
    finally:
        writer.join()

    for step, log in logs.items():
        assert [line for line in text.splitlines() if line.startswith(step)] == \
            log.read_text().splitlines()


def test_a_finished_job_is_an_ordinary_end_to_the_client(live):
    from siliconcompiler.remote.client.logs import LogTail
    client, app, job_id, logs = live
    app.config["SC_STORE"].execute(
        "UPDATE jobs SET state = 'completed' WHERE id = ?", (job_id,))
    assert LogTail(client, job_id).follow() == ""
