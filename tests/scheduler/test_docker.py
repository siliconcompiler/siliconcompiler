import docker
import glob
import io
import json
import os
import pytest
import sys
import tarfile

import os.path

from pathlib import Path
from unittest.mock import MagicMock, patch

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.tools.builtin.nop import NOPTask

from siliconcompiler.scheduler import DockerSchedulerNode
from siliconcompiler import __version__, NodeStatus
from siliconcompiler.utils.paths import jobdir, workdir


@pytest.fixture
def docker_image(scroot):
    # Build image for test
    buildargs = {
        'SC_VERSION': __version__
    }
    scimage = os.getenv('SC_IMAGE', None)
    if scimage:
        buildargs['SC_IMAGE'] = scimage

    client = docker.from_env()
    image = client.images.build(
        path=scroot,
        buildargs=buildargs,
        dockerfile=f'{scroot}/setup/docker/sc_local_runner.docker')

    return image[0].id


@pytest.fixture
def project():
    flow = Flowgraph("testflow")

    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


def test_init(project):
    node = DockerSchedulerNode(project, "stepone", "0")
    assert node.queue.startswith(
        "ghcr.io/siliconcompiler/sc_runner:v")


def test_init_specify_queue(project):
    project.set("option", "scheduler", "queue", "docker:v1", step="stepone", index="0")
    node = DockerSchedulerNode(project, "stepone", "0")
    assert node.queue == "docker:v1"


def test_init_specify_env(project, monkeypatch):
    monkeypatch.setenv("SC_DOCKER_IMAGE", "image:v2")
    node = DockerSchedulerNode(project, "stepone", "0")
    assert node.queue == "image:v2"


@pytest.mark.docker
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.skipif(sys.platform != 'linux', reason='Not supported in testing')
def test_docker_run(docker_image, project):
    project.set('option', 'scheduler', 'name', 'docker')
    project.set('option', 'scheduler', 'queue', docker_image)
    project.set("option", "nodashboard", True)
    assert project.run()

    assert os.path.isfile(f'{jobdir(project)}/testdesign.pkg.json')
    assert os.path.isfile(
        f'{workdir(project, step="stepone", index="0")}/outputs/testdesign.pkg.json')
    assert os.path.isfile(
        f'{workdir(project, step="steptwo", index="0")}/outputs/testdesign.pkg.json')

    # assert "Running in docker container:" in output.out
    # assert output.out.count("Running in docker container:") == 2

    assert project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS


def test_run_streams_manifest_into_container(project):
    """The manifest is streamed into the container, never staged in the shared job directory,
    where parallel siblings could read it half-written.
    """

    node = DockerSchedulerNode(project, "stepone", "0")

    container = MagicMock()
    client = MagicMock()
    client.images.get.return_value = MagicMock(id="image-id")
    client.containers.run.return_value = container
    client.api.exec_create.return_value = {'Id': 'exec-id'}
    client.api.exec_start.return_value = [b'running\n']
    client.api.exec_inspect.return_value = {'ExitCode': 0}

    with patch('siliconcompiler.scheduler.docker.docker.from_env', return_value=client):
        node.run()

    # Nothing was staged on the host.
    assert not glob.glob(os.path.join(jobdir(project), '**', 'sc_docker*'), recursive=True)

    # The runner is pointed at the container-local path...
    cmd = client.api.exec_create.call_args.args[1]
    assert '-cfg /tmp/sc_manifest.json' in cmd

    # ...and the manifest actually got there, as a readable one-entry tar.
    dest, blob = container.put_archive.call_args.args
    assert dest == '/tmp'
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        members = tar.getmembers()
        assert [m.name for m in members] == ['sc_manifest.json']
        assert members[0].mode & 0o444
        assert json.loads(tar.extractfile(members[0]).read())


@pytest.mark.skipif(sys.platform == 'win32', reason='posix uid/gid mapping')
def test_run_passes_uid_and_gid(project):
    """The container runs as the host's uid, gid and supplementary groups, so build artifacts
    do not land on the host owned by root.
    """

    node = DockerSchedulerNode(project, "stepone", "0")

    client = MagicMock()
    client.images.get.return_value = MagicMock(id="image-id")
    client.api.exec_create.return_value = {'Id': 'exec-id'}
    client.api.exec_start.return_value = [b'running\n']
    client.api.exec_inspect.return_value = {'ExitCode': 0}

    with patch('siliconcompiler.scheduler.docker.docker.from_env', return_value=client):
        node.run()

    kwargs = client.containers.run.call_args.kwargs
    assert kwargs['user'] == f"{os.getuid()}:{os.getgid()}"
    # An explicit user drops supplementary groups unless they are handed back.
    assert kwargs['group_add'] == os.getgroups()


def test_a_task_container_is_given_email_json_and_nothing_else_of_sc(project, monkeypatch):
    """A node reads one file from ~/.sc, so that file is all it is given: nothing
    else there, the token store in ~/.sc/auth included, reaches a tool."""
    home = os.path.abspath(".sc")
    os.makedirs(os.path.join(home, "auth"))
    email = os.path.join(home, "email.json")
    with open(email, "w") as f:
        f.write("{}")
    monkeypatch.setattr("siliconcompiler.scheduler.docker.default_email_credentials_file",
                        lambda: email)

    node = DockerSchedulerNode(project, "stepone", "0")
    client = MagicMock()
    client.images.get.return_value = MagicMock(id="image-id")
    client.api.exec_create.return_value = {'Id': 'exec-id'}
    client.api.exec_start.return_value = [b'running\n']
    client.api.exec_inspect.return_value = {'ExitCode': 0}

    with patch('siliconcompiler.scheduler.docker.docker.from_env', return_value=client):
        node.run()

    volumes = client.containers.run.call_args.kwargs['volumes']
    assert f"{email}:/sc_home/.sc/email.json:ro" in volumes
    assert not any(volume.startswith(f"{home}:") for volume in volumes)


@pytest.mark.skipif(sys.platform == 'win32', reason='posix volume mapping')
def test_a_mount_holding_the_token_store_has_it_hidden(project, monkeypatch):
    """A directory mounted for an input, here the home the token store is in, gets an
    empty tmpfs over the store."""
    home = os.getcwd()
    monkeypatch.setattr(Path, "home", lambda: Path(home))
    os.makedirs(os.path.join(".sc", "auth"))
    with open("top.v", "w") as f:
        f.write("module top(); endmodule\n")
    project.design.add_file("top.v", fileset="rtl")

    node = DockerSchedulerNode(project, "stepone", "0")
    client = MagicMock()
    client.images.get.return_value = MagicMock(id="image-id")
    client.api.exec_create.return_value = {'Id': 'exec-id'}
    client.api.exec_start.return_value = [b'running\n']
    client.api.exec_inspect.return_value = {'ExitCode': 0}

    with patch('siliconcompiler.scheduler.docker.docker.from_env', return_value=client):
        node.run()

    kwargs = client.containers.run.call_args.kwargs
    assert f"{home}:{home}:rw" in kwargs["volumes"]
    assert kwargs["tmpfs"] == {os.path.join(home, ".sc", "auth"): "size=64k,mode=0700"}


@pytest.mark.skipif(sys.platform == 'win32', reason='posix volume mapping')
def test_run_stops_container_without_grace_period(project):
    """Teardown stops the container with no grace period, as its shell PID 1 ignores SIGTERM."""

    node = DockerSchedulerNode(project, "stepone", "0")

    container = MagicMock()
    client = MagicMock()
    client.images.get.return_value = MagicMock(id="image-id")
    client.containers.run.return_value = container
    client.api.exec_create.return_value = {'Id': 'exec-id'}
    client.api.exec_start.return_value = [b'running\n']
    client.api.exec_inspect.return_value = {'ExitCode': 0}

    with patch('siliconcompiler.scheduler.docker.docker.from_env', return_value=client):
        node.run()

    container.stop.assert_called_once_with(timeout=0)


PRESCRIPT = ("tool", "builtin", "task", "nop", "prescript")
REFDIR = ("tool", "builtin", "task", "nop", "refdir")


@patch('sys.platform', 'win32')
def test_collect_keys_win32(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = DockerSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set:
        assert node.collect_keys() == {PRESCRIPT, REFDIR}
        # Named, never marked: nothing is written into the project.
        sc_set.assert_not_called()


@patch('sys.platform', 'linux')
def test_collect_keys_non_win32(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = DockerSchedulerNode(project, "steptwo", "0")
    assert node.collect_keys() == set()


def test_check_required_paths(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    assert DockerSchedulerNode(project, "steptwo", "0").check_required_paths() is True
