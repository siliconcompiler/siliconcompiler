import os
import subprocess
import sys

from pathlib import Path

import pytest

from siliconcompiler import Design, Flowgraph, Project
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tool import Task, TaskExecutableNotFound
from siliconcompiler.tools._common.cocotb import cocotb_task
from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask
from siliconcompiler.tools.verilator.cocotb_compile import CocotbCompileTask


# The cocotb driver, on a machine that need not have cocotb: setup runs where
# a run is submitted from, and what needs cocotb -- the GPI bootstrap, the VPI
# library -- is the node's.


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


def test_importing_the_driver_imports_no_cocotb():
    code = ("import sys, siliconcompiler.tools.icarus.cocotb_exec, "
            "siliconcompiler.tools.verilator.cocotb_compile; "
            "print('cocotb_tools' in sys.modules or 'find_libpython' in sys.modules)")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)})

    assert done.stdout.strip() == "False", done.stderr


def test_setup_needs_no_cocotb_and_sets_no_gpi_users(project, monkeypatch, caplog):
    '''🔴 GPI_USERS names absolute paths into the Python and cocotb that run
    the node, so it is not set on the machine that sets the node up.'''
    monkeypatch.setattr(cocotb_task, "_cocotb", lambda: None)

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
    monkeypatch.setattr(cocotb_task, "_cocotb", lambda: None)

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
    monkeypatch.setattr(cocotb_task, "_cocotb", lambda: (_Config, _FindLibpython))

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        node.setup()
        assert "GPI_USERS" not in node.task.getkeys("env")
        env = node.task.get_runtime_environmental_variables()

    assert env["GPI_USERS"] == "/usr/lib/libpython3.so;/opt/cocotb/libs/libpygpi.so"
    assert env["PYGPI_PYTHON_BIN"] == sys.executable
    assert env["PATH"].split(os.pathsep)[0] == str(Path("/opt/cocotb/libs"))


def test_a_renamed_test_module_keeps_its_own_name(project, monkeypatch, tmp_path):
    '''Collection renames a file `<name>_<hash>.py`; the module is still
    imported, and reported, under its own name.'''
    renamed = tmp_path / "test_gcd_0123abcd.py"
    renamed.write_text("import cocotb\n")
    design = project.get("library", "gcd", field="schema")
    real = design.get_file
    monkeypatch.setattr(type(design), "get_file",
                        lambda self, fileset=None, filetype=None:
                        [str(renamed)] if filetype == "python" else
                        real(fileset=fileset, filetype=filetype))
    monkeypatch.setattr(cocotb_task, "_cocotb", lambda: None)

    node = SchedulerNode(project, "sim", "0")
    with node.runtime():
        node.setup()
        assert node.task.get("env", "COCOTB_TEST_MODULES") == "test_gcd"
        os.makedirs(node.task.nodeworkdir, exist_ok=True)
        node.task.pre_process()
        staged = os.path.join(node.task.nodeworkdir, "cocotb_modules")
        path = node.task.get_runtime_environmental_variables()["PYTHONPATH"]

    assert os.path.isfile(os.path.join(staged, "test_gcd.py"))
    assert path.split(os.pathsep)[0] == staged


def test_cocotb_is_declared_on_the_class():
    '''So a remote run names it without running setup, Verilator's compile
    step included, which runs none of the user's Python.'''
    assert Task.framework_distributions() == ()
    assert CocotbExecTask.framework_distributions() == ("cocotb",)
    assert CocotbCompileTask.framework_distributions() == ("cocotb",)
