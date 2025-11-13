import logging
import pytest
import re
import sys

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


@pytest.mark.skipif(sys.platform != "linux",
                    reason="only works on linux, due to issues with patching")
def test_slurm_show_no_nodelog(project):
    # Inserting value into configuration
    project.option.scheduler.set_name("slurm")
    project.option.scheduler.set_queue("test_queue")

    # Add file handler to help
    project.logger.addHandler(logging.FileHandler("test.log"))

    class DummyPOpen:
        def wait(self):
            return

        returncode = 10

    # Run the project's build process synchronously.
    with patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode.assert_slurm") as assert_slurm, \
            patch("subprocess.Popen") as popen, \
            patch("siliconcompiler.schema_support.record.RecordSchema.record_python_packages"):
        popen.return_value = DummyPOpen()

        with pytest.raises(RuntimeError,
                           match=r"Run failed: Could not run final steps \(steptwo\) "
                                 r"due to errors in: stepone/0"):
            project.run()
        assert_slurm.assert_called_once()

    assert os.path.isfile('build/testdesign/job0/testdesign.pkg.json')

    project.logger.handlers.clear()

    # Collect from test.log
    with open("test.log") as f:
        caplog = f.read()

    assert "Slurm exited with a non-zero code (10)." in caplog
    assert re.search(r"Node log file: .*\/build\/testdesign\/job0\/sc_configs\/"
                     r"[0-9a-f]+_stepone_0\.log", caplog) is None


@pytest.mark.skipif(sys.platform != "linux",
                    reason="only works on linux, due to issues with patching")
def test_slurm_show_nodelog(project):
    # Inserting value into configuration
    project.option.scheduler.set_name("slurm")
    project.option.scheduler.set_queue("test_queue")

    # Add file handler to help
    project.logger.addHandler(logging.FileHandler("test.log"))

    class DummyPOpen:
        def wait(self):
            return

        returncode = 10

    def dummy_get_runtime_file_name(hash, step, index, ext):
        return f"thisfile.{ext}"

    # Run the project's build process synchronously.
    with patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode.assert_slurm") as assert_slurm, \
            patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode.get_runtime_file_name") \
            as get_runtime_file_name, \
            patch("siliconcompiler.scheduler.slurm.SlurmSchedulerNode."
                  "get_configuration_directory") as get_configuration_directory, \
            patch("subprocess.Popen") as popen, \
            patch("siliconcompiler.schema_support.record.RecordSchema.record_python_packages"):
        popen.return_value = DummyPOpen()
        get_configuration_directory.return_value = "."
        get_runtime_file_name.side_effect = dummy_get_runtime_file_name

        with open("thisfile.log", "w") as f:
            f.write("find this text in the log")

        with pytest.raises(RuntimeError,
                           match=r"Run failed: Could not run final steps \(steptwo\) "
                                 r"due to errors in: stepone/0"):
            project.run()
        assert_slurm.assert_called_once()

    assert os.path.isfile('build/testdesign/job0/testdesign.pkg.json')

    project.logger.handlers.clear()

    # Collect from test.log
    with open("test.log") as f:
        caplog = f.read()

    assert "find this text in the log" in caplog
    assert "Slurm exited with a non-zero code (10)." in caplog
    assert "Node log file: ./thisfile.log" in caplog


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
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
