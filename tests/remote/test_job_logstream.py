import threading
import time

import pytest

from conftest import call, slug
from test_logs import frames


pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server import logstream                  # noqa: E402


# `GET /v1/jobs/{id}/logs` with no step and no index: every node's live log,
# merged into one stream. What is asserted is the three rules the merge needs,
# and the first is the one an implementation gets wrong -- the id is the JOB's.


###########################
# The merge, without a server
###########################

class Job:
    '''Two nodes' logs on disk, and the states a stream asks about.'''

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

    def finish(self):
        self.states = {node: "completed" for node in self.nodes}
        self.over = True

    def events(self, start=None, deadline=None):
        return logstream.job_events(
            self.nodes, self.path, node_states=lambda: dict(self.states),
            job_over=lambda: self.over,
            start=start or [0] * len(self.nodes),
            deadline=deadline or time.monotonic() + 30,
            artifact_id=lambda step, index: f"art-{step}")


def parse(chunks):
    class Body:
        def get_data(self, as_text=False):
            return b"".join(chunks).decode()

    return frames(Body())


def run_to_end(job, **kwargs):
    '''Consume a job stream whose nodes have all finished.'''
    return parse(list(job.events(**kwargs)))


def test_every_node_is_in_one_stream_and_says_which_it_is(tmp_path):
    '''✅ The event format already carried per-event coordinates; they only
    earn their place in a stream carrying several nodes.'''
    job = Job(tmp_path)
    job.write("place", "placing\n")
    job.write("route", "routing\n")
    job.states = {node: "completed" for node in job.nodes}

    events = run_to_end(job)
    logs = [(d["step"], d["text"]) for e, _, d in events if e == "log"]

    assert ("place", "placing\n") in logs
    assert ("route", "routing\n") in logs


def test_the_id_is_the_jobs_and_it_only_goes_up(tmp_path):
    '''🔴 The rule a merge gets wrong. A per-node offset handed back to a
    merged stream would resume every other node at a position not its own.'''
    job = Job(tmp_path)
    job.write("place", "a\n")
    job.write("route", "bb\n")
    job.write("place", "ccc\n")
    job.states = {node: "completed" for node in job.nodes}

    ids = [i for e, i, _ in run_to_end(job) if e == "log"]
    totals = [int(i.split("-")[0], 16) for i in ids]

    assert totals == sorted(totals) and len(set(totals)) == len(totals)
    # Every id names every node's position, not just the one that spoke.
    assert all(len(i.split("-")[1].split(".")) == 2 for i in ids)


def test_resuming_from_a_job_id_has_no_gap_and_no_repeat(tmp_path):
    job = Job(tmp_path)
    job.write("place", "p1\np2\n")
    job.write("route", "r1\n")

    # Read what is there, then hang up.
    first = []
    stream = job.events()
    for chunk in stream:
        first.append(chunk)
        if sum(c.startswith(b"event: log") for c in first) == 2:
            break
    stream.close()
    seen = parse(first)
    last = [i for e, i, _ in seen if e == "log"][-1]

    # More from both nodes, then they finish -- the job is still open, so the
    # reconnect drains them.
    job.write("place", "p3\n")
    job.write("route", "r2\n")
    job.states = {node: "completed" for node in job.nodes}

    start = logstream.resume_job(last, None, len(job.nodes))
    rest = run_to_end(job, start=start)

    def text(events, step):
        return "".join(d["text"] for e, _, d in events
                       if e == "log" and d["step"] == step)

    for step in ("place", "route"):
        assert text(seen, step) + text(rest, step) == job.path(step, "0").read_text()


def test_a_resume_after_the_job_ended_is_also_an_immediate_end(tmp_path):
    '''⚠️ The contract's rule, and the price of it: what the first
    connection had not read yet is not replayed once the job is over. The
    client has it from the archives, which is where a finished job's logs are.'''
    job = Job(tmp_path)
    job.write("place", "p1\n")
    job.finish()

    events = run_to_end(job, start=logstream.resume_job("0-0.0", None, 2))

    assert [e for e, _, _ in events] == ["end"]


def test_order_is_kept_within_a_node(tmp_path):
    job = Job(tmp_path)
    job.write("place", "".join(f"line {n}\n" for n in range(200)))
    job.states = {node: "completed" for node in job.nodes}

    place = "".join(d["text"] for e, _, d in run_to_end(job)
                    if e == "log" and d["step"] == "place")

    assert place == job.path("place", "0").read_text()


def test_each_node_names_its_archive_and_end_names_none(tmp_path):
    '''🔴 No single archive for a job, and every node has already named its
    own -- so a client that watched holds them all when `end` arrives.'''
    job = Job(tmp_path)
    job.finish()
    job.over = False     # the nodes are done; the job ends with them

    events = run_to_end(job)
    states = {(d["step"], d["index"]): d.get("artifact_id")
              for e, _, d in events if e == "node_state"}

    assert states == {("place", "0"): "art-place", ("route", "0"): "art-route"}
    assert events[-1][0] == "end"
    assert events[-1][2] == {"reason": "terminal"}


def test_a_job_already_over_ends_at_once_and_replays_nothing(tmp_path):
    '''⚠️ The late request and the race are one path: the client reads the
    listing for `kind=logs`.'''
    job = Job(tmp_path)
    job.write("place", "long finished\n")
    job.finish()

    events = run_to_end(job)

    assert [e for e, _, _ in events] == ["end"]
    assert events[0][2] == {"reason": "terminal"}


def test_a_node_that_never_ran_is_reported_and_ends_nothing(tmp_path):
    job = Job(tmp_path)
    job.states = {("place", "0"): "skipped", ("route", "0"): "running"}
    job.write("route", "still going\n")

    stream = job.events()
    got = []
    for chunk in stream:
        got.append(chunk)
        if b"node_state" in chunk:
            break
    stream.close()

    events = parse(got)
    assert ("node_state", {"step": "place", "index": "0", "state": "skipped",
                           "artifact_id": "art-place"}) in [(e, d) for e, _, d in events]
    assert not any(e == "end" for e, _, _ in events)


@pytest.mark.parametrize("given", [
    None, "not-an-id", "1a",               # a per-node id: a byte offset, no vector
    "5-2.3.0",                             # three nodes, and this job has two
    "9-2.3",                               # the total does not add up
])
def test_an_id_that_is_not_this_jobs_starts_from_the_beginning(given):
    '''A stream that replays is a nuisance; one that skips is a lost log.'''
    assert logstream.resume_job(given, None, 2) == [0, 0]


def test_a_good_id_resumes_each_node_at_its_own_place():
    assert logstream.resume_job("5-2.3", None, 2) == [2, 3]
    assert logstream.resume_job(None, "5-2.3", 2) == [2, 3]


###########################
# The endpoint
###########################

@pytest.fixture
def job(server, server_client, key, token):
    '''A running job with two nodes, both logging.'''
    from siliconcompiler.remote.server.ids import uuid7

    store = server.config["SC_STORE"]
    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]

    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
        (job_id, me))
    row = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    for step in ("place", "route"):
        store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                      "VALUES (?, ?, '0', 'running')", (job_id, step))
        log = server.config["SC_JOBS"].node_log_path(row, step, "0")
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"{step} says hello\n")
    return job_id


def end_job(server, job_id, state="completed"):
    store = server.config["SC_STORE"]
    store.execute("UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))
    store.execute("UPDATE jobs SET state = ? WHERE id = ?", (state, job_id))


def job_stream_url(server_client, key, token, job_id):
    response = call(server_client, key, "GET", f"/v1/jobs/{job_id}/logs", token)
    assert response.status_code == 303, response.get_json()
    return response.headers["Location"].split("http://localhost", 1)[1]


def test_no_coordinates_is_the_whole_job(server, server_client, key, token, job):
    target = job_stream_url(server_client, key, token, job)
    assert target.startswith(f"/stream/logs/{job}?")

    # Every node's nodes finish, then the job does.
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


def test_before_any_node_starts_it_is_not_ready(server, server_client, key,
                                                token, job):
    '''The same answer a node gives before it starts: transient.'''
    server.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'pending' WHERE job_id = ?", (job,))
    server.config["SC_STORE"].execute(
        "UPDATE jobs SET state = 'queued' WHERE id = ?", (job,))

    response = call(server_client, key, "GET", f"/v1/jobs/{job}/logs", token)

    assert response.status_code == 409
    assert slug(response) == "not-ready"
    assert response.get_json()["artifact_kind"] == "logs"
    assert response.headers["Retry-After"]


@pytest.mark.parametrize("state", ["completed", "failed", "cancelled"])
def test_a_finished_job_is_a_stream_that_ends_at_once(server, server_client, key,
                                                      token, job, state):
    '''⚠️ Deliberately not a refusal: it is the race case arriving late.'''
    end_job(server, job, state)

    events = frames(server_client.get(job_stream_url(server_client, key, token, job)))

    assert events == [("end", None, {"reason": "terminal"})]


@pytest.mark.parametrize("features,missing", [
    ([], "logs"),
    (["logs"], "logs.stream"),
    (["logs", "logs.stream"], "logs.stream.job"),
])
def test_the_refusal_names_the_broadest_missing_capability(
        server, server_client, key, token, job, features, missing):
    server.config["SC_CONFIG"]._values["features"] = features

    response = call(server_client, key, "GET", f"/v1/jobs/{job}/logs", token)

    assert response.status_code == 501
    assert slug(response) == "feature-unsupported"
    assert response.get_json()["feature"] == missing


def test_a_job_link_is_not_a_node_link(server, server_client, key, token, job):
    '''Their own signature prefixes: neither can be edited into the other.'''
    target = job_stream_url(server_client, key, token, job)
    query = target.split("?", 1)[1]

    assert server_client.get(f"/stream/logs/{job}/place/0?{query}").status_code == 400
    assert server_client.get(f"/stream/logs/{job}?expires=1&sig=x").status_code == 400


def test_the_job_stream_holds_one_slot(server, server_client, key, token, job):
    '''🔴 The point of it: a flow wider than `concurrent_log_streams` could
    not be watched in full one node at a time, and one connection can.'''
    server.config["SC_STREAMS"]._ceiling = 1
    end_job(server, job)
    # A slot held elsewhere is what makes the next one refused.
    owner = server.config["SC_STORE"].one(
        "SELECT user_id FROM jobs WHERE id = ?", (job,))["user_id"]
    assert server.config["SC_STREAMS"].acquire(owner)
    try:
        response = server_client.get(job_stream_url(server_client, key, token, job))
        assert response.status_code == 429
        assert response.get_json()["limit"] == "concurrent_log_streams"
    finally:
        server.config["SC_STREAMS"].release(owner)

    frames(server_client.get(job_stream_url(server_client, key, token, job)))
    assert server.config["SC_STREAMS"].held(owner) == 0


def test_the_job_stream_implies_the_others(tmp_path):
    '''🔴 Never advertised alone: a client reading it opens a job stream and
    falls back to per-node ones.'''
    import json
    from siliconcompiler.remote.server.config import Config

    (tmp_path / "config.json").write_text(json.dumps({"features": ["logs.stream.job"]}))
    with pytest.raises(ValueError, match="logs.stream.job without logs.stream"):
        Config.load(tmp_path)


###########################
# The client, over a real socket
###########################

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
    job_id = str(uuid7())
    store.execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk) VALUES (?, ?, 'running', 'gcd', 'job0', '{}', 'none')",
        (job_id, client.me()["id"]))
    row = store.one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    logs = {}
    for step in ("place", "route"):
        store.execute('INSERT INTO job_nodes (job_id, step, "index", state) '
                      "VALUES (?, ?, '0', 'running')", (job_id, step))
        logs[step] = app.config["SC_JOBS"].node_log_path(row, step, "0")
        logs[step].parent.mkdir(parents=True, exist_ok=True)
        logs[step].write_text("")

    try:
        yield client, app, job_id, logs
    finally:
        server.shutdown()
        thread.join(timeout=10)


def test_the_client_follows_the_whole_job_to_its_end(live):
    client, app, job_id, logs = live

    def run():
        for n in range(4):
            time.sleep(0.15)
            for step, log in logs.items():
                with open(log, "a") as f:
                    f.write(f"{step} {n}\n")
        time.sleep(0.2)
        store = app.config["SC_STORE"]
        store.execute("UPDATE job_nodes SET state = 'completed' WHERE job_id = ?",
                      (job_id,))
        store.execute("UPDATE jobs SET state = 'completed' WHERE id = ?", (job_id,))

    writer = threading.Thread(target=run)
    writer.start()
    try:
        text = client.tail_job(job_id)
    finally:
        writer.join()

    for step, log in logs.items():
        # Everything each node wrote, in its own order.
        assert [line for line in text.splitlines() if line.startswith(step)] == \
            log.read_text().splitlines()


def test_the_client_collects_every_nodes_archive_as_it_goes(live):
    from siliconcompiler.remote.client.logs import LogTail

    client, app, job_id, logs = live
    for log in logs.values():
        log.write_text("done\n")
    app.config["SC_STORE"].execute(
        "UPDATE job_nodes SET state = 'completed' WHERE job_id = ?", (job_id,))

    tail = LogTail(client, job_id)
    tail.follow()

    # The server indexes each log as its node's stream reaches the end.
    assert set(tail.artifact_ids) == {("place", "0"), ("route", "0")}


def test_a_finished_job_is_an_ordinary_end_to_the_client(live):
    client, app, job_id, logs = live
    app.config["SC_STORE"].execute(
        "UPDATE jobs SET state = 'completed' WHERE id = ?", (job_id,))

    assert client.tail_job(job_id) == ""
