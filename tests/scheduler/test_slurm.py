import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Chip, Flow
from siliconcompiler.tools.builtin import nop

from siliconcompiler.scheduler.slurm import SlurmSchedulerNode


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
    with patch("uuid.uuid4") as job_name_call:
        class DummyUUID:
            hex = "thisisahash"
        job_name_call.return_value = DummyUUID
        node = SlurmSchedulerNode(chip, "stepone", "0")
        job_name_call.assert_called_once()
    assert node.jobhash == "thisisahash"


def test_init_with_id(chip):
    chip.set("record", "remoteid", "thisistheremoteid")
    with patch("uuid.uuid4") as job_name_call:
        class DummyUUID:
            pass
        job_name_call.return_value = DummyUUID
        node = SlurmSchedulerNode(chip, "stepone", "0")
        job_name_call.assert_not_called()
    assert node.jobhash == "thisistheremoteid"


def test_is_local(chip):
    node = SlurmSchedulerNode(chip, "stepone", "0")
    assert node.is_local is False


def test_get_configuration_directory(chip):
    assert os.path.basename(SlurmSchedulerNode.get_configuration_directory(chip)) == \
        "sc_configs"
    assert os.path.dirname(SlurmSchedulerNode.get_configuration_directory(chip)) == \
        chip.getworkdir()


def test_get_job_name():
    assert SlurmSchedulerNode.get_job_name("hash", "step", "index") == "hash_step_index"


def test_get_runtime_file_name():
    assert SlurmSchedulerNode.get_runtime_file_name("hash", "step", "index", "sh") == \
        "hash_step_index.sh"
