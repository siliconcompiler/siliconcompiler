import os
import sys

from pathlib import Path
from types import SimpleNamespace

import pytest

from siliconcompiler import Design, Flowgraph, Project
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools._common.cocotb import cocotb_task
from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask


# The cocotb driver, on a machine that need not have cocotb: setup runs
# wherever a flow is configured, and what needs cocotb -- the GPI bootstrap,
# the VPI library -- is the node's.


@pytest.fixture
def project():
    with open("test_gcd.py", "w") as f:
        f.write("import cocotb\n")
    design = Design("gcd")
    design.set_dataroot("here", os.getcwd())
    with design.active_dataroot("here"), design.active_fileset("tb"):
        design.set_topmodule("gcd")
        design.add_file("test_gcd.py", filetype="python")

    project = Project(design)
    project.add_fileset("tb")
    flow = Flowgraph("cocotbflow")
    flow.node("sim", CocotbExecTask())
    project.set_flow(flow)
    return project


def test_setup_needs_no_cocotb_and_sets_no_gpi_users(project, monkeypatch, caplog):
    '''GPI_USERS names absolute paths into the Python and cocotb that run the
    node, so it is not set on the machine that sets the node up.'''
    monkeypatch.setattr(cocotb_task, "_has_cocotb", False)

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        assert node.setup()
        assert "GPI_USERS" not in node.task.getkeys("env")
        assert node.task.get("env", "COCOTB_TEST_MODULES") == "test_gcd"

    assert "Cocotb is not installed; this test will not be able to run." in caplog.text


def test_the_node_stops_before_it_runs_without_cocotb(project, monkeypatch):
    monkeypatch.setattr(cocotb_task, "_has_cocotb", False)

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        node.setup()
        with pytest.raises(RuntimeError, match=r"^Cocotb is not installed; cannot run test\.$"):
            node.task.pre_process()


class _Config:
    libs_dir = Path("/opt/cocotb/libs")

    @staticmethod
    def pygpi_entry_point():
        return "/opt/cocotb/libs/libpygpi.so"


class _FindLibpython:
    @staticmethod
    def find_libpython():
        return "/usr/lib/libpython3.so"


def test_the_node_computes_gpi_users_for_its_own_python(project, monkeypatch):
    '''Even where setup has cocotb, the manifest does not record GPI_USERS:
    the node computes it.'''
    monkeypatch.setattr(cocotb_task, "_has_cocotb", True)
    monkeypatch.setattr(cocotb_task, "cocotb_tools", SimpleNamespace(config=_Config),
                        raising=False)
    monkeypatch.setattr(cocotb_task, "find_libpython", _FindLibpython, raising=False)

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        node.setup()
        assert "GPI_USERS" not in node.task.getkeys("env")
        env = node.task.get_runtime_environmental_variables()

    assert env["GPI_USERS"] == "/usr/lib/libpython3.so;/opt/cocotb/libs/libpygpi.so"
    assert env["PYGPI_PYTHON_BIN"] == sys.executable
    assert env["PATH"].split(os.pathsep)[0] == str(Path("/opt/cocotb/libs"))
