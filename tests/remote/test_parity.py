import os
import time
import uuid

import pytest
import requests

from siliconcompiler import Flowgraph, Project
from siliconcompiler.remote import Client, Credentials
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir

from conftest import write_progress


pytest.importorskip("flask", reason="the server extra is not installed")


# The client and the server for real: a socket, the store, the archive, the
# dispatch of a run in its own process, and `project.run()` driving it.


def credentials():
    return os.path.abspath("sc-home/auth/remote.json")


def build_project(gcd_design, builddir, remote=False):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)

    project.option.set_nodisplay(True)
    project.option.set_quiet(True)
    project.option.set_nodashboard(True)
    project.option.set_jobname("job0")
    project.option.set_builddir(os.path.abspath(builddir))
    if remote:
        project.option.set_credentials(credentials())
        project.option.set_remote(True)
    return project


def tree(root):
    '''Every file under a directory, by relative path.'''
    return {os.path.relpath(os.path.join(dirpath, name), root)
            for dirpath, _, files in os.walk(root) for name in files}


@pytest.fixture
def ran(gcd_design, live_server):
    '''A remote run: the project and a client of the server it ran on.'''
    Credentials(credentials()).set_server(live_server)
    remote = build_project(gcd_design, "remote-build", remote=True)
    history = remote.run()
    return remote, history, Client(Credentials(credentials()))


@pytest.mark.timeout(90)
def test_a_remote_run_leaves_the_build_directory_a_local_run_does(gcd_design, ran):
    remote, history, client = ran
    local = build_project(gcd_design, "local-build")
    local.run()
    local_tree = tree(jobdir(local))

    job, = client.jobs()
    assert (job["state"], job["terminal"]) == ("completed", True)
    detail, _ = client.job(job["id"])
    assert detail["progress"] == {"total_count": 2, "completed_count": 2, "failed_count": 0,
                                  "skipped_count": 0, "cancelled_count": 0}

    # What the run wrote on the server, and what came home, less `inputs/`
    # (copies of upstream outputs the server does not send back).
    on_server = tree(os.path.join("sc-server", "users", client.me()["id"], "builds",
                                  job["id"], "gcd", "job0"))
    assert local_tree <= on_server, sorted(local_tree - on_server)
    here = tree(jobdir(remote))
    missing = {name for name in local_tree - here if os.sep + "inputs" + os.sep not in
               os.sep + name}
    assert not missing, sorted(missing)

    # Only what the client itself keeps: the job it ran as, and the server's log.
    extra = {name for name in here - local_tree if not name.startswith("job.")}
    assert {name for name in extra if os.path.basename(name) != "sc_remote_job.json"} == \
        {"remote-job.log"}

    for step in ("stepone", "steptwo"):
        assert history.get("record", "status", step=step, index="0") == "success"
        assert history.get("metric", "tasktime", step=step, index="0") is not None

    assert "stepone" in client.archived_log(job["id"], "stepone", "0")


def run_cli(monkeypatch, *args):
    from siliconcompiler.apps import sc_config

    monkeypatch.setenv("SC_AUTH_DIR", os.path.dirname(credentials()))
    monkeypatch.setattr("sys.argv", ["sc-config", "remote", *args])
    return sc_config.main()


@pytest.mark.timeout(60)
def test_the_cli_configures_shows_and_logs_out_of_a_live_server(
        monkeypatch, caplog, live_server):
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "configure", live_server) == 0
        assert run_cli(monkeypatch, "show", live_server) == 0
        assert "Server reports you as" in caplog.text
        assert run_cli(monkeypatch, "logout") == 0
    assert Credentials(credentials()).servers() == []


class Dropped:
    '''A stream response that fails after delivering its first log event.'''

    def __init__(self, response):
        self._response = response

    def __getattr__(self, name):
        return getattr(self._response, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._response.close()

    def iter_content(self, chunk_size):
        seen = b""
        for chunk in self._response.iter_content(chunk_size):
            seen += chunk
            yield chunk
            if b"event: log" in seen and seen.endswith(b"\n\n"):
                raise requests.ConnectionError("the connection dropped")


@pytest.mark.timeout(60)
def test_a_tail_resumes_after_a_dropped_connection_with_no_gap_and_no_repeat(
        monkeypatch, server, live_server, dispatcher):
    Credentials(credentials()).set_server(live_server)
    client = Client(Credentials(credentials()))
    user = client.me()["id"]

    job = {"id": str(uuid.uuid4()), "owner": {"id": user}}
    server.config["SC_STORE"].execute(
        "INSERT INTO jobs (id, user_id, design, jobname, state, scheduler_job_id, created_at) "
        "VALUES (?, ?, 'gcd', 'job0', 'running', 'fake:1', ?)", (job["id"], user, time.time()))
    server.config["SC_STORE"].execute(
        "INSERT INTO job_nodes (job_id, step, idx, state) VALUES (?, 'stepone', '0', 'running')",
        (job["id"],))
    node = server.config["SC_JOBS"].root(user, job["id"]) / "gcd" / "job0" / "stepone" / "0"
    node.mkdir(parents=True)
    write_progress(server, job, "running", {"stepone/0": "running"})
    log = node / "sc_stepone_0.log"
    log.write_text("one\ntwo\n")

    requests_made = []
    follow = client.follow_log

    def follow_log(job_id, step=None, index=None, last_event_id=None):
        requests_made.append(last_event_id)
        if len(requests_made) == 2:
            # Between the two streams: more output, and the node ends.
            with open(log, "a") as f:
                f.write("three\n")
            write_progress(server, job, "completed", {"stepone/0": "completed"},
                           finished_at=1010.0)
            dispatcher.alive = False
        response = follow(job_id, step, index, last_event_id)
        return Dropped(response) if len(requests_made) == 1 else response

    monkeypatch.setattr(client, "follow_log", follow_log)

    text = client.tail_log(job["id"], "stepone", "0")

    assert text == "one\ntwo\nthree\n"
    assert requests_made == [None, "8"]
