import os
import threading

import pytest

from siliconcompiler import Flowgraph, Project
from siliconcompiler.remote import Client, Credentials
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir


pytest.importorskip("flask", reason="the server extra is not installed")


# 🔴 The parity milestone, both halves for real: a server on a real port, a real
# store, archive, socket and dispatch, and `project.run()` driving it. The gate
# is that a remote run's build directory matches a local run's.


@pytest.fixture
def live_server():
    '''A server on a real socket: the test client runs a handler on the
    calling thread, so it cannot see per-thread state such as sqlite's.'''
    from werkzeug.serving import make_server

    from siliconcompiler.remote.server.app import create_app

    app = create_app(os.path.abspath("datadir"), cluster="local")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    app.config["SC_PUBLIC_ORIGINS"] = [f"http://127.0.0.1:{server.server_port}"]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=10)


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


@pytest.fixture
def ran(gcd_design, live_server):
    '''A remote run: the project, the history `run()` returned, and a client.'''
    Credentials(credentials()).set_server(live_server)
    remote = build_project(gcd_design, "remote-build", remote=True)
    history = remote.run()
    return remote, history, Client(Credentials(credentials()))


def tree(root):
    '''Every file under a directory, by relative path.'''
    found = set()
    for dirpath, _, files in os.walk(root):
        for name in files:
            found.add(os.path.relpath(os.path.join(dirpath, name), root))
    return found


def test_a_design_runs_to_completion_and_the_tree_matches(gcd_design, ran):
    remote, history, client = ran
    local = build_project(gcd_design, "local-build")
    local.run()
    local_tree = tree(jobdir(local))
    assert local_tree

    jobs = client.jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["state"] == "completed"
    assert job["terminal"] is True
    assert (job["design"], job["jobname"], job["flow"]) == ("gcd", "job0", "nopflow")

    detail, _ = client.job(job["id"])
    assert detail["progress"] == {"total_count": 2, "completed_count": 2,
                                  "failed_count": 0, "skipped_count": 0,
                                  "cancelled_count": 0}
    assert all(node["state"] == "completed" for node in detail["nodes"])
    assert all(node["terminal"] for node in detail["nodes"])
    assert detail["submitted_at"] and detail["started_at"] and detail["finished_at"]

    # 🔴 The gate: every file a local run produced, the server's run produced.
    root = os.path.join("datadir", "users", client.me()["id"], "builds", job["id"],
                        "gcd", "job0")
    assert local_tree <= tree(root), sorted(local_tree - tree(root))

    # 🔴 And on THIS machine, less `inputs/` (copies of upstream outputs).
    here = tree(jobdir(remote))
    missing = {name for name in local_tree - here
               if os.sep + "inputs" + os.sep not in os.sep + name}
    assert not missing, sorted(missing)
    # Extra: the reconnect handle, the server's log as `remote-job.log` (`job.log`
    # is open), its staging record, and each directory's job as recorded here.
    extra = here - local_tree
    for name in ("sc_remote.pkg.json", "remote-job.log", "remote-staging.log",
                 "sc_remote_job.json"):
        assert name in extra
    assert all(name in ("sc_remote.pkg.json", "remote-job.log", "remote-staging.log")
               or os.path.basename(name) == "sc_remote_job.json"
               or name.startswith("job.")
               for name in extra), sorted(extra)

    # What the manifests are fetched FOR: a summary, read off run()'s history.
    remote.summary()
    for step in ("stepone", "steptwo"):
        assert history.get("metric", "tasktime", step=step, index="0") is not None
        assert history.get("record", "status", step=step, index="0") == "success"

    # Endpoint 20 followed to its bytes: a log at rest is an artifact.
    client.node_log(job["id"], "stepone", "0", "fetched.log")
    assert "stepone" in open("fetched.log").read()


def test_the_run_happens_inside_the_users_own_tree(ran):
    '''Per user and per job, build directory AND cache, so no user creates a
    directory the next cannot write into; and the settings the run saw.'''
    _, _, client = ran
    user_root = os.path.join("datadir", "users", client.me()["id"])

    assert os.path.isdir(os.path.join(user_root, "builds"))
    assert os.path.isdir(os.path.join(user_root, "cache"))

    job = client.jobs()[0]
    seen = Project.from_manifest(filepath=os.path.join(user_root, "builds", job["id"],
                                                       "gcd", "job0", "gcd.pkg.json"))

    assert seen.option.get_remote() is False          # without it the node resubmits
    assert seen.option.get_nodisplay() is True
    assert seen.get('option', 'nodashboard') is True
    assert seen.get('record', 'remoteid') == job["id"]
    assert os.path.abspath(seen.option.get_builddir()) == \
        os.path.abspath(os.path.join(user_root, "builds", job["id"]))
    assert os.path.abspath(seen.option.get_cachedir()) == \
        os.path.abspath(os.path.join(user_root, "cache"))


def test_an_unconfigured_client_refuses_before_it_packs_anything(gcd_design, monkeypatch):
    '''🔴 E4: a three-call submit has more to waste. Fails if collection runs.'''
    from siliconcompiler.remote.client import run as run_module

    def explode(self, *args, **kwargs):
        raise AssertionError("the job was packed before the server was checked")
    monkeypatch.setattr(run_module.RemoteRun, "_collect", explode)
    with pytest.raises(RuntimeError) as raised:
        build_project(gcd_design, "remote-build", remote=True).run()
    assert "server" in str(raised.value).lower()


###########################
# The CLI, against a live server
###########################

def run_cli(monkeypatch, *args):
    from siliconcompiler.apps import sc_remote
    monkeypatch.setattr("sys.argv", ["sc-remote", "-credentials", credentials(), *args])
    return sc_remote.main()


@pytest.fixture
def submitted(ran):
    '''The manifest that names the job.'''
    return os.path.join(jobdir(ran[0]), "sc_remote.pkg.json")


def test_status_reconnect_and_tail_through_the_cli(monkeypatch, capsys, caplog, submitted):
    '''🔴 The manifest naming the job is written before the upload. `-tail`
    reaches a finished node's archive; the index defaults to 0, a step is needed.'''
    assert Project.from_manifest(filepath=submitted).get('record', 'remoteid')

    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted) == 0
        assert "completed" in caplog.text
        assert run_cli(monkeypatch, "-cfg", submitted, "-reconnect") == 0

    for node in ("stepone/0", "stepone"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-tail", node) == 0
        assert "stepone" in capsys.readouterr().out
    caplog.clear()
    with caplog.at_level("ERROR"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-tail", "/0") == 1
    assert "step" in caplog.text


def test_delete_through_the_cli(monkeypatch, caplog, submitted):
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-delete") == 0
    assert Client(Credentials(credentials())).jobs() == []


def test_cancel_through_the_cli_is_an_answer_and_its_reason_is_held_to_300(
        monkeypatch, caplog, submitted):
    '''Cancelling a finished job is a 202 with the current object. `-reason` is
    for `-cancel`, refused here at 300 characters as the server would.'''
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-cancel") == 0
    assert "completed" in caplog.text
    assert run_cli(monkeypatch, "-cfg", submitted, "-cancel", "-reason", "x" * 301) == 1
    assert "at most 300 characters" in caplog.text
    assert run_cli(monkeypatch, "-cfg", submitted, "-cancel", "-reason", "wrong corner") == 0
    assert run_cli(monkeypatch, "-cfg", submitted, "-reason", "wrong corner") == 1


def test_a_rotated_key_logs_in_again_as_a_new_device(live_server, tmp_path):
    '''🔴 `sc-server` binds a subject to its first key: the old key revokes its
    own device, so the new one enrols rather than being refused.'''
    path = tmp_path / "sc-home" / "auth" / "remote.json"
    credentials = Credentials(path)
    credentials.set_server(live_server)
    client = Client(credentials)
    user = client.me()["id"]
    old, = [device["id"] for device in client.devices() if device["current"]]

    client.rotate_key()

    again = Client(Credentials(path))
    assert again.me()["id"] == user
    devices = again.devices()
    new, = [device["id"] for device in devices if device["current"]]
    assert new != old
    assert old not in [device["id"] for device in devices]
