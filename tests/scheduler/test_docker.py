import docker
import os
import pytest
import sys

import os.path

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


@pytest.mark.skipif(sys.platform == 'win32', reason='posix volume mapping')
def test_run_stops_container_without_grace_period(project):
    """Teardown must not sit through the daemon's SIGTERM grace period.

    The container's PID 1 is an interactive shell that ignores SIGTERM, so a
    plain stop() costs the full 10s timeout on every node.
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

    container.stop.assert_called_once_with(timeout=0)


@patch('sys.platform', 'win32')
def test_mark_copy_win32(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = DockerSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set:
        assert node.mark_copy() is True
        sc_set.assert_called()
        assert sc_set.call_count == 2


@patch('sys.platform', 'linux')
def test_mark_copy_non_win32(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    node = DockerSchedulerNode(project, "steptwo", "0")
    with patch("siliconcompiler.schema.BaseSchema.set") as sc_set:
        assert node.mark_copy() is False
        sc_set.assert_not_called()


def test_check_required_paths(project):
    project.set("tool", "builtin", "task", "nop", "require",
                ["tool,builtin,task,nop,prescript", "tool,builtin,task,nop,refdir"],
                step="steptwo", index="0")

    assert DockerSchedulerNode(project, "steptwo", "0").check_required_paths() is True
