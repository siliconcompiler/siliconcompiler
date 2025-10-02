import copy
import hashlib
import logging
import pathlib
import pytest
import os
import time

import os.path

from unittest.mock import patch, ANY

from siliconcompiler import Flowgraph
from siliconcompiler import ShowTask, ScreenshotTask
from siliconcompiler.schema_support.metric import MetricSchema
from siliconcompiler.schema_support.record import RecordSchema
from siliconcompiler import Task
from siliconcompiler import Design, Project
from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, SafeSchema
from siliconcompiler.schema.parameter import PerNode, Scope
from siliconcompiler.tool import TaskExecutableNotFound, TaskError, TaskTimeout
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.builtin.nop import NOPTask

import siliconcompiler.tool as dut_tool
from siliconcompiler.tool import shutil as imported_shutil
from siliconcompiler.tool import subprocess as imported_subprocess
from siliconcompiler.tool import os as imported_os
from siliconcompiler.tool import psutil as imported_psutil
from siliconcompiler.tool import resource as imported_resource


@pytest.fixture
def patch_psutil(monkeypatch):
    class Process:
        def __init__(*args, **kwargs):
            pass

        def memory_full_info(self):
            class Memory:
                uss = 2
            return Memory

        def children(*args, **kwargs):
            return [Process()]

        def terminate(*args, **kwargs):
            pass

        def kill(*args, **kwargs):
            pass

        def wait(*args, **kwargs):
            pass

    monkeypatch.setattr(imported_psutil, 'Process', Process)

    def drummy_wait_procs(*args, **kwargs):
        return None, [Process()]

    monkeypatch.setattr(imported_psutil, 'wait_procs', drummy_wait_procs)

    def drummy_virtual_memory():
        class Memory:
            percent = 91.21
        return Memory

    monkeypatch.setattr(imported_psutil, 'virtual_memory', drummy_virtual_memory)

    yield


@pytest.fixture
def running_project():
    class TestProject(Project):
        def __init__(self):
            super().__init__()

            design = Design("testdesign")
            with design.active_fileset("rtl"):
                design.set_topmodule("designtop")
            self.set_design(design)
            self.add_fileset("rtl")

            self._Project__logger = logging.getLogger()
            self.logger.setLevel(logging.INFO)

            flow = Flowgraph("testflow")
            flow.node("running", NOPTask())
            flow.node("notrunning", NOPTask())
            flow.edge("running", "notrunning")

            self.set_flow(flow)

        def get_nop(self) -> NOPTask:
            return self.get("tool", "builtin", "task", "nop", field="schema")

    return TestProject()


@pytest.fixture
def running_node(running_project):
    return SchedulerNode(running_project, "running", "0")


def test_tasktimeout_init():
    timeout = TaskTimeout("somemsg", timeout=5.5)
    assert timeout.timeout == 5.5
    assert timeout.args == ("somemsg",)


def test_init():
    tool = Task()
    assert tool.step is None
    assert tool.index is None
    assert tool.logger is None
    assert tool.project is None


def test_tool():
    with pytest.raises(NotImplementedError,
                       match="^tool name must be implemented by the child class$"):
        Task().tool()


def test_task():
    with pytest.raises(NotImplementedError,
                       match="^task name must be implemented by the child class$"):
        Task().task()


def test_task_name():
    class NameTask(Task):
        def task(self):
            return "thistask"
    task = NameTask()
    assert task.task() == "thistask"
    assert task.name == "thistask"


def test_runtime_invalid_type():
    with pytest.raises(TypeError, match="^node must be a scheduler node$"):
        with Task().runtime(BaseSchema()):
            pass


def test_runtime_step_override(running_project):
    with pytest.raises(RuntimeError, match="^step and index cannot be provided with node$"):
        with Task().runtime(SchedulerNode(running_project, "step", "index"), step="step"):
            pass


def test_runtime_index_override(running_project):
    with pytest.raises(RuntimeError, match="^step and index cannot be provided with node$"):
        with Task().runtime(SchedulerNode(running_project, "step", "index"), index="index"):
            pass


def test_set_runtime_invalid_flow(running_node):
    running_node.project.unset('option', 'flow')
    with pytest.raises(RuntimeError, match="^flow not specified$"):
        with Task().runtime(running_node):
            pass


def test_runtime(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.step == 'running'
        assert runtool.index == '0'
        assert runtool.node is running_node
        assert runtool.logger is running_node.project.logger
        assert runtool.project is running_node.project


def test_runtime_node_only(running_node):
    with running_node.task.runtime(None, 'running', '0') as runtool:
        assert runtool.step == 'running'
        assert runtool.index == '0'
        assert runtool.node is None
        assert runtool.logger is None
        assert runtool.project is None


def test_runtime_same_task(running_node):
    running1 = running_node.switch_node("notrunning", "0")
    with running_node.task.runtime(running_node) as runtool0, \
         running_node.task.runtime(running1) as runtool1:
        assert runtool0 is not runtool1
        assert runtool0.step == 'running'
        assert runtool0.index == '0'
        assert runtool0.node is running_node
        assert runtool0.logger is running_node.project.logger
        assert runtool0.project is running_node.project
        assert runtool1.step == 'notrunning'
        assert runtool1.index == '0'
        assert runtool1.node is running1
        assert runtool1.logger is running_node.project.logger
        assert runtool1.project is running_node.project

        assert runtool0.set("option", "tool0_opt")
        assert runtool1.set("option", "tool1_opt")

        assert runtool0.get("option") == ["tool0_opt"]
        assert runtool1.get("option") == ["tool1_opt"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == ["tool0_opt"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="notrunning", index="0") == ["tool1_opt"]


def test_runtime_different(running_node):
    with running_node.task.runtime(running_node.switch_node("notrunning", "0")) as \
            runtool:
        assert runtool.step == 'notrunning'
        assert runtool.index == '0'
        assert runtool.logger is running_node.project.logger
        assert runtool.project is running_node.project


def test_schema_access(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.project is running_node.project
        assert isinstance(runtool.schema_record, RecordSchema)
        assert isinstance(runtool.schema_metric, MetricSchema)
        assert isinstance(runtool.schema_flow, Flowgraph)
        assert isinstance(runtool.schema_flowruntime, RuntimeFlowgraph)


def test_design_name(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.design_name == "testdesign"


def test_design_topmodule(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.design_topmodule == "designtop"


def test_set(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set("option", "only_step_index")
        assert runtool.get("option") == ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="notrunning", index="0") == []
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == ["only_step_index"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="notrunning", index="0") == []


def test_set_step_index_only(running_node):
    with running_node.task.runtime(None, step="notrunning", index="0") as runtool:
        assert runtool.set("option", "only_step_index")
        assert runtool.get("option") == ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="notrunning", index="0") == \
            ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == []
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="notrunning", index="0") == ["only_step_index"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == []


def test_set_step_index_only_override(running_node):
    with running_node.task.runtime(None, step="notrunning", index="0") as runtool:
        assert runtool.set("option", "only_step_index", step="something", index="else")
        assert runtool.get("option", step="something", index="else") == ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="something", index="else") == \
            ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == []
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="something", index="else") == ["only_step_index"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == []


def test_add(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add("option", "only_step_index0")
        assert runtool.add("option", "only_step_index1")
        assert runtool.get("option") == ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == \
            ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="notrunning", index="0") == []
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == \
        ["only_step_index0", "only_step_index1"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="notrunning", index="0") == []


def test_add_step_index_only(running_node):
    with running_node.task.runtime(None, step="notrunning", index="0") as runtool:
        assert runtool.add("option", "only_step_index0")
        assert runtool.add("option", "only_step_index1")
        assert runtool.get("option") == ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="notrunning", index="0") == \
            ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == []
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="notrunning", index="0") == \
        ["only_step_index0", "only_step_index1"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == []


def test_add_step_index_only_override(running_node):
    with running_node.task.runtime(None, step="notrunning", index="0") as runtool:
        assert runtool.add("option", "only_step_index0", step="something", index="else")
        assert runtool.add("option", "only_step_index1", step="something", index="else")
        assert runtool.get("option", step="something", index="else") == \
            ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="something", index="else") == \
            ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == []
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="something", index="else") == \
        ["only_step_index0", "only_step_index1"]
    assert running_node.project.get("tool", "builtin", "task", "nop", "option",
                                    step="running", index="0") == []


def test_unset(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add("option", "only_step_index0")
        assert runtool.add("option", "only_step_index1")
        assert runtool.get("option") == ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == \
            ["only_step_index0", "only_step_index1"]
        runtool.unset("option")
        assert runtool.get("option") == []


def test_get_exe_empty(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_exe() is None


def test_get_exe_not_found(running_node):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'exe', 'testexe')
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(TaskExecutableNotFound, match="^testexe could not be found$"):
            runtool.get_exe()


def test_get_exe_found(running_node, monkeypatch):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'exe', 'testexe')

    def dummy_env(*args, **kwargs):
        assert "include_path" in kwargs
        assert kwargs["include_path"] is True
        return {"PATH": "search:this:path:set"}

    monkeypatch.setattr(running_node.task, 'get_runtime_environmental_variables', dummy_env)

    def dummy_which(*args, **kwargs):
        assert "path" in kwargs
        assert kwargs["path"] == "search:this:path:set"
        return "found/exe"

    monkeypatch.setattr(imported_shutil, 'which', dummy_which)
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_exe() == "found/exe"


def test_get_exe_version_no_vswitch(running_node):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'exe', 'testexe')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_exe_version() is None


def test_get_exe_version_no_exe(running_node):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'vswitch', '-version')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_exe_version() is None


def test_get_exe_version(running_node, monkeypatch, caplog):
    def parse_version(stdout):
        assert stdout == "myversion"
        return "1.0.0"
    monkeypatch.setattr(running_node.task, 'parse_version', parse_version)

    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'exe', 'testexe')
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_exe_version() == "1.0.0"
    assert "Tool 'exe' found with version '1.0.0' in directory 'found'" in caplog.text


def test_get_exe_version_not_implemented(running_node, monkeypatch):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'exe', 'testexe')
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(RuntimeError,
                           match=r"^builtin/nop does not implement parse_version\(\)$"):
            runtool.get_exe_version()


def test_get_exe_version_non_zero_return(running_node, monkeypatch, caplog):
    def parse_version(stdout):
        assert stdout == "myversion"
        return "1.0.0"
    monkeypatch.setattr(running_node.task, 'parse_version', parse_version)

    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'exe', 'testexe')
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 1
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_exe_version() == "1.0.0"

    assert "Version check on 'exe' ended with code 1" in caplog.text


def test_get_exe_version_internal_error(running_node, monkeypatch, caplog):
    def parse_version(stdout):
        raise ValueError("look for this match")
    monkeypatch.setattr(running_node.task, 'parse_version', parse_version)

    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^look for this match$"):
            runtool.get_exe_version()

    assert "builtin/nop failed to parse version string: myversion" in caplog.text


def test_check_exe_version_not_set(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version(None) is True


def test_check_exe_version_valid(running_node, caplog):
    pass

def test_check_exe_version_invalid(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version', '\!=1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('1.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 1.0.0, did not satisfy any version specifier set \!=1.0.0" in caplog.text

# ... remainder of file unchanged ...