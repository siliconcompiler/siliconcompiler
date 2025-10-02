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
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version', '==1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('1.0.0') is True
    assert caplog.text == ''


def test_check_exe_version_invalid(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version', '!=1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('1.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 1.0.0, did not satisfy any version specifier set !=1.0.0" in caplog.text


def test_check_exe_version_value_ge(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version', '>=1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('1.0.0') is True
    assert caplog.text == ""


def test_check_exe_version_value_compound(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version',
                                    ['>=1.0.0,!=2.0.0'])
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('2.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,!=2.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_fail(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version',
                                    ['>=1.0.0,<2.0.0', '>3.0.0'])
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('2.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,<2.0.0; >3.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_pass(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version',
                                    ['>=1.0.0,<2.0.0', '>3.0.0'])
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('3.0.1') is True
    assert caplog.text == ""


def test_check_exe_version_value_invalid_spec(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version', '1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('1.0.0') is True
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text


def test_check_exe_version_value_invalid_spec_fail(running_node, caplog):
    assert running_node.project.set('tool', 'builtin', 'task', 'nop', 'version', '1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('1.0.1') is False
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text
    assert "Found version 1.0.1, did not satisfy any version specifier set 1.0.0" in caplog.text


def test_check_exe_version_normalize_error(running_node, monkeypatch, caplog):
    def normalize_version(reported_version):
        assert reported_version == "myversion"
        raise ValueError("match this error")
    monkeypatch.setattr(running_node.task, 'normalize_version', normalize_version)

    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'version', '==1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^match this error$"):
            runtool.check_exe_version('myversion')
    assert "Unable to normalize version for builtin/nop: myversion" in caplog.text


def test_check_exe_version_normalize_pass(running_node, monkeypatch, caplog):
    def normalize_version(reported_version):
        return "1.0.0"
    monkeypatch.setattr(running_node.task, 'normalize_version', normalize_version)

    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'version', '==1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.check_exe_version('myversion') is True
    assert caplog.text == ""


def test_check_exe_version_normalize_error_spec(running_node, monkeypatch, caplog):
    def normalize_version(reported_version):
        if reported_version == "1.0.0":
            raise ValueError("match this error")
        return "1.0.0"
    monkeypatch.setattr(running_node.task, 'normalize_version', normalize_version)

    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'version', '==1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^match this error$"):
            runtool.check_exe_version('myversion')
    assert "Unable to normalize versions for builtin/nop: ==1.0.0" in caplog.text


def test_check_exe_version_normalize_invalid_version(running_node, monkeypatch, caplog):
    def normalize_version(reported_version):
        return "notvalid"
    monkeypatch.setattr(running_node.task, 'normalize_version', normalize_version)

    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'version', '==1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        runtool.check_exe_version('myversion') is False
    assert "Version notvalid reported by builtin/nop does not match standard" in caplog.text


def test_check_exe_version_normalize_invalid_spec_version(running_node, monkeypatch, caplog):
    def normalize_version(reported_version):
        if reported_version == "myversion":
            return "1.0.0"
        return "notvalid"
    monkeypatch.setattr(running_node.task, 'normalize_version', normalize_version)

    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'version', '==1.0.0')
    with running_node.task.runtime(running_node) as runtool:
        runtool.check_exe_version('myversion') is False
    assert "Version specifier set ==notvalid does not match standard" in caplog.text


def test_get_runtime_environmental_variables(running_node, monkeypatch):
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_runtime_environmental_variables() == {'PATH': 'this:path'}


def test_get_runtime_environmental_variables_no_path(running_node, monkeypatch):
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {}


def test_get_runtime_environmental_variables_envs(running_node, monkeypatch):
    running_node.project.set('option', 'env', 'CHECK', 'THIS')
    running_node.project.set('option', 'env', 'CHECKS', 'THAT')
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'licenseserver', 'ENV_LIC0',
                                    ('server0', 'server1'))
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'licenseserver', 'ENV_LIC1',
                                    ('server2', 'server3'))
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'env', 'CHECK', "helloworld")

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.setenv("LD_LIBRARY_PATH", "this:ld:path")

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {
            'CHECK': 'helloworld',
            'CHECKS': 'THAT',
            'ENV_LIC0': 'server0:server1',
            'ENV_LIC1': 'server2:server3'
        }

        assert runtool.get_runtime_environmental_variables() == {
            'CHECK': 'helloworld',
            'CHECKS': 'THAT',
            'ENV_LIC0': 'server0:server1',
            'ENV_LIC1': 'server2:server3',
            'PATH': 'this:path',
            'LD_LIBRARY_PATH': 'this:ld:path'
        }


def test_get_runtime_environmental_variables_tool_path(running_node, monkeypatch):
    os.makedirs('./testpath', exist_ok=True)
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'path', './testpath')

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    expect_path = os.path.abspath('./testpath') + os.pathsep + "this:path"

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {}
        assert runtool.get_runtime_environmental_variables() == {
            'PATH': expect_path
        }


def test_get_runtime_arguments(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_runtime_arguments() == []


def test_get_runtime_arguments_all(running_node, monkeypatch):
    with open("arg2.run", "w") as f:
        f.write("testfile")

    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option',
                                    ['--arg0', '--arg1'])
    assert running_node.project.set('tool', "builtin", 'task', "nop", 'script', 'arg2.run')

    with running_node.task.runtime(running_node) as runtool:
        def runtime_options():
            options = Task.runtime_options(runtool)
            options.append("--arg3")
            return options
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == [
            '--arg0',
            '--arg1',
            os.path.abspath("arg2.run"),
            '--arg3']


def test_get_runtime_arguments_no_return(running_node, monkeypatch):
    with running_node.task.runtime(running_node) as runtool:
        def runtime_options():
            pass

        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        with pytest.raises(RuntimeError, match=r"^runtime_options\(\) returned None$"):
            runtool.get_runtime_arguments()


def test_get_runtime_arguments_number(running_node, monkeypatch):
    with running_node.task.runtime(running_node) as runtool:
        def runtime_options():
            return 1

        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        with pytest.raises(RuntimeError, match=r"^runtime_options\(\) must return a list$"):
            runtool.get_runtime_arguments()


def test_get_runtime_different_types(running_node, monkeypatch):
    with running_node.task.runtime(running_node) as runtool:
        def runtime_options():
            return [
                1,
                None,
                1.0,
                "string",
                pathlib.Path("path")
            ]
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == [
            '1',
            'None',
            '1.0',
            'string',
            'path']


def test_get_runtime_different_types_relpath(running_node, monkeypatch):
    with running_node.task.runtime(running_node, relpath=".") as runtool:
        def runtime_options():
            return [
                1,
                None,
                1.0,
                "string",
                pathlib.Path("path")
            ]
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == [
            '1',
            'None',
            '1.0',
            'string',
            'path']


def test_get_runtime_arguments_all_relative(running_node, monkeypatch):
    with open("arg2.run", "w") as f:
        f.write("testfile")

    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option',
                                    ['--arg0', '--arg1'])
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')

    with running_node.task.runtime(running_node, relpath=os.getcwd()) as runtool:
        def runtime_options():
            options = Task.runtime_options(runtool)
            options.append("--arg3")
            return options
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == [
            '--arg0',
            '--arg1',
            "arg2.run",
            '--arg3']


def test_get_runtime_arguments_overwrite(running_node, monkeypatch):
    with open("arg2.run", "w") as f:
        f.write("testfile")

    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option',
                                    ['--arg0', '--arg1'])
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')

    with running_node.task.runtime(running_node) as runtool:
        def runtime_options():
            return ['--arg3']
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == ['--arg3']


def test_get_runtime_arguments_error(running_node, monkeypatch, caplog):
    with running_node.task.runtime(running_node) as runtool:
        def runtime_options():
            raise ValueError("match this error")
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)
        with pytest.raises(ValueError, match="^match this error$"):
            runtool.get_runtime_arguments()

    assert "Failed to get runtime options for builtin/nop" in caplog.text


def test_get_output_files(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set('output', ["file0", "file1"])
        assert runtool.get_output_files() == set(["file0", "file1"])


def test_parse_version_not_implemented():
    with pytest.raises(NotImplementedError,
                       match="^must be implemented by the implementation class$"):
        Task().parse_version("nothing")


def test_normalize_version():
    tool = Task()
    assert tool.normalize_version("nothing") == "nothing"
    assert tool.normalize_version(None) is None


def test_setup():
    tool = Task()
    assert tool.setup() is None


def test_pre_process():
    tool = Task()
    assert tool.pre_process() is None


def test_runtime_options(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.runtime_options() == []


def test_runtime_options_with_aruments(running_node):
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option',
                                    ['--arg0', '--arg1'])
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')
    with running_node.task.runtime(running_node) as runtool:
        with open("arg2.run", "w") as f:
            f.write("test")

        assert runtool.runtime_options() == [
            '--arg0',
            '--arg1',
            os.path.abspath("arg2.run")
        ]


def test_runtime_options_with_aruments_with_refdir(running_node):
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option',
                                    ['--arg0', '--arg1'])
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'refdir', 'refdir')
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')
    os.makedirs("refdir", exist_ok=True)
    with open("refdir/arg2.run", "w") as f:
        f.write("test")

    with running_node.task.runtime(running_node) as runtool:

        assert runtool.runtime_options() == [
            '--arg0',
            '--arg1',
            os.path.abspath("refdir/arg2.run")
        ]


def test_run_not_implemented():
    with pytest.raises(NotImplementedError,
                       match="^must be implemented by the implementation class$"):
        Task().run()


def test_post_process():
    tool = Task()
    assert tool.post_process() is None


def test_resetting_state_in_copy(running_node):
    tool = Task()
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.project is not None

        tool = copy.deepcopy(runtool)
        assert tool.project is None


def test_generate_replay_script(running_node, monkeypatch):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'exe', 'testexe')
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'vswitch', '-version')
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_node.task.runtime(running_node) as runtool:
        runtool.generate_replay_script('replay.sh', './')
        assert os.path.exists('replay.sh')
        assert os.access('replay.sh', os.X_OK)

        with open('replay.sh', 'r') as replay:
            replay_text = "\n".join(replay.read().splitlines())
        replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

    assert replay_hash == "d86d8d1a38c5acf8a8954670cb0f802c"


def test_generate_replay_script_no_path(running_node, monkeypatch):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'exe', 'testexe')
    assert running_node.project.set("tool", "builtin", 'task', 'nop', 'vswitch', '-version')
    assert running_node.project.set("tool", "builtin", 'task', "nop", 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_node.task.runtime(running_node) as runtool:
        runtool.generate_replay_script('replay.sh', './', include_path=False)
        assert os.path.exists('replay.sh')
        assert os.access('replay.sh', os.X_OK)

        with open('replay.sh', 'r') as replay:
            replay_text = "\n".join(replay.read().splitlines())
        replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

        assert replay_hash == "ecf2e9d93e49feb3ce734fc3185e7480"


def test_setup_work_directory():
    tool = Task()

    os.makedirs("testwork", exist_ok=True)

    assert os.path.isdir("testwork")
    assert os.listdir("testwork") == []

    tool.setup_work_directory("testwork")

    assert os.path.isdir("testwork/inputs")
    assert os.path.isdir("testwork/outputs")
    assert os.path.isdir("testwork/reports")
    assert set(os.listdir("testwork")) == set(["inputs", "outputs", "reports"])


def test_setup_work_directory_ensure_clean():
    tool = Task()

    os.makedirs("testwork", exist_ok=True)

    with open("testwork/dummyfile", 'w') as f:
        f.write("test")

    assert os.path.isdir("testwork")
    assert os.listdir("testwork") == ["dummyfile"]

    tool.setup_work_directory("testwork")

    assert os.path.isdir("testwork/inputs")
    assert os.path.isdir("testwork/outputs")
    assert os.path.isdir("testwork/reports")
    assert set(os.listdir("testwork")) == set(["inputs", "outputs", "reports"])


def test_setup_work_directory_ensure_keep():
    tool = Task()

    os.makedirs("testwork", exist_ok=True)

    with open("testwork/dummyfile", 'w') as f:
        f.write("test")

    assert os.path.isdir("testwork")
    assert os.listdir("testwork") == ["dummyfile"]

    tool.setup_work_directory("testwork", remove_exist=False)

    assert os.path.isdir("testwork/inputs")
    assert os.path.isdir("testwork/outputs")
    assert os.path.isdir("testwork/reports")
    assert set(os.listdir("testwork")) == set(["inputs", "outputs", "reports", "dummyfile"])


def test_write_task_manifest_none(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == []


@pytest.mark.parametrize("suffix", ("tcl", "json", "yaml"))
def test_write_task_manifest(running_node, suffix):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", suffix)
    with running_node.task.runtime(running_node) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == [f'sc_manifest.{suffix}']


def test_write_task_manifest_abspath(running_node):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")
    running_node.project.set("tool", "builtin", "task", "nop", "refdir", ".")
    with running_node.task.runtime(running_node) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']

    check = SafeSchema.from_manifest(filepath="sc_manifest.json")
    assert check.get("tool", "builtin", "task", "nop", "refdir") == \
        [pathlib.Path(os.path.abspath(".")).as_posix()]


def test_write_task_manifest_relative(running_node):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")
    assert running_node.project.set("tool", "builtin", "task", "nop", "refdir", ".")
    with running_node.task.runtime(running_node, relpath=os.getcwd()) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']

    check = SafeSchema.from_manifest(filepath="sc_manifest.json")
    assert check.get("tool", "builtin", "task", "nop", "refdir") == ["."]


def test_write_task_manifest_with_backup(running_node):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")
    with running_node.task.runtime(running_node) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']
        runtool.write_task_manifest('.')
        assert set(os.listdir()) == set(['sc_manifest.json', 'sc_manifest.json.bak'])


def test_write_task_manifest_without_backup(running_node):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")
    with running_node.task.runtime(running_node) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']
        runtool.write_task_manifest('.', backup=False)
        assert os.listdir() == ['sc_manifest.json']


@pytest.mark.parametrize("exitcode", [0, 1])
def test_run_task(running_node, exitcode, monkeypatch):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = exitcode

            def poll(self):
                return self.returncode
        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    assert running_node.project.get("record", "toolargs", step="running", index="0") is None
    assert running_node.project.get("record", "toolexitcode", step="running", index="0") is None
    assert running_node.project.get("metric", "exetime", step="running", index="0") is None
    assert running_node.project.get("metric", "memory", step="running", index="0") is None

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == exitcode

    assert running_node.project.get("record", "toolargs", step="running", index="0") == ""
    assert running_node.project.get("record", "toolexitcode", step="running", index="0") == exitcode
    assert running_node.project.get("metric", "exetime", step="running", index="0") >= 0
    assert running_node.project.get("metric", "memory", step="running", index="0") >= 0


def test_run_task_failed_popen(running_node, monkeypatch):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_popen(*args, **kwargs):
        raise RuntimeError("something bad happened")
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(TaskError, match="^Unable to start found/exe: something bad happened$"):
            runtool.run_task('.', False, "info", False, None, None)


@pytest.mark.parametrize("nice", [-5, 0, 5])
def test_run_task_nice(running_node, nice, monkeypatch):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_nice(level):
        assert level == nice
    if hasattr(imported_os, 'nice'):
        monkeypatch.setattr(imported_os, 'nice', dummy_nice)

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        if hasattr(imported_os, 'nice'):
            assert kwargs["preexec_fn"] is not None
            kwargs["preexec_fn"]()
        else:
            assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 0

            def poll(self):
                return self.returncode
        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.run_task('.', False, "info", False, nice, None) == 0


def test_run_task_timeout(running_node, monkeypatch, patch_psutil):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            pid = 1

            def poll(self):
                time.sleep(5)
                return None

            def wait(*args, **kwargs):
                pass

        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(TaskTimeout, match="^$"):
            runtool.run_task('.', False, "info", False, None, 2)


def test_run_task_memory_limit(running_node, monkeypatch, patch_psutil, caplog):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 0
            pid = 1

            call_count = 0

            def poll(self):
                self.call_count += 1
                if self.call_count > 2:
                    return self.returncode
                return None

        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == 0

    assert "Current system memory usage is 91.2%" in caplog.text


@pytest.mark.parametrize("error", [PermissionError, imported_psutil.Error])
def test_run_task_exceptions_loop(running_node, monkeypatch, patch_psutil, error):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 0
            pid = 1

            call_count = 0

            def poll(self):
                self.call_count += 1
                if self.call_count > 2:
                    return self.returncode
                return None

        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_virtual_memory():
        raise error
    monkeypatch.setattr(imported_psutil, 'virtual_memory', dummy_virtual_memory)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == 0


def test_run_task_contl_c(running_node, monkeypatch, patch_psutil, caplog):
    assert running_node.project.set("tool", "builtin", 'task', 'nop', "format", "json")

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 0
            pid = 1

            call_count = 0

            def poll(self):
                self.call_count += 1
                if self.call_count > 2:
                    return self.returncode
                return None

            def wait(*args, **kwargs):
                pass

        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_virtual_memory():
        raise KeyboardInterrupt
    monkeypatch.setattr(imported_psutil, 'virtual_memory', dummy_virtual_memory)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(TaskError, match="^$"):
            runtool.run_task('.', False, "info", False, None, None)

    assert "Received ctrl-c." in caplog.text


def test_run_task_breakpoint_valid(running_node, monkeypatch):
    pytest.importorskip('pty')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    with running_node.task.runtime(running_node) as runtool:
        with patch("pty.spawn", autospec=True) as spawn:
            spawn.return_value = 1
            assert runtool.run_task('.', False, "info", True, None, None) == 1
            spawn.assert_called_once()
            spawn.assert_called_with(["found/exe"], ANY)


def test_run_task_breakpoint_not_used(running_node, monkeypatch):
    pytest.importorskip('pty')
    monkeypatch.setattr(dut_tool, "pty", None)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_node.task, 'get_exe', dummy_get_exe)

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 1

            def poll(self):
                return self.returncode
        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    with running_node.task.runtime(running_node) as runtool:
        with patch("pty.spawn", autospec=True) as spawn:
            spawn.return_value = 1
            assert runtool.run_task('.', False, "info", True, None, None) == 1
            spawn.assert_not_called()


def test_run_task_run(running_node):
    class RunTool(NOPTask):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    assert isinstance(running_node.task, NOPTask)
    EditableSchema(running_node.project.get("tool", "builtin", "task", field="schema")).insert(
        "nop", RunTool(), clobber=True)

    running_node = running_node.switch_node("running", "0")
    assert isinstance(running_node.task, RunTool)

    with running_node.task.runtime(running_node) as runtool:
        assert isinstance(runtool, RunTool)
        assert runtool.run_task('.', False, "info", True, None, None) == 1
        assert runtool.call_count == 1


def test_run_task_run_error(running_node):
    class RunTool(NOPTask):
        call_count = 0

        def run(self):
            self.call_count += 1
            raise ValueError("run error")

    assert isinstance(running_node.task, NOPTask)
    EditableSchema(running_node.project.get("tool", "builtin", "task", field="schema")).insert(
        "nop", RunTool(), clobber=True)

    running_node = running_node.switch_node("running", "0")
    assert isinstance(running_node.task, RunTool)

    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^run error$"):
            runtool.run_task('.', False, "info", True, None, None)
        assert runtool.call_count == 1


@pytest.mark.skipif(imported_resource is None, reason="resource not available")
def test_run_task_run_failed_resource(running_node, monkeypatch):
    class RunTool(NOPTask):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    assert isinstance(running_node.task, NOPTask)
    EditableSchema(running_node.project.get("tool", "builtin", "task", field="schema")).insert(
        "nop", RunTool(), clobber=True)

    def dummy_resource(*args, **kwargs):
        raise PermissionError
    monkeypatch.setattr(imported_resource, "getrusage", dummy_resource)

    running_node = running_node.switch_node("running", "0")
    assert isinstance(running_node.task, RunTool)

    with running_node.task.runtime(running_node) as runtool:
        assert runtool.run_task('.', False, "info", True, None, None) == 1
        assert runtool.call_count == 1


def test_select_input_nodes_entry(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.select_input_nodes() == []


def test_select_input_nodes_entry_has_input(running_node):
    with running_node.task.runtime(running_node.switch_node("notrunning", "0")) as \
            runtool:
        assert runtool.select_input_nodes() == [('running', '0')]


def test_task_add_parameter():
    task = Task()

    assert task.getkeys("var") == tuple()

    assert isinstance(task.add_parameter("teststr", "str", "long form help"), Parameter)
    assert isinstance(task.add_parameter("testbool", "bool", "long form help"), Parameter)
    assert isinstance(task.add_parameter("testlist", "[str]", "long form help"), Parameter)

    assert task.getkeys("var") == ("testbool", "testlist", "teststr")

    assert task.get("var", "teststr") is None
    assert task.get("var", "testlist") == []
    assert task.get("var", "testbool") is False

    assert task.get("var", "teststr", field="help") == "long form help"
    assert task.get("var", "testlist", field="help") == "long form help"
    assert task.get("var", "testbool", field="help") == "long form help"

    assert task.get("var", "teststr", field="shorthelp") == "long form help"
    assert task.get("var", "testlist", field="shorthelp") == "long form help"
    assert task.get("var", "testbool", field="shorthelp") == "long form help"

    assert task.get("var", "teststr", field="type") == "str"
    assert task.get("var", "testlist", field="type") == "[str]"
    assert task.get("var", "testbool", field="type") == "bool"

    assert task.get("var", "teststr", field="scope") == Scope.JOB
    assert task.get("var", "testlist", field="scope") == Scope.JOB
    assert task.get("var", "testbool", field="scope") == Scope.JOB

    assert task.get("var", "teststr", field="pernode") == PerNode.OPTIONAL
    assert task.get("var", "testlist", field="pernode") == PerNode.OPTIONAL
    assert task.get("var", "testbool", field="pernode") == PerNode.OPTIONAL


def test_task_add_parameter_recovered():
    task = Task()
    assert task.add_parameter("teststr", "str", "long form help")
    assert task.add_parameter("testbool", "bool", "long form help")
    assert task.add_parameter("testlist", "[str]", "long form help")

    assert task.getkeys("var") == ("testbool", "testlist", "teststr")

    new_task = Task.from_manifest(name="newtask", cfg=task.getdict())

    assert new_task.getkeys("var") == ("testbool", "testlist", "teststr")

    assert new_task.get("var", "teststr") is None
    assert new_task.get("var", "testlist") == []
    assert new_task.get("var", "testbool") is False

    assert new_task.get("var", "teststr", field="help") == "long form help"
    assert new_task.get("var", "testlist", field="help") == "long form help"
    assert new_task.get("var", "testbool", field="help") == "long form help"

    assert new_task.get("var", "teststr", field="shorthelp") == "long form help"
    assert new_task.get("var", "testlist", field="shorthelp") == "long form help"
    assert new_task.get("var", "testbool", field="shorthelp") == "long form help"

    assert new_task.get("var", "teststr", field="type") == "str"
    assert new_task.get("var", "testlist", field="type") == "[str]"
    assert new_task.get("var", "testbool", field="type") == "bool"

    assert new_task.get("var", "teststr", field="scope") == Scope.JOB
    assert new_task.get("var", "testlist", field="scope") == Scope.JOB
    assert new_task.get("var", "testbool", field="scope") == Scope.JOB

    assert new_task.get("var", "teststr", field="pernode") == PerNode.OPTIONAL
    assert new_task.get("var", "testlist", field="pernode") == PerNode.OPTIONAL
    assert new_task.get("var", "testbool", field="pernode") == PerNode.OPTIONAL


def test_task_add_parameter_defvalue():
    task = Task()

    task.add_parameter("teststr", "str", "long form help", defvalue="checkthis")

    assert task.get("var", "teststr") == "checkthis"


@pytest.mark.parametrize("filename,step,index,expect", [
    ("noext", "instep", "inindex", "noext.instepinindex"),
    ("file.ext0", "instep", "inindex", "file.instepinindex.ext0"),
    ("file.ext0.ext1.ext2", "instep", "inindex", "file.instepinindex.ext0.ext1.ext2"),
])
def test_compute_input_file_node_name(filename, step, index, expect):
    assert Task().compute_input_file_node_name(filename, step, index) == expect


def test_get_files_from_input_nodes_entry(running_node):
    with running_node.task.runtime(running_node.switch_node("running", "0")) as runtool:
        assert runtool.get_files_from_input_nodes() == {}


def test_get_files_from_input_nodes_end(running_node):
    running_node.project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                             step="running", index="0")

    with running_node.task.runtime(running_node.switch_node("notrunning", "0")) as \
            runtool:
        assert runtool.get_files_from_input_nodes() == {
            'file0.txt': [('running', '0')]
        }


def test_get_files_from_input_nodes_skipped(running_node):
    flow = running_node.project.get("flowgraph", "testflow", field="schema")
    flow.node("lastnode", NOPTask())
    flow.edge("notrunning", "lastnode")

    running_node.project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                             step="running", index="0")
    running_node.project.set("record", "status", "skipped", step="notrunning", index="0")

    with running_node.task.runtime(running_node.switch_node("lastnode", "0")) as runtool:
        assert runtool.get_files_from_input_nodes() == {
            'file0.txt': [('running', '0')]
        }


def test_get_files_from_input_nodes_multiple(running_node):
    flow = running_node.project.get("flowgraph", "testflow", field="schema")
    flow.node("firstnode", NOPTask())
    flow.edge("firstnode", "notrunning")

    running_node.project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                             step="running", index="0")
    running_node.project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                             step="firstnode", index="0")
    running_node.project.add("tool", "builtin", "task", "nop", "output", "file1.txt",
                             step="firstnode", index="0")

    with running_node.task.runtime(running_node.switch_node("notrunning", "0")) as \
            runtool:
        assert runtool.get_files_from_input_nodes() == {
            'file0.txt': [('running', '0'), ('firstnode', '0')],
            'file1.txt': [('firstnode', '0')]
        }


def test_add_required_key(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_required_key("this", "key", "is", "required")
        assert runtool.get("require") == ["this,key,is,required"]
        assert runtool.add_required_key("this", "key", "is", "required", "too")
        assert runtool.get("require") == ["this,key,is,required", "this,key,is,required,too"]


def test_add_required_key_obj(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_required_key(running_node.task, "this", "key", "is", "required")
        assert runtool.get("require") == ["tool,builtin,task,nop,this,key,is,required"]
        assert runtool.add_required_key(runtool, "this", "key", "is", "required", "too")
        assert runtool.get("require") == ["tool,builtin,task,nop,this,key,is,required",
                                          "tool,builtin,task,nop,this,key,is,required,too"]


def test_add_required_key_tool(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_required_key("exe")
        assert runtool.get("require") == ["tool,builtin,task,nop,exe"]
        assert runtool.add_required_key("path")
        assert runtool.get("require") == ["tool,builtin,task,nop,exe",
                                          "tool,builtin,task,nop,path"]


def test_add_required_key_not_tool(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_required_key("option", "design")
        assert runtool.get("require") == ["option,design"]


def test_add_required_key_invalid(running_node):
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^key can only contain strings$"):
            runtool.add_required_key("this", None, "is", "required")


def test_record_metric_with_units(running_node):
    EditableSchema(running_node.project).insert(
        "metric", "peakpower", Parameter("float", pernode=PerNode.REQUIRED, unit="mw"))
    with running_node.task.runtime(running_node) as runtool:
        runtool.record_metric("peakpower", 1.05e6, source_unit="uW")
    assert running_node.project.get("metric", "peakpower", field="unit") == "mw"
    assert running_node.project.get("metric", "peakpower", step="running", index="0") == 1.05e3

    assert running_node.project.get("tool", "builtin", "task", "nop", "report", "peakpower",
                                    step="running", index="0") == []


def test_record_metric_without_units(running_node):
    EditableSchema(running_node.project).insert(
        "metric", "cells", Parameter("float", pernode=PerNode.REQUIRED))
    with running_node.task.runtime(running_node) as runtool:
        runtool.record_metric("cells", 25)
    assert running_node.project.get("metric", "cells", step="running", index="0") == 25

    assert running_node.project.get("tool", "builtin", "task", "nop", "report", "cells",
                                    step="running", index="0") == []


def test_record_metric_with_source(running_node):
    EditableSchema(running_node.project).insert(
        "metric", "cells", Parameter("float", pernode=PerNode.REQUIRED))
    with running_node.task.runtime(running_node) as runtool:
        runtool.record_metric("cells", 25, "report.txt")
    assert running_node.project.get("metric", "cells", step="running", index="0") == 25

    assert running_node.project.get("tool", "builtin", "task", "nop", "report", "cells",
                                    step="running", index="0") == ["report.txt"]


def test_record_metric_invalid_metric(running_node, caplog):
    with running_node.task.runtime(running_node) as runtool:
        runtool.record_metric("notavalidmetric", 25, "report.txt")

    assert "notavalidmetric is not a valid metric" in caplog.text


def test_record_metric_invalid_metric_quiet(running_node, caplog):
    with running_node.task.runtime(running_node) as runtool:
        runtool.record_metric("notavalidmetric", 25, "report.txt", quiet=True)

    assert caplog.text == ""


def test_has_breakpoint(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.has_breakpoint() is False

    running_node.project.set("option", "breakpoint", True, step="running")
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.has_breakpoint() is True


def test_search_path_resolution_not_special(running_node):
    assert running_node.task._find_files_search_paths("otherkey", "step", "index") == []


def test_search_path_resolution_script_no_ref(running_node):
    assert running_node.task._find_files_search_paths("script", "step", "index") == []


def test_search_path_resolution_script_with_ref(running_node):
    running_node.task.set("refdir", "refdir")
    os.makedirs("refdir", exist_ok=True)

    assert running_node.task._find_files_search_paths("script", "step", "index") == [
        os.path.abspath("refdir")
    ]


def test_search_path_resolution_input(running_node):
    assert running_node.task._find_files_search_paths("input", "step", "index") == [
        os.path.abspath("build/testdesign/job0/step/index/inputs")
    ]


def test_search_path_resolution_report(running_node):
    assert running_node.task._find_files_search_paths("report", "step", "index") == [
        os.path.abspath("build/testdesign/job0/step/index/report")
    ]


def test_search_path_resolution_output(running_node):
    assert running_node.task._find_files_search_paths("output", "step", "index") == [
        os.path.abspath("build/testdesign/job0/step/index/outputs")
    ]


def test_set_threads(running_node):
    with patch("siliconcompiler.utils.get_cores") as get_cores:
        get_cores.return_value = 15
        with running_node.task.runtime(running_node) as runtool:
            assert runtool.set_threads()
            assert runtool.get("threads") == 15
            assert BaseSchema.get(runtool, "threads", step="running", index="0") == 15
            assert BaseSchema.get(runtool, "threads", step="notrunning", index="0") is None
            assert runtool.get_threads() == 15
        get_cores.assert_called_once()


def test_set_threads_with_max(running_node):
    with patch("siliconcompiler.utils.get_cores") as get_cores:
        with running_node.task.runtime(running_node) as runtool:
            assert runtool.set_threads(5)
            assert runtool.get("threads") == 5
            assert runtool.get_threads() == 5
        get_cores.assert_not_called()


def test_set_threads_without_clobber(running_node):
    with patch("siliconcompiler.utils.get_cores") as get_cores:
        with running_node.task.runtime(running_node) as runtool:
            assert runtool.set_threads(5)
            assert runtool.get("threads") == 5
            assert runtool.get_threads() == 5
            assert not runtool.set_threads(10)
            assert runtool.get("threads") == 5
            assert runtool.get_threads() == 5
        get_cores.assert_not_called()


def test_set_threads_with_clobber(running_node):
    with patch("siliconcompiler.utils.get_cores") as get_cores:
        with running_node.task.runtime(running_node) as runtool:
            assert runtool.set_threads(5)
            assert runtool.get("threads") == 5
            assert runtool.get_threads() == 5
            assert runtool.set_threads(10, clobber=True)
            assert runtool.get("threads") == 10
            assert runtool.get_threads() == 10
        get_cores.assert_not_called()


def test_add_commandline_option(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_commandline_option("-exit")
        assert runtool.get("option") == ["-exit"]
        assert runtool.get_commandline_options() == ["-exit"]
        assert runtool.add_commandline_option("arg0")
        assert runtool.get("option") == ["-exit", "arg0"]
        assert runtool.get_commandline_options() == ["-exit", "arg0"]


def test_add_input_file_invalid(running_node):
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^only file or ext can be specified$"):
            runtool.add_input_file(file="this.v", ext="v")


def test_add_input_file_file(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.add_input_file("this.v")
        assert runtool.get("input") == ["this.v"]


def test_add_input_file_ext(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.add_input_file(ext="v")
        assert runtool.get("input") == ["designtop.v"]
        runtool.add_input_file("this.v")
        assert runtool.get("input") == ["designtop.v", "this.v"]


def test_add_input_file_clobber(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.add_input_file(ext="v")
        assert runtool.get("input") == ["designtop.v"]
        runtool.add_input_file("this.v", clobber=True)
        assert runtool.get("input") == ["this.v"]


def test_add_output_file_invalid(running_node):
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^only file or ext can be specified$"):
            runtool.add_output_file(file="this.v", ext="v")


def test_add_output_file_file(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.add_output_file("this.v")
        assert runtool.get("output") == ["this.v"]


def test_add_output_file_ext(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.add_output_file(ext="v")
        assert runtool.get("output") == ["designtop.v"]
        runtool.add_output_file("this.v")
        assert runtool.get("output") == ["designtop.v", "this.v"]


def test_add_output_file_clobber(running_node):
    with running_node.task.runtime(running_node) as runtool:
        runtool.add_output_file(ext="v")
        assert runtool.get("output") == ["designtop.v"]
        runtool.add_output_file("this.v", clobber=True)
        assert runtool.get("output") == ["this.v"]


def test_get_logpath(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_logpath("exe") == "running.log"
        assert runtool.get_logpath("sc") == "sc_running_0.log"


def test_get_logpath_fail(running_node):
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(ValueError, match="^notvalid is not a log$"):
            runtool.get_logpath("notvalid")


def test_get_tcl_variables(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_tcl_variables() == {
            'sc_task': '"nop"',
            'sc_tool': '"builtin"',
            'sc_topmodule': '"designtop"',
            'sc_designlib': '"testdesign"'
        }


def test_get_tcl_variables_with_refdir(running_node):
    running_node.task.set("refdir", ".")
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_tcl_variables() == {
            'sc_task': '"nop"',
            'sc_tool': '"builtin"',
            'sc_topmodule': '"designtop"',
            "sc_refdir": '[list "."]',
            'sc_designlib': '"testdesign"'
        }


def test_get_tcl_variables_with_refdir_diffsource(running_node):
    copy_project = running_node.project.copy()
    copy_project.set("tool", "builtin", "task", "nop", "refdir", "thispath")
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_tcl_variables(copy_project) == {
            'sc_task': '"nop"',
            'sc_tool': '"builtin"',
            'sc_topmodule': '"designtop"',
            "sc_refdir": '[list "thispath"]',
            'sc_designlib': '"testdesign"'
        }


def test_set_exe(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set_exe(exe="testexe", vswitch="-ver", format="json")
        assert runtool.get("exe") == "testexe"
        assert runtool.get("vswitch") == ["-ver"]
        assert runtool.get("format") == "json"


def test_set_path(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set_path(".")
        assert runtool.get("path") == "."


def test_add_version(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_version(">=1")
        assert runtool.add_version(">=2")
        assert runtool.get("version") == [">=1", ">=2"]
        assert runtool.add_version(">=3", clobber=True)
        assert runtool.get("version") == [">=3"]


def test_add_vswitch(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_vswitch("-h")
        assert runtool.add_vswitch("-v")
        assert runtool.get("vswitch") == ["-h", "-v"]
        assert runtool.add_vswitch("-version", clobber=True)
        assert runtool.get("vswitch") == ["-version"]


def test_add_licenseserver(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_licenseserver("testlic", "lic0")
        assert runtool.add_licenseserver("testlic", "lic1")
        assert runtool.get("licenseserver", "testlic") == ['lic0', 'lic1']
        assert runtool.add_licenseserver("testlic", "lic2", clobber=True)
        assert runtool.get("licenseserver", "testlic") == ["lic2"]


def test_add_sbom(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_sbom("v1", "sbom0")
        assert runtool.add_sbom("v1", "sbom1")
        assert runtool.get("sbom", "v1") == ['sbom0', 'sbom1']
        assert runtool.add_sbom("v1", "sbom2", clobber=True)
        assert runtool.get("sbom", "v1") == ["sbom2"]


def test_set_environmentalvariable(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set_environmentalvariable("ENV0", "TEST")
        assert runtool.get("env", "ENV0") == "TEST"


def test_add_prescript(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.has_prescript() is False

        assert runtool.add_prescript("prescript0.tcl")
        assert runtool.add_prescript("prescript1.tcl")
        assert runtool.get("prescript") == ["prescript0.tcl", "prescript1.tcl"]
        assert runtool.add_prescript("prescript2.tcl", clobber=True)
        assert runtool.get("prescript") == ["prescript2.tcl"]

        assert runtool.has_prescript() is True


def test_add_postscript(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.has_postscript() is False

        assert runtool.add_postscript("postscript0.tcl")
        assert runtool.add_postscript("postscript1.tcl")
        assert runtool.get("postscript") == ["postscript0.tcl", "postscript1.tcl"]
        assert runtool.add_postscript("postscript2.tcl", clobber=True)
        assert runtool.get("postscript") == ["postscript2.tcl"]

        assert runtool.has_postscript() is True


def test_set_refdir(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set_refdir(".")
        assert runtool.get("refdir") == ["."]


def test_set_script(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.set_script("script.tcl")
        assert runtool.get("script") == ["script.tcl"]


def test_add_regex(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_regex("errors", "^Error")
        assert runtool.add_regex("errors", "^Error0")
        assert runtool.get("regex", "errors") == ["^Error", "^Error0"]
        assert runtool.add_regex("errors", "^ERROR", clobber=True)
        assert runtool.get("regex", "errors") == ["^ERROR"]


def test_set_logdestination(running_node):
    with running_node.task.runtime(running_node) as runtool:
        print(runtool.get("stdout", "suffix"))
        assert runtool.set_logdestination("stderr", "output", "txt")
        assert runtool.set_logdestination("stdout", "none")
        assert runtool.get("stderr", "destination") == "output"
        assert runtool.get("stderr", "suffix") == "txt"
        assert runtool.get("stdout", "destination") == "none"
        assert runtool.get("stdout", "suffix") == "log"


def test_add_warningoff(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.add_warningoff("Error")
        assert runtool.add_warningoff("Error0")
        assert runtool.get("warningoff") == ["Error", "Error0"]
        assert runtool.add_warningoff("ERROR", clobber=True)
        assert runtool.get("warningoff") == ["ERROR"]


def test_get_fileset_file_keys(running_node):
    with running_node.task.runtime(running_node) as runtool:
        assert runtool.get_fileset_file_keys("verilog") == []


def test_get_fileset_file_keys_invalid(running_node):
    with running_node.task.runtime(running_node) as runtool:
        with pytest.raises(TypeError, match="^filetype must be a string$"):
            runtool.get_fileset_file_keys(["verilog"])


@pytest.mark.parametrize("cls", [ShowTask, ScreenshotTask])
def test_show_keys(cls):
    assert cls().getkeys("var") == ('showexit', 'showfilepath', 'showfiletype', 'shownode')


@pytest.mark.parametrize("cls", [ShowTask, ScreenshotTask])
def test_show_check_task_none(cls):
    assert cls._ShowTask__check_task(None) is None


@pytest.mark.parametrize("cls", [ShowTask, ScreenshotTask])
def test_show_tcl_vars(cls):
    with patch("siliconcompiler.Task.get_tcl_variables") as tcl_vars:
        tcl_vars.return_value = {}
        assert cls().get_tcl_variables() == {
            "sc_do_screenshot": "true" if cls is ScreenshotTask else "false"}


def test_show_task_name():
    assert ShowTask().task() == "show"
    assert ScreenshotTask().task() == "screenshot"


def test_show_check_task_invalid():
    class Test(ShowTask):
        pass

    with pytest.raises(TypeError, match="^class must be ShowTask or ScreenshotTask$"):
        Test._ShowTask__check_task(None)


def test_show_check_task_is_showtask():
    class Test(ShowTask):
        pass

    assert ShowTask._ShowTask__check_task(Test) is True
    assert ScreenshotTask._ShowTask__check_task(Test) is False


def test_show_check_task_is_screenshottask():
    class Test(ScreenshotTask):
        pass

    assert ShowTask._ShowTask__check_task(Test) is False
    assert ScreenshotTask._ShowTask__check_task(Test) is True


def test_show_register_task_invalid():
    class Test:
        pass

    with pytest.raises(TypeError, match="^task must be a subclass of ShowTask$"):
        ShowTask.register_task(Test)


def test_show_register_task():
    class Test(ShowTask):
        pass

    with patch.dict("siliconcompiler.ShowTask._ShowTask__TASKS", clear=True) \
            as tasks:
        assert len(tasks) == 0
        ShowTask.register_task(Test)
        assert len(tasks) == 1
        assert tasks[ShowTask] == set([Test])


def test_show_get_task():
    class Test(ShowTask):
        def get_supported_show_extentions(self):
            return ["ext"]
        pass

    with patch.dict("siliconcompiler.ShowTask._ShowTask__TASKS", clear=True), \
            patch("siliconcompiler.utils.showtools.showtasks") as showtasks:
        assert ShowTask.get_task("ext").__class__ is Test
        showtasks.assert_called_once()


@pytest.mark.parametrize("cls", [ShowTask, ScreenshotTask])
def test_show_get_supported_show_extentions(cls):
    with pytest.raises(NotImplementedError,
                       match="^get_supported_show_extentions must be "
                             "implemented by the child class$"):
        cls().get_supported_show_extentions() == {}
