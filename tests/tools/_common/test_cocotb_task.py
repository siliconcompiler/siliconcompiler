import os
import sys

from pathlib import Path
from types import SimpleNamespace

import pytest

from siliconcompiler import Design, Flowgraph, Project
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tool import TaskExecutableNotFound
from siliconcompiler.tools._common.cocotb import cocotb_task
from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask
from siliconcompiler.tools.verilator.cocotb_compile import CocotbCompileTask as \
    VerilatorCocotbCompileTask
from siliconcompiler.tools.verilator.cocotb_exec import CocotbExecTask as VerilatorCocotbExecTask


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


def test_the_tool_check_stops_the_run_without_cocotb(project, monkeypatch):
    '''The scheduler's tool check looks up each node's executable before any
    node runs, which is where a missing cocotb is reported. The environment it
    is looked up in has to build without cocotb for that to be reached.'''
    monkeypatch.setattr(cocotb_task, "_has_cocotb", False)

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        node.setup()
        with pytest.raises(TaskExecutableNotFound, match=r"^cocotb is not installed$"):
            node.get_exe_path()


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


def test_collected_test_module_keeps_its_name(cocotb_project, cocotb_installed):
    '''A cluster or server imports the collected copy of a test module, so it
    has to be importable there under the name cocotb is given.'''
    proj = cocotb_project(CocotbExecTask(), copy=True)

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get("env", "COCOTB_TEST_MODULES") == "test_mod"
        _, module_dirs = node.task._get_test_modules()

    collection = os.path.realpath(os.path.join("build", "tb", "job0", "sc_collected_files"))
    assert len(module_dirs) == 1
    assert module_dirs[0].startswith(collection + os.sep)
    assert os.path.isfile(os.path.join(module_dirs[0], "test_mod.py"))


def test_verilator_runtime_ld_library_path(cocotb_project):
    '''The compiled simulation's RUNPATH names the compile node's cocotb, so
    the node running it puts its own first.'''
    pytest.importorskip("cocotb_tools")

    proj = cocotb_project(VerilatorCocotbExecTask(), compile_task=VerilatorCocotbCompileTask())

    # The exec task takes its input from the compile task's outputs.
    compile_node = SchedulerNode(proj, "compile", "0")
    with compile_node.runtime():
        assert compile_node.setup() is True

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        assert node.setup() is True
        envs = node.task.get_runtime_environmental_variables()

    libs_dir, _, _ = cocotb_task.get_cocotb_config("verilator")
    assert envs["LD_LIBRARY_PATH"].split(os.pathsep)[0] == str(libs_dir)


@pytest.mark.parametrize("include_path", [True, False])
def test_runtime_pythonpath_forwards_caller(cocotb_project, monkeypatch, include_path):
    '''Packages reachable only through the caller's PYTHONPATH -- a checkout,
    an environment module -- stay importable by the testbench.'''
    pytest.importorskip("cocotb_tools")

    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(["/caller/one", "/caller/two"]))

    proj = cocotb_project(CocotbExecTask())

    node = SchedulerNode(proj, "simulate", "0")
    with node.runtime():
        assert node.setup() is True
        envs = node.task.get_runtime_environmental_variables(include_path=include_path)

    python_path = envs["PYTHONPATH"].split(os.pathsep)
    if include_path:
        # After the test module directories, so a testbench module is found first
        assert python_path == [os.path.abspath("."), "/caller/one", "/caller/two"]
    else:
        assert python_path == [os.path.abspath(".")]
