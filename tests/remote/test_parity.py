import os
import threading

import pytest

from siliconcompiler import Flowgraph, Project
from siliconcompiler.remote import Credentials
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir


pytest.importorskip("flask", reason="the server extra is not installed")


# 🔴 The parity milestone. Before it the new path does nothing a user wants;
# after it every remaining phase is additive.
#
# Both halves for real: a server on a real port, a real store, a real archive
# over a real socket, a real dispatch, and `project.run()` driving it through
# ClientScheduler. What it asserts is the gate -- that the build directory the
# run produced matches what the same design produces locally.
#
# It is the server's copy of the tree that is compared, because fetching results
# back to the client is the artifact endpoints, which are the next phase.


@pytest.fixture
def live_server():
    '''A server on an ephemeral port, in a thread of its own.

    A real socket rather than `app.test_client()`, and the difference is not
    cosmetic: the test client runs a handler on the calling thread, so it cannot
    see anything that is wrong with holding state per thread -- which is exactly
    what a sqlite connection is.
    '''
    from werkzeug.serving import make_server

    from siliconcompiler.remote.server.app import create_app

    app = create_app(os.path.abspath("datadir"), cluster="local")
    server = make_server("127.0.0.1", 0, app, threaded=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=10)


def build_project(gcd_design, builddir):
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
    return project


def tree(root):
    '''Every file under a directory, by relative path.'''
    found = set()
    for dirpath, _, files in os.walk(root):
        for name in files:
            found.add(os.path.relpath(os.path.join(dirpath, name), root))
    return found


def test_a_design_runs_to_completion_and_the_tree_matches(gcd_design, live_server):
    local = build_project(gcd_design, "local-build")
    local.run()
    local_tree = tree(jobdir(local))
    assert local_tree

    credentials = Credentials(os.path.abspath("sc-home/credentials"))
    credentials.update(address=live_server)

    remote = build_project(gcd_design, "remote-build")
    remote.option.set_credentials(os.path.abspath("sc-home/credentials"))
    remote.option.set_remote(True)
    remote.run()

    from siliconcompiler.remote import Client

    client = Client(Credentials(os.path.abspath("sc-home/credentials")))
    jobs = client.jobs()
    assert len(jobs) == 1

    job = jobs[0]
    assert job["state"] == "completed"
    assert job["terminal"] is True
    assert job["design"] == "gcd"
    assert job["jobname"] == "job0"
    assert job["flow"] == "nopflow"

    detail, _ = client.job(job["id"])
    assert detail["progress"] == {"total_count": 2, "completed_count": 2,
                                  "failed_count": 0}
    assert all(node["state"] == "completed" for node in detail["nodes"])
    assert all(node["terminal"] for node in detail["nodes"])
    assert detail["submitted_at"] and detail["started_at"] and detail["finished_at"]

    # 🔴 The gate: every file a local run produced, the remote run produced too.
    identity = client.me()
    root = os.path.join("datadir", "users", identity["id"], "builds", job["id"],
                        "gcd", "job0")
    assert local_tree <= tree(root), sorted(local_tree - tree(root))

    # 🔴 And now on THIS machine, which is what a user actually looks at. The
    # two differences are both deliberate: `inputs/` is copies of the upstream
    # node's outputs, which the caller has from the upstream node, and
    # sc_remote.pkg.json is the client's own handle for reconnecting.
    here = tree(jobdir(remote))
    missing = {name for name in local_tree - here
               if os.sep + "inputs" + os.sep not in os.sep + name}
    assert not missing, sorted(missing)
    # What the remote run has and a local one does not: its own handle for
    # reconnecting, and the log the server's own run wrote.
    #
    # 🔴 `remote-job.log` and not `job.log`: a remote run is still a
    # `Scheduler` run, so the local `job.log` is open and being appended to for
    # the whole of it, and downloading onto it would truncate a file this
    # process is still writing.
    extra = here - local_tree
    assert "sc_remote.pkg.json" in extra
    assert "remote-job.log" in extra
    assert all(name in ("sc_remote.pkg.json", "remote-job.log")
               or name.startswith("job.")
               for name in extra), sorted(extra)


def test_a_summary_works_after_a_remote_run(gcd_design, live_server):
    '''What the manifests are fetched FOR. The record, the metrics and the tool
    versions are in them and in nothing the poll loop saw, so a run whose
    results did not come back can report node states and no numbers.'''
    Credentials(os.path.abspath("sc-home/credentials")).update(address=live_server)

    remote = build_project(gcd_design, "remote-build")
    remote.option.set_credentials(os.path.abspath("sc-home/credentials"))
    remote.option.set_remote(True)
    history = remote.run()

    remote.summary()

    # Read off the history `run()` returns, which is where a LOCAL run leaves
    # them too: the live parameters are reset when a run ends.
    for step in ("stepone", "steptwo"):
        assert history.get("metric", "tasktime", step=step, index="0") is not None
        assert history.get("record", "status", step=step, index="0") == "success"


def test_one_nodes_log_comes_back_as_text(gcd_design, live_server):
    '''Endpoint 20 followed to its bytes. A log at rest IS an artifact, so
    this is the same machinery the listing uses with a different scope gate.'''
    Credentials(os.path.abspath("sc-home/credentials")).update(address=live_server)

    remote = build_project(gcd_design, "remote-build")
    remote.option.set_credentials(os.path.abspath("sc-home/credentials"))
    remote.option.set_remote(True)
    remote.run()

    from siliconcompiler.remote import Client

    client = Client(Credentials(os.path.abspath("sc-home/credentials")))
    job = client.jobs()[0]

    client.node_log(job["id"], "stepone", "0", "fetched.log")
    assert "stepone" in open("fetched.log").read()


def test_the_run_happens_inside_the_users_own_tree(gcd_design, live_server):
    '''Per user as well as per job -- build directory AND cache. Nothing a user
    writes shares a path with another user, which is what makes the tree
    single-owner and stops ccache and coursier creating directories the next
    user cannot write into.'''
    credentials = Credentials(os.path.abspath("sc-home/credentials"))
    credentials.update(address=live_server)

    remote = build_project(gcd_design, "remote-build")
    remote.option.set_credentials(os.path.abspath("sc-home/credentials"))
    remote.option.set_remote(True)
    remote.run()

    from siliconcompiler.remote import Client

    client = Client(Credentials(os.path.abspath("sc-home/credentials")))
    identity = client.me()
    user_root = os.path.join("datadir", "users", identity["id"])

    assert os.path.isdir(os.path.join(user_root, "builds"))
    assert os.path.isdir(os.path.join(user_root, "cache"))

    job = client.jobs()[0]
    manifest = os.path.join(user_root, "builds", job["id"], "gcd", "job0",
                            "gcd.pkg.json")
    ran = Project.from_manifest(filepath=manifest)

    # The seven settings, as the run actually saw them.
    assert ran.option.get_remote() is False          # without it the node resubmits
    assert ran.option.get_nodisplay() is True
    assert ran.get('option', 'nodashboard') is True
    assert ran.get('record', 'remoteid') == job["id"]
    assert os.path.abspath(ran.option.get_builddir()) == \
        os.path.abspath(os.path.join(user_root, "builds", job["id"]))
    assert os.path.abspath(ran.option.get_cachedir()) == \
        os.path.abspath(os.path.join(user_root, "cache"))


def test_an_unconfigured_client_refuses_before_it_packs_anything(gcd_design, monkeypatch):
    '''🔴 E4, and it matters more under v1: the three-call submit means there is
    more to waste. The test fails if the collection runs at all.'''
    from siliconcompiler.remote.client import run as run_module

    def explode(self):
        raise AssertionError("the job was packed before the server was checked")
    monkeypatch.setattr(run_module.RemoteRun, "_preprocess", explode)

    project = build_project(gcd_design, "remote-build")
    project.option.set_credentials(os.path.abspath("sc-home/credentials"))
    project.option.set_remote(True)

    with pytest.raises(RuntimeError) as raised:
        project.run()

    assert "server" in str(raised.value).lower()


###########################
# The CLI, against a live server
###########################

def run_cli(monkeypatch, *args):
    from siliconcompiler.apps import sc_remote

    monkeypatch.setattr("sys.argv", ["sc-remote", "-credentials",
                                     os.path.abspath("sc-home/credentials"),
                                     *args])
    return sc_remote.main()


@pytest.fixture
def submitted(gcd_design, live_server):
    '''A job that has been run, and the manifest that names it.'''
    Credentials(os.path.abspath("sc-home/credentials")).update(address=live_server)

    project = build_project(gcd_design, "remote-build")
    project.option.set_credentials(os.path.abspath("sc-home/credentials"))
    project.option.set_remote(True)
    project.run()

    return os.path.join(os.path.abspath("remote-build"), "gcd", "job0",
                        "sc_remote.pkg.json")


def test_a_bare_cfg_reports_the_jobs_status(monkeypatch, caplog, submitted):
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted) == 0

    assert "completed" in caplog.text


def test_the_manifest_is_written_before_the_upload(submitted):
    '''🔴 A user who interrupts a long run needs the job id, and interrupting it
    is exactly the case where the run never reached its end to write one.'''
    assert os.path.isfile(submitted)

    ran = Project.from_manifest(filepath=submitted)
    assert ran.get('record', 'remoteid')


def test_delete_through_the_cli(monkeypatch, caplog, submitted):
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-delete") == 0

    from siliconcompiler.remote import Client

    client = Client(Credentials(os.path.abspath("sc-home/credentials")))
    assert client.jobs() == []


def test_cancel_through_the_cli_is_an_answer_not_an_exception(
        monkeypatch, caplog, submitted):
    '''Cancelling a job that has already finished is still a 202 with the
    current object: the caller's intent is satisfied either way.'''
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-cancel") == 0

    assert "completed" in caplog.text


def test_reconnect_through_the_cli(monkeypatch, caplog, submitted):
    with caplog.at_level("INFO"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-reconnect") == 0


def test_tailing_a_node_through_the_cli(monkeypatch, capsys, submitted):
    '''`-tail` against a finished node reaches the archive by the same call a
    live tail uses, and the client tells them apart by what it was served.'''
    assert run_cli(monkeypatch, "-cfg", submitted, "-tail", "stepone/0") == 0

    assert "stepone" in capsys.readouterr().out


def test_tail_needs_a_step(monkeypatch, caplog, submitted):
    '''An index with no step names no node. (An empty -tail is indistinguishable
    from not passing it, so the reachable bad input is this one.)'''
    with caplog.at_level("ERROR"):
        assert run_cli(monkeypatch, "-cfg", submitted, "-tail", "/0") == 1

    assert "step" in caplog.text


def test_tail_defaults_the_index(monkeypatch, capsys, submitted):
    '''`-tail stepone` is the common case and means index 0.'''
    assert run_cli(monkeypatch, "-cfg", submitted, "-tail", "stepone") == 0

    assert "stepone" in capsys.readouterr().out
