import pytest

import os.path

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.tools.builtin.nop import NOPTask

from siliconcompiler.scheduler import SlurmSchedulerNode
from siliconcompiler.utils.paths import jobdir


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
    with patch("uuid.uuid4") as job_name_call:
        class DummyUUID:
            hex = "thisisahash"
        job_name_call.return_value = DummyUUID
        node = SlurmSchedulerNode(project, "stepone", "0")
        job_name_call.assert_called_once()
    assert node.jobhash == "thisisahash"


def test_init_with_id(project):
    project.set("record", "remoteid", "thisistheremoteid")
    with patch("uuid.uuid4") as job_name_call:
        class DummyUUID:
            pass
        job_name_call.return_value = DummyUUID
        node = SlurmSchedulerNode(project, "stepone", "0")
        job_name_call.assert_not_called()
    assert node.jobhash == "thisistheremoteid"


def test_is_local(project):
    node = SlurmSchedulerNode(project, "stepone", "0")
    assert node.is_local is False


def test_get_configuration_directory(project):
    assert os.path.basename(SlurmSchedulerNode.get_configuration_directory(project)) == \
        "sc_configs"
    assert os.path.dirname(SlurmSchedulerNode.get_configuration_directory(project)) == \
        jobdir(project)


def test_get_job_name():
    assert SlurmSchedulerNode.get_job_name("hash", "step", "index") == "hash_step_index"


def test_get_runtime_file_name():
    assert SlurmSchedulerNode.get_runtime_file_name("hash", "step", "index", "sh") == \
        "hash_step_index.sh"


@pytest.mark.eda
@pytest.mark.quick
def test_slurm_local_py(project):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    project.set('option', 'scheduler', 'name', 'slurm')

    # Run the project's build process synchronously.
    assert project.run()

    assert os.path.isfile('build/testdesign/job0/testdesign.pkg.json')
    assert os.path.isfile('build/testdesign/job0/stepone/0/outputs/testdesign.pkg.json')
    assert os.path.isfile('build/testdesign/job0/steptwo/0/outputs/testdesign.pkg.json')

    assert project.history("job0").get("record", "status", step="stepone", index="0") == \
        NodeStatus.SUCCESS
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
