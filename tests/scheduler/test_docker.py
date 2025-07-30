import pytest

from siliconcompiler import Chip, Flow
from siliconcompiler.tools.builtin import nop

from siliconcompiler.scheduler import DockerSchedulerNode


@pytest.fixture
def chip():
    flow = Flow("testflow")

    flow.node("testflow", "stepone", nop)
    flow.node("testflow", "steptwo", nop)
    flow.edge("testflow", "stepone", "steptwo")

    chip = Chip("dummy")
    chip.use(flow)
    chip.set("option", "flow", "testflow")
    chip.set("tool", "builtin", "task", "nop", "threads", 1)

    return chip


def test_init(chip):
    node = DockerSchedulerNode(chip, "stepone", "0")
    assert node.queue.startswith(
        "ghcr.io/siliconcompiler/sc_runner:v")


def test_init_specify_queue(chip):
    chip.set("option", "scheduler", "queue", "docker:v1", step="stepone", index="0")
    node = DockerSchedulerNode(chip, "stepone", "0")
    assert node.queue == "docker:v1"


def test_init_specify_env(chip, monkeypatch):
    monkeypatch.setenv("SC_DOCKER_IMAGE", "image:v2")
    node = DockerSchedulerNode(chip, "stepone", "0")
    assert node.queue == "image:v2"
