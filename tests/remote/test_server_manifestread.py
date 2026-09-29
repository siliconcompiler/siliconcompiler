import json
import os
import sys
import tarfile

from pathlib import Path

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from conftest import outcome, run_manifest, slug                         # noqa: E402
from test_server_jobs import (                                           # noqa: E402,F401
    FakeDispatcher, container_client, container_server, container_token, fake_unpack,
    registry, stage, submit, wants)
from test_server_sources_flow import read, wait_for                      # noqa: E402

from siliconcompiler.remote.server.staging import manifestread, sandbox          # noqa: E402


# Contract §1, *No server process holding credentials parses a manifest*: the
# read runs while the job stages, in a process of its own, and the server acts
# on its data summary alone. These run the real, contained subprocess where
# they are marked `real_read`; the rest of the suite reads in-process.


@pytest.fixture
def dispatcher(server):
    fake = FakeDispatcher()
    server.config["SC_JOBS"]._dispatcher = fake
    return fake


def submitted(server_client, key, token, archive):
    path, digest, size = archive
    job = stage(server_client, key, token, path, size)
    return job, outcome(server_client, key, token,
                        submit(server_client, key, token, job["id"], digest, size))


def a_manifest(nop_project, where) -> Path:
    '''The nop project's manifest in a tree of its own, as an upload expands.'''
    tree = Path(where) / nop_project.name / nop_project.option.get_jobname()
    tree.mkdir(parents=True, exist_ok=True)
    nop_project.write_manifest(str(tree / f"{nop_project.name}.pkg.json"))
    return tree


###########################
# No manifest is parsed in the server process
###########################

@pytest.mark.real_read
@pytest.mark.timeout(300)
def test_no_manifest_is_parsed_in_the_server_process(
        server, server_client, key, token, job_archive, monkeypatch):
    '''🔴 With SiliconCompiler's loader refusing in this process, a job goes
    from create through staging to a run that completes: the manifest was read
    in a process of its own, and the run loaded it in another.'''
    from siliconcompiler import Project

    archive = job_archive()

    def refuse(*args, **kwargs):
        raise AssertionError("a manifest was parsed in the server's own process")

    monkeypatch.setattr(Project, "from_manifest", staticmethod(refuse))

    job, response = submitted(server_client, key, token, archive)

    assert response.status_code == 202, response.get_json()
    assert wait_for(lambda: read(server_client, key, token, job["id"])["state"]
                    in ("completed", "failed"), seconds=240)
    assert read(server_client, key, token, job["id"])["state"] == "completed"

    # And the run's metrics, into the table the portal reads, as plain JSON.
    row = server.config["SC_STORE"].one(
        "SELECT records FROM job_nodes WHERE job_id = ? AND step = 'stepone'", (job["id"],))
    assert json.loads(row["records"])["status"] == "success"


@pytest.mark.real_read
def test_a_task_module_the_manifest_names_is_never_imported_by_the_read(
        server_client, key, token, job_archive, nop_project, dispatcher, tmp_path):
    '''The extracted tree is never on the read's path, and a task module that
    is not installed is looked up, not imported: refused, and nothing ran.'''
    marker = tmp_path / "imported"
    nop_project.get_flow().get_graph_node("stepone", "0").set(
        "taskmodule", "sc_uploaded_task/NamedTask")
    archive = job_archive(extra={"sc_uploaded_task.py": (
        f"open({str(marker)!r}, 'w').write('imported')\n").encode()})

    _, response = submitted(server_client, key, token, archive)

    assert (response.status_code, slug(response)) == (422, "software-unavailable")
    assert response.get_json()["reason"] == "unknown_class"
    assert not marker.exists()
    assert not dispatcher.submitted


###########################
# What the read is given, and what it is not
###########################

@pytest.mark.real_read
def test_the_read_holds_none_of_the_servers_variables(tmp_path, monkeypatch):
    '''An empty environment, its own HOME and working directory, stdin closed
    and no descriptor but the three: none of the server's variables reach it,
    and the upload is not on its path.'''
    monkeypatch.setenv("SC_SERVER_SECRET", "not for the read")
    tree = tmp_path / "root" / "gcd" / "job0"
    tree.mkdir(parents=True)
    probe = ("import json, os, sys; sys.stdout.write(json.dumps({"
             "'env': dict(os.environ), 'cwd': os.getcwd(), 'path': sys.path, "
             "'fds': sorted(os.listdir('/proc/self/fd')), "
             "'stdin': os.readlink('/proc/self/fd/0')}))")
    monkeypatch.setattr(sandbox, "_command", lambda request: [*sandbox._python(), "-c", probe])

    said = sandbox.run_read(manifestread.request(tree, "gcd", "job0"),
                            tmp_path / "root" / sandbox.READ_DIRNAME, timeout=60)

    home = str(tmp_path / "root" / sandbox.READ_DIRNAME / "home")
    assert "SC_SERVER_SECRET" not in said["env"]
    assert said["env"]["HOME"] == home and said["cwd"] == home
    assert set(said["env"]) <= {"HOME", "TMPDIR", "LC_ALL", "PYTHONNOUSERSITE",
                                "PYTHONDONTWRITEBYTECODE", "PYTHONPATH",
                                "SC_READ_CPU_SECONDS", "SC_READ_MEMORY_BYTES", "LC_CTYPE"}
    assert not any(str(tree) in entry for entry in said["path"])
    # 0, 1, 2, and the one listdir opened to answer.
    assert len(said["fds"]) == 4
    assert said["stdin"] == os.devnull


@pytest.mark.real_read
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="namespaces are Linux's")
def test_the_read_contains_itself_where_the_host_allows(tmp_path, nop_project):
    '''A real read, on a real manifest: its own network namespace where the
    kernel lets it have one, and limits it set on itself.'''
    achieved = sandbox.probe()
    tree = a_manifest(nop_project, tmp_path / "root")

    raw = sandbox.run_read(manifestread.request(tree, nop_project.name, "job0"),
                           tmp_path / "root" / sandbox.READ_DIRNAME, timeout=120)
    summary = manifestread.validate(raw)

    assert summary["outcome"] is None
    assert [(node["step"], node["index"]) for node in summary["nodes"]] == \
        [("stepone", "0"), ("steptwo", "0")]
    assert raw["contained"] == achieved
    assert raw["contained"]["limits"] is True


###########################
# The summary is untrusted input
###########################

def refused_for(server, server_client, key, token, job_archive, monkeypatch, raw):
    from siliconcompiler.remote.server.jobs import JobService

    monkeypatch.setattr(JobService, "_run_read", lambda self, job, root, asked: raw(asked))
    job, response = submitted(server_client, key, token, job_archive())
    return job, response


@pytest.mark.parametrize("damage", [
    lambda summary: dict(summary, nodes="every node"),
    lambda summary: dict(summary, summary=99),
    lambda summary: dict(summary, outcome={"type": "entitlement-denied", "reason": None}),
    lambda summary: dict(summary, flow="f" * (manifestread.MAX_NAME + 1)),
    lambda summary: dict(summary, values=[{"key": ["library"], "kind": "who", "origin": "x"}]),
], ids=["shape", "version", "outcome", "flow-length", "value"])
def test_a_summary_that_fails_its_shape_has_not_read_the_manifest(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch, damage):
    _, response = refused_for(server, server_client, key, token, job_archive, monkeypatch,
                              lambda asked: damage(manifestread.read(asked)))

    assert (response.status_code, slug(response)) == (422, "archive-rejected")
    assert response.get_json()["reason"] == "manifest_invalid"
    assert not dispatcher.submitted


def test_a_node_name_the_node_name_check_refuses_never_reaches_a_column(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    '''🔴 A step travels into a primary key, a path and a URL.'''
    def lying(asked):
        summary = manifestread.read(asked)
        summary["nodes"][0]["step"] = "../../etc"
        return summary

    job, response = refused_for(server, server_client, key, token, job_archive,
                                monkeypatch, lying)

    assert response.get_json()["reason"] == "manifest_invalid"
    assert not server.config["SC_STORE"].all(
        "SELECT step FROM job_nodes WHERE job_id = ?", (job["id"],))


def test_a_read_members_are_taken_by_name_and_shape(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    '''A lying outcome cannot write fields of the problem body.'''
    def lying(asked):
        summary = manifestread.read(asked)
        summary["outcome"] = {"type": "resource-unresolved", "reason": None,
                              "detail": "no PDK",
                              "members": {"resource_kind": "passwd", "status": 200,
                                          "type": "about:blank"}}
        return summary

    _, response = refused_for(server, server_client, key, token, job_archive,
                              monkeypatch, lying)

    body = response.get_json()
    assert (response.status_code, slug(response)) == (422, "resource-unresolved")
    assert body["resource_kind"] == "pdk"


@pytest.mark.real_read
def test_an_oversized_summary_has_not_read_the_manifest(
        server_client, key, token, job_archive, dispatcher, monkeypatch):
    monkeypatch.setattr(manifestread, "MAX_SUMMARY_BYTES", 100)

    _, response = submitted(server_client, key, token, job_archive())

    assert response.get_json()["reason"] == "manifest_invalid"
    assert "more than 100 bytes" in response.get_json()["detail"]


@pytest.mark.real_read
def test_a_read_past_its_time_limit_has_not_read_the_manifest(
        server, server_client, key, token, job_archive, dispatcher, monkeypatch):
    server.config["SC_CONFIG"]._values["manifest_read_timeout_seconds"] = 1
    monkeypatch.setattr(sandbox, "_command", lambda request: [
        *sandbox._python(), "-c", "import time; time.sleep(60)"])

    _, response = submitted(server_client, key, token, job_archive())

    assert (response.status_code, slug(response)) == (422, "archive-rejected")
    assert response.get_json()["reason"] == "manifest_invalid"
    assert "past its 1s limit" in response.get_json()["detail"]


def test_a_read_the_job_stops_waiting_for_is_killed(tmp_path, monkeypatch):
    '''A cancel while the manifest is read ends the read, as it ends a fetch.'''
    import time

    monkeypatch.setattr(sandbox, "_command", lambda request: [
        *sandbox._python(), "-c", "import time; time.sleep(60)"])
    started = time.monotonic()

    with pytest.raises(sandbox.Cancelled):
        sandbox.run_read({"tree": str(tmp_path)}, tmp_path / "read", timeout=60,
                         alive=lambda: time.monotonic() - started < 0.5)
    assert time.monotonic() - started < 10


###########################
# The checks the read makes
###########################

def test_a_manifest_for_another_job_name_is_declared_mismatch(
        server_client, key, token, job_archive, nop_project, dispatcher):
    '''The job name the job declared is the manifest's, or it is refused.'''
    nop_project.option.set_jobname("other")

    _, response = submitted(server_client, key, token, job_archive())

    assert (response.status_code, slug(response)) == (422, "declared-mismatch")
    assert "the manifest is gcd/other and the job is gcd/job0" in \
        response.get_json()["detail"]
    assert not dispatcher.submitted


def test_a_manifest_for_another_design_is_declared_mismatch(nop_project, tmp_path):
    '''The read compares the design the job declared with the manifest's.'''
    tree = a_manifest(nop_project, tmp_path / "root")
    (tree / "other.pkg.json").write_bytes((tree / "gcd.pkg.json").read_bytes())

    summary = manifestread.validate(manifestread.read(
        manifestread.request(tree, "other", "job0")))

    assert summary["outcome"]["type"] == "declared-mismatch"
    assert "the manifest is gcd/job0 and the job is other/job0" in \
        summary["outcome"]["detail"]


def test_a_project_with_no_pdk_where_it_takes_one_is_resource_unresolved(
        gcd_design, tmp_path):
    '''🔴 The PDK fails closed only where the class has a PDK setting.'''
    from siliconcompiler import ASIC

    project = ASIC(gcd_design)
    project.add_fileset("rtl")
    from siliconcompiler.flows.lintflow import LintFlow
    project.set_flow(LintFlow())
    project.option.set_jobname("job0")
    tree = a_manifest(project, tmp_path / "root")

    summary = manifestread.read(manifestread.request(tree, "gcd", "job0"))

    assert summary["outcome"]["type"] == "resource-unresolved"
    assert summary["outcome"]["members"] == {"resource_kind": "pdk"}


###########################
# The run loads the uploaded manifest
###########################

def test_the_run_loads_the_manifest_as_it_was_uploaded(
        server, server_client, key, token, job_archive, dispatcher):
    '''🔴 No server process rewrites it: the file the run is handed is the
    upload's, byte for byte, and the overrides are data beside it, applied by
    the run.'''
    path, digest, size = job_archive()
    with tarfile.open(path) as tar:
        uploaded = next(tar.extractfile(member).read() for member in tar.getmembers()
                        if member.name.lstrip("./") == "gcd.pkg.json")

    job, response = submitted(server_client, key, token, (path, digest, size))

    assert response.status_code == 202, response.get_json()
    handed = Path(dispatcher.submitted[0][2])
    assert handed.read_bytes() == uploaded

    ran = run_manifest(handed)
    user = server.config["SC_STORE"].one("SELECT user_id FROM jobs WHERE id = ?",
                                         (job["id"],))["user_id"]
    assert ran.option.get_builddir() == str(server.config["SC_JOBS"].job_root(user, job["id"]))
    assert ran.get("record", "remoteid") == job["id"]
    assert ran.option.get_remote() is False


def test_the_summary_is_kept_outside_what_an_upload_can_write(
        server, server_client, key, token, job_archive, dispatcher):
    job, response = submitted(server_client, key, token, job_archive())

    assert response.status_code == 202
    user = server.config["SC_STORE"].one("SELECT user_id FROM jobs WHERE id = ?",
                                         (job["id"],))["user_id"]
    root = server.config["SC_JOBS"].job_root(user, job["id"])
    from siliconcompiler.remote.server.running import runspec
    kept = json.loads((root / runspec.SUMMARY_FILENAME).read_text())
    assert manifestread.validate(kept)["flow"]
    # Above the tree the upload expanded into.
    assert (root / "gcd" / "job0").is_dir()
    assert not (root / "gcd" / "job0" / runspec.SUMMARY_FILENAME).exists()


###########################
# In the job's own image, where containers are configured
###########################

class ReadingDispatcher(FakeDispatcher):
    '''A cluster that runs the read it is handed, in this process, and says
    what it was asked to run it in.'''

    name = "slurm"

    def __init__(self):
        super().__init__()
        self.reads = []
        self.alive = False

    def submit_read(self, name, workdir, command, bundle, timeout, queue=None):
        self.reads.append({"command": command, "bundle": bundle, "timeout": timeout})
        asked = json.loads(command[-1])
        (Path(workdir) / "summary.json").write_text(json.dumps(manifestread.read(asked)))
        return f"read:{len(self.reads)}"


@pytest.mark.real_read
def test_with_containers_the_read_runs_in_a_bundle_of_the_jobs_own_image(  # noqa: F811
        container_server, container_client, key, container_token, job_archive,  # noqa: F811
        monkeypatch):
    '''On a cluster the read is a batch job in the job's framework image, with
    the extracted tree mounted read-only, nothing else bound, and a network
    namespace of its own (profile D63).'''
    from siliconcompiler.remote.server.software import images

    fake = ReadingDispatcher()
    container_server.config["SC_JOBS"]._dispatcher = fake
    monkeypatch.setattr(images, "stage_bundle", fake_unpack)

    path, digest, size = job_archive()
    job = stage(container_client, key, container_token, path, size,
                requires=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], digest, size)

    assert len(fake.reads) == 1 and fake.submitted
    spec = json.loads((Path(fake.reads[0]["bundle"]) / "config.json").read_text())
    binds = [entry for entry in spec["mounts"] if entry.get("type") == "none"]
    assert len(binds) == 1 and binds[0]["options"][-1] == "ro"
    assert binds[0]["source"].endswith(os.path.join("gcd", "job0"))
    assert {"type": "network"} in spec["linux"]["namespaces"]
    assert spec["root"]["readonly"] is True
    assert "siliconcompiler.remote.server.staging.manifestread" in fake.reads[0]["command"]


@pytest.mark.real_read
def test_with_containers_on_docker_the_read_runs_with_no_network(  # noqa: F811
        container_server, container_client, key, container_token, job_archive,  # noqa: F811
        monkeypatch):
    '''The docker daemon's own container: no network, the tree read-only.'''
    import docker

    ran = {}

    class Container:
        status = "exited"
        attrs = {"State": {"ExitCode": 0}}

        def reload(self):
            pass

        def logs(self, stdout=True, stderr=False):
            return json.dumps(manifestread.read(json.loads(ran["command"][-1]))).encode() \
                if stdout else b""

        def remove(self, force=False):
            ran["removed"] = True

    class Client:
        class containers:
            @staticmethod
            def run(image, command, **kwargs):
                ran.update(image=image, command=command, **kwargs)
                return Container()

    monkeypatch.setattr(docker, "from_env", lambda: Client())

    path, digest, size = job_archive()
    job = stage(container_client, key, container_token, path, size,
                requires=wants("0.38.0"))
    submit(container_client, key, container_token, job["id"], digest, size)

    assert ran["network_mode"] == "none" and ran["read_only"] is True
    assert [mount["mode"] for mount in ran["volumes"].values()] == ["ro"]
    assert ran["image"].endswith("@sha256:" + "a" * 64)
    assert ran["removed"]
