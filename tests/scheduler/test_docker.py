import pytest

from siliconcompiler import Project, FlowgraphSchema, DesignSchema
from siliconcompiler.tools.builtin.nop import NOPTask

from siliconcompiler.scheduler import DockerSchedulerNode


@pytest.fixture
def project():
    flow = FlowgraphSchema("testflow")

    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")

    design = DesignSchema("testdesign")
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
