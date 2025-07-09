import copy
import hashlib
import logging
import pathlib
import pytest
import os
import time

import os.path

from unittest.mock import patch, ANY

from siliconcompiler import RecordSchema, MetricSchema, FlowgraphSchema
from siliconcompiler.packageschema import PackageSchema
from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, SafeSchema
from siliconcompiler.schema.parameter import PerNode, Scope
from siliconcompiler.tool import TaskSchema, TaskExecutableNotFound, TaskError, TaskTimeout
from siliconcompiler.tool import ToolSchema
from siliconcompiler.flowgraph import RuntimeFlowgraph

from siliconcompiler.tools.builtin import nop

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


class NOPTask(TaskSchema):
    def __init__(self):
        super().__init__()
        self.set_name("testtask")

    def tool(self):
        return "builtin"

    def task(self):
        return "nop"


@pytest.fixture
def running_project():

    class TestProject(BaseSchema):
        def __init__(self):
            super().__init__()

            self.design = "testdesign"
            self.cwd = os.getcwd()

            self.schema = self

            self.logger = logging.getLogger()
            self.logger.setLevel(logging.INFO)

            schema = EditableSchema(self)

            flow = FlowgraphSchema("testflow")
            flow.node("running", nop)
            flow.node("notrunning", nop)
            flow.edge("running", "notrunning")
            schema.insert("flowgraph", "testflow", flow)
            schema.insert("record", RecordSchema())
            schema.insert("metric", MetricSchema())

            schema.insert("arg", "step", Parameter("str"))
            schema.insert("arg", "index", Parameter("str"))
            schema.insert("option", "breakpoint", Parameter("bool", pernode=PerNode.OPTIONAL))
            schema.insert("option", "flow", Parameter("str"))
            schema.insert("option", "strict", Parameter("bool"))
            schema.insert("option", "prune", Parameter("[(str,str)]"))
            schema.insert("option", "env", "default", Parameter("str"))

            schema.insert("tool", "default", ToolSchema(None))
            EditableSchema(
                self.get("tool", "builtin", "task", field="schema")).insert("nop", NOPTask())
            schema.insert("package", PackageSchema())

        def top(self):
            return "designtop"

        def get_nop(self):
            return self.get("tool", "builtin", "task", "nop", field="schema")

        def getworkdir(self, step=None, index=None):
            return os.path.abspath(".")

    project = TestProject()
    project.set('option', 'flow', 'testflow')
    project.set('arg', 'step', "running")
    project.set('arg', 'index', "0")
    return project


def test_tasktimeout_init():
    timeout = TaskTimeout("somemsg", timeout=5.5)
    assert timeout.timeout == 5.5
    assert timeout.args == ("somemsg",)


def test_init():
    tool = TaskSchema("testtool")
    assert tool.node() == (None, None)
    assert tool.logger() is None
    assert tool.schema() is None


def test_tool():
    with pytest.raises(NotImplementedError,
                       match="tool name must be implemented by the child class"):
        TaskSchema("testtool").tool()


def test_task():
    with pytest.raises(NotImplementedError,
                       match="task name must be implemented by the child class"):
        TaskSchema("testtool").task()


def test_runtime_invalid_step(running_project):
    running_project.unset('arg', 'step')
    with pytest.raises(RuntimeError, match="step or index not specified"):
        with TaskSchema("testtool").runtime(running_project):
            pass


def test_set_runtime_invalid_index(running_project):
    running_project.unset('arg', 'index')
    with pytest.raises(RuntimeError, match="step or index not specified"):
        with TaskSchema("testtool").runtime(running_project):
            pass


def test_set_runtime_invalid_flow(running_project):
    running_project.unset('option', 'flow')
    with pytest.raises(RuntimeError, match="flow not specified"):
        with TaskSchema("testtool").runtime(running_project):
            pass


def test_runtime(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.node() == ('running', '0')
        assert runtool.logger() is running_project.logger
        assert runtool.schema() is running_project.schema


def test_runtime_same_task(running_project):
    with running_project.get_nop().runtime(running_project) as runtool0, \
         running_project.get_nop().runtime(running_project,
                                           step="notrunning", index="0") as runtool1:
        assert runtool0 is not runtool1
        assert runtool0.node() == ('running', '0')
        assert runtool0.logger() is running_project.logger
        assert runtool0.schema() is running_project.schema
        assert runtool1.node() == ('notrunning', '0')
        assert runtool1.logger() is running_project.logger
        assert runtool1.schema() is running_project.schema

        assert runtool0.set("option", "tool0_opt")
        assert runtool1.set("option", "tool1_opt")

        assert runtool0.get("option") == ["tool0_opt"]
        assert runtool1.get("option") == ["tool1_opt"]
    assert running_project.get("tool", "builtin", "task", "nop", "option",
                               step="running", index="0") == ["tool0_opt"]
    assert running_project.get("tool", "builtin", "task", "nop", "option",
                               step="notrunning", index="0") == ["tool1_opt"]


def test_runtime_different(running_project):
    with running_project.get_nop().runtime(running_project, step="notrunning", index="0") as \
            runtool:
        assert runtool.node() == ('notrunning', '0')
        assert runtool.logger() is running_project.logger
        assert runtool.schema() is running_project.schema


def test_schema_access(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.schema() is running_project.schema
        assert isinstance(runtool.schema("record"), RecordSchema)
        assert isinstance(runtool.schema("metric"), MetricSchema)
        assert isinstance(runtool.schema("flow"), FlowgraphSchema)
        assert isinstance(runtool.schema("runtimeflow"), RuntimeFlowgraph)
        assert isinstance(runtool.schema("tool"), ToolSchema)


def test_schema_access_invalid(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="invalid is not a schema section"):
            runtool.schema("invalid")


def test_design_name(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.design_name() == "testdesign"


def test_design_topmodule(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.design_topmodule() == "designtop"


def test_set(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.set("option", "only_step_index")
        assert runtool.get("option") == ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == ["only_step_index"]
        assert BaseSchema.get(runtool, "option", step="notrunning", index="0") == []
    assert running_project.get("tool", "builtin", "task", "nop", "option",
                               step="running", index="0") == ["only_step_index"]
    assert running_project.get("tool", "builtin", "task", "nop", "option",
                               step="notrunning", index="0") == []


def test_add(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.add("option", "only_step_index0")
        assert runtool.add("option", "only_step_index1")
        assert runtool.get("option") == ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="running", index="0") == \
            ["only_step_index0", "only_step_index1"]
        assert BaseSchema.get(runtool, "option", step="notrunning", index="0") == []
    assert running_project.get("tool", "builtin", "task", "nop", "option",
                               step="running", index="0") == \
        ["only_step_index0", "only_step_index1"]
    assert running_project.get("tool", "builtin", "task", "nop", "option",
                               step="notrunning", index="0") == []


def test_get_exe_empty(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_exe() is None


def test_get_exe_not_found(running_project):
    assert running_project.set('tool', 'builtin', 'exe', 'testexe')
    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(TaskExecutableNotFound, match="testexe could not be found"):
            runtool.get_exe()


def test_get_exe_found(running_project, monkeypatch):
    assert running_project.set('tool', 'builtin', 'exe', 'testexe')

    def dummy_env(*args, **kwargs):
        assert "include_path" in kwargs
        assert kwargs["include_path"] is True
        return {"PATH": "search:this:path:set"}

    monkeypatch.setattr(running_project.get_nop(), 'get_runtime_environmental_variables', dummy_env)

    def dummy_which(*args, **kwargs):
        assert "path" in kwargs
        assert kwargs["path"] == "search:this:path:set"
        return "found/exe"

    monkeypatch.setattr(imported_shutil, 'which', dummy_which)
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_exe() == "found/exe"


def test_get_exe_version_no_vswitch(running_project):
    assert running_project.set('tool', 'builtin', 'exe', 'testexe')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_exe_version() is None


def test_get_exe_version_no_exe(running_project):
    assert running_project.set('tool', 'builtin', 'vswitch', '-version')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_exe_version() is None


def test_get_exe_version(running_project, monkeypatch, caplog):
    def parse_version(stdout):
        assert stdout == "myversion"
        return "1.0.0"
    monkeypatch.setattr(running_project.get_nop(), 'parse_version', parse_version)

    assert running_project.set('tool', 'builtin', 'vswitch', 'testexe')
    assert running_project.set('tool', 'builtin', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_exe_version() == "1.0.0"
    assert "Tool 'exe' found with version '1.0.0' in directory 'found'" in caplog.text


def test_get_exe_version_not_implemented(running_project, monkeypatch):
    assert running_project.set('tool', 'builtin', 'vswitch', 'testexe')
    assert running_project.set('tool', 'builtin', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(RuntimeError, match=r"builtin/nop does not implement parse_version\(\)"):
            runtool.get_exe_version()


def test_get_exe_version_non_zero_return(running_project, monkeypatch, caplog):
    def parse_version(stdout):
        assert stdout == "myversion"
        return "1.0.0"
    monkeypatch.setattr(running_project.get_nop(), 'parse_version', parse_version)

    assert running_project.set('tool', 'builtin', 'vswitch', 'testexe')
    assert running_project.set('tool', 'builtin', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 1
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_exe_version() == "1.0.0"

    assert "Version check on 'exe' ended with code 1" in caplog.text


def test_get_exe_version_internal_error(running_project, monkeypatch, caplog):
    def parse_version(stdout):
        raise ValueError("look for this match")
    monkeypatch.setattr(running_project.get_nop(), 'parse_version', parse_version)

    assert running_project.set('tool', 'builtin', 'vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="look for this match"):
            runtool.get_exe_version()

    assert "builtin/nop failed to parse version string: myversion" in caplog.text


def test_check_exe_version_not_set(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version(None) is True


def test_check_exe_version_valid(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', '==1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('1.0.0') is True
    assert caplog.text == ''


def test_check_exe_version_invalid(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', '!=1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('1.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 1.0.0, did not satisfy any version specifier set !=1.0.0" in caplog.text


def test_check_exe_version_value_ge(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', '>=1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('1.0.0') is True
    assert caplog.text == ""


def test_check_exe_version_value_compound(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', ['>=1.0.0,!=2.0.0'])
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('2.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,!=2.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_fail(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', ['>=1.0.0,<2.0.0', '>3.0.0'])
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('2.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,<2.0.0; >3.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_pass(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', ['>=1.0.0,<2.0.0', '>3.0.0'])
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('3.0.1') is True
    assert caplog.text == ""


def test_check_exe_version_value_invalid_spec(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', '1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('1.0.0') is True
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text


def test_check_exe_version_value_invalid_spec_fail(running_project, caplog):
    assert running_project.set('tool', 'builtin', 'version', '1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('1.0.1') is False
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text
    assert "Found version 1.0.1, did not satisfy any version specifier set 1.0.0" in caplog.text


def test_check_exe_version_normalize_error(running_project, monkeypatch, caplog):
    def normalize_version(reported_version):
        assert reported_version == "myversion"
        raise ValueError("match this error")
    monkeypatch.setattr(running_project.get_nop(), 'normalize_version', normalize_version)

    assert running_project.set("tool", "builtin", 'version', '==1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="match this error"):
            runtool.check_exe_version('myversion')
    assert "Unable to normalize version for builtin/nop: myversion" in caplog.text


def test_check_exe_version_normalize_pass(running_project, monkeypatch, caplog):
    def normalize_version(reported_version):
        return "1.0.0"
    monkeypatch.setattr(running_project.get_nop(), 'normalize_version', normalize_version)

    assert running_project.set("tool", "builtin", 'version', '==1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.check_exe_version('myversion') is True
    assert caplog.text == ""


def test_check_exe_version_normalize_error_spec(running_project, monkeypatch, caplog):
    def normalize_version(reported_version):
        if reported_version == "1.0.0":
            raise ValueError("match this error")
        return "1.0.0"
    monkeypatch.setattr(running_project.get_nop(), 'normalize_version', normalize_version)

    assert running_project.set("tool", "builtin", 'version', '==1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="match this error"):
            runtool.check_exe_version('myversion')
    assert "Unable to normalize versions for builtin/nop: ==1.0.0" in caplog.text


def test_check_exe_version_normalize_invalid_version(running_project, monkeypatch, caplog):
    def normalize_version(reported_version):
        return "notvalid"
    monkeypatch.setattr(running_project.get_nop(), 'normalize_version', normalize_version)

    assert running_project.set("tool", "builtin", 'version', '==1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.check_exe_version('myversion') is False
    assert "Version notvalid reported by builtin/nop does not match standard" in caplog.text


def test_check_exe_version_normalize_invalid_spec_version(running_project, monkeypatch, caplog):
    def normalize_version(reported_version):
        if reported_version == "myversion":
            return "1.0.0"
        return "notvalid"
    monkeypatch.setattr(running_project.get_nop(), 'normalize_version', normalize_version)

    assert running_project.set("tool", "builtin", 'version', '==1.0.0')
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.check_exe_version('myversion') is False
    assert "Version specifier set ==notvalid does not match standard" in caplog.text


def test_get_runtime_environmental_variables(running_project, monkeypatch):
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_runtime_environmental_variables() == {'PATH': 'this:path'}


def test_get_runtime_environmental_variables_no_path(running_project, monkeypatch):
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {}


def test_get_runtime_environmental_variables_envs(running_project, monkeypatch):
    running_project.set('option', 'env', 'CHECK', 'THIS')
    running_project.set('option', 'env', 'CHECKS', 'THAT')
    assert running_project.set("tool", "builtin", 'licenseserver', 'ENV_LIC0',
                               ('server0', 'server1'))
    assert running_project.set("tool", "builtin", 'licenseserver', 'ENV_LIC1',
                               ('server2', 'server3'))
    assert running_project.set("tool", "builtin", 'task', "nop", 'env', 'CHECK', "helloworld")

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.setenv("LD_LIBRARY_PATH", "this:ld:path")

    with running_project.get_nop().runtime(running_project) as runtool:
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


def test_get_runtime_environmental_variables_tool_path(running_project, monkeypatch):
    os.makedirs('./testpath', exist_ok=True)
    assert running_project.set("tool", "builtin", 'path', './testpath')

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    expect_path = os.path.abspath('./testpath') + os.pathsep + "this:path"

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {}
        assert runtool.get_runtime_environmental_variables() == {
            'PATH': expect_path
        }


def test_get_runtime_arguments(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.get_runtime_arguments() == []


def test_get_runtime_arguments_all(running_project, monkeypatch):
    with open("arg2.run", "w") as f:
        f.write("testfile")

    assert running_project.set("tool", "builtin", 'task', "nop", 'option', ['--arg0', '--arg1'])
    assert running_project.set('tool', "builtin", 'task', "nop", 'script', 'arg2.run')

    with running_project.get_nop().runtime(running_project) as runtool:
        def runtime_options():
            options = TaskSchema.runtime_options(runtool)
            options.append("--arg3")
            return options
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == [
            '--arg0',
            '--arg1',
            os.path.abspath("arg2.run"),
            '--arg3']


def test_get_runtime_different_types(running_project, monkeypatch):
    with running_project.get_nop().runtime(running_project) as runtool:
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


def test_get_runtime_different_types_relpath(running_project, monkeypatch):
    with running_project.get_nop().runtime(running_project, relpath=".") as runtool:
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


def test_get_runtime_arguments_all_relative(running_project, monkeypatch):
    with open("arg2.run", "w") as f:
        f.write("testfile")

    assert running_project.set("tool", "builtin", 'task', "nop", 'option', ['--arg0', '--arg1'])
    assert running_project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')

    with running_project.get_nop().runtime(running_project, relpath=os.getcwd()) as runtool:
        def runtime_options():
            options = TaskSchema.runtime_options(runtool)
            options.append("--arg3")
            return options
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == [
            '--arg0',
            '--arg1',
            "arg2.run",
            '--arg3']


def test_get_runtime_arguments_overwrite(running_project, monkeypatch):
    with open("arg2.run", "w") as f:
        f.write("testfile")

    assert running_project.set("tool", "builtin", 'task', "nop", 'option', ['--arg0', '--arg1'])
    assert running_project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')

    with running_project.get_nop().runtime(running_project) as runtool:
        def runtime_options():
            return ['--arg3']
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)

        assert runtool.get_runtime_arguments() == ['--arg3']


def test_get_runtime_arguments_error(running_project, monkeypatch, caplog):
    with running_project.get_nop().runtime(running_project) as runtool:
        def runtime_options():
            raise ValueError("match this error")
        monkeypatch.setattr(runtool, 'runtime_options', runtime_options)
        with pytest.raises(ValueError, match="match this error"):
            runtool.get_runtime_arguments()

    assert "Failed to get runtime options for builtin/nop" in caplog.text


def test_get_output_files(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.set('output', ["file0", "file1"])
        assert runtool.get_output_files() == set(["file0", "file1"])


def test_parse_version_not_implemented():
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        TaskSchema("testtool").parse_version("nothing")


def test_normalize_version():
    tool = TaskSchema("testtool")
    assert tool.normalize_version("nothing") == "nothing"
    assert tool.normalize_version(None) is None


def test_setup():
    tool = TaskSchema("testtool")
    assert tool.setup() is None


def test_pre_process():
    tool = TaskSchema("testtool")
    assert tool.pre_process() is None


def test_runtime_options(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.runtime_options() == []


def test_runtime_options_with_aruments(running_project):
    assert running_project.set("tool", "builtin", 'task', "nop", 'option', ['--arg0', '--arg1'])
    assert running_project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')
    with running_project.get_nop().runtime(running_project) as runtool:
        with open("arg2.run", "w") as f:
            f.write("test")

        assert runtool.runtime_options() == [
            '--arg0',
            '--arg1',
            os.path.abspath("arg2.run")
        ]


def test_runtime_options_with_aruments_with_refdir(running_project):
    assert running_project.set("tool", "builtin", 'task', "nop", 'option', ['--arg0', '--arg1'])
    assert running_project.set("tool", "builtin", 'task', "nop", 'refdir', 'refdir')
    assert running_project.set("tool", "builtin", 'task', "nop", 'script', 'arg2.run')
    os.makedirs("refdir", exist_ok=True)
    with open("refdir/arg2.run", "w") as f:
        f.write("test")

    with running_project.get_nop().runtime(running_project) as runtool:

        assert runtool.runtime_options() == [
            '--arg0',
            '--arg1',
            os.path.abspath("refdir/arg2.run")
        ]


def test_run_not_implemented():
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        TaskSchema("testtool").run()


def test_post_process():
    tool = TaskSchema("testtool")
    assert tool.post_process() is None


def test_resetting_state_in_copy(running_project):
    tool = TaskSchema("testtool")
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.schema() is not None

        tool = copy.deepcopy(runtool)
        assert tool.schema() is None


def test_generate_replay_script(running_project, monkeypatch):
    assert running_project.set("tool", "builtin", 'exe', 'testexe')
    assert running_project.set("tool", "builtin", 'vswitch', '-version')
    assert running_project.set("tool", "builtin", 'task', "nop", 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.generate_replay_script('replay.sh', './')
        assert os.path.exists('replay.sh')
        assert os.access('replay.sh', os.X_OK)

        with open('replay.sh', 'r') as replay:
            replay_text = "\n".join(replay.read().splitlines())
        replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

    assert replay_hash == "d86d8d1a38c5acf8a8954670cb0f802c"


def test_generate_replay_script_no_path(running_project, monkeypatch):
    assert running_project.set("tool", "builtin", 'exe', 'testexe')
    assert running_project.set("tool", "builtin", 'vswitch', '-version')
    assert running_project.set("tool", "builtin", 'task', "nop", 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.generate_replay_script('replay.sh', './', include_path=False)
        assert os.path.exists('replay.sh')
        assert os.access('replay.sh', os.X_OK)

        with open('replay.sh', 'r') as replay:
            replay_text = "\n".join(replay.read().splitlines())
        replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

        assert replay_hash == "ecf2e9d93e49feb3ce734fc3185e7480"


def test_setup_work_directory():
    tool = TaskSchema("builtin")

    os.makedirs("testwork", exist_ok=True)

    assert os.path.isdir("testwork")
    assert os.listdir("testwork") == []

    tool.setup_work_directory("testwork")

    assert os.path.isdir("testwork/inputs")
    assert os.path.isdir("testwork/outputs")
    assert os.path.isdir("testwork/reports")
    assert set(os.listdir("testwork")) == set(["inputs", "outputs", "reports"])


def test_setup_work_directory_ensure_clean():
    tool = TaskSchema("builtin")

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
    tool = TaskSchema("builtin")

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


def test_write_task_manifest_none(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == []


@pytest.mark.parametrize("suffix", ("tcl", "json", "yaml"))
def test_write_task_manifest(running_project, suffix):
    assert running_project.set("tool", "builtin", "format", suffix)
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == [f'sc_manifest.{suffix}']


def test_write_task_manifest_abspath(running_project):
    assert running_project.set("tool", "builtin", "format", "json")
    running_project.set("tool", "builtin", "task", "nop", "refdir", ".")
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']

    check = SafeSchema.from_manifest(filepath="sc_manifest.json")
    assert check.get("tool", "builtin", "task", "nop", "refdir") == \
        [pathlib.Path(os.path.abspath(".")).as_posix()]


def test_write_task_manifest_relative(running_project):
    assert running_project.set("tool", "builtin", "format", "json")
    assert running_project.set("tool", "builtin", "task", "nop", "refdir", ".")
    with running_project.get_nop().runtime(running_project, relpath=os.getcwd()) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']

    check = SafeSchema.from_manifest(filepath="sc_manifest.json")
    assert check.get("tool", "builtin", "task", "nop", "refdir") == ["."]


def test_write_task_manifest_with_backup(running_project):
    assert running_project.set("tool", "builtin", "format", "json")
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']
        runtool.write_task_manifest('.')
        assert set(os.listdir()) == set(['sc_manifest.json', 'sc_manifest.json.bak'])


def test_write_task_manifest_without_backup(running_project):
    assert running_project.set("tool", "builtin", "format", "json")
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']
        runtool.write_task_manifest('.', backup=False)
        assert os.listdir() == ['sc_manifest.json']


@pytest.mark.parametrize("exitcode", [0, 1])
def test_run_task(running_project, exitcode, monkeypatch):
    assert running_project.set("tool", "builtin", "format", "json")

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
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    assert running_project.get("record", "toolargs", step="running", index="0") is None
    assert running_project.get("record", "toolexitcode", step="running", index="0") is None
    assert running_project.get("metric", "exetime", step="running", index="0") is None
    assert running_project.get("metric", "memory", step="running", index="0") is None

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == exitcode

    assert running_project.get("record", "toolargs", step="running", index="0") == ""
    assert running_project.get("record", "toolexitcode", step="running", index="0") == exitcode
    assert running_project.get("metric", "exetime", step="running", index="0") >= 0
    assert running_project.get("metric", "memory", step="running", index="0") >= 0


def test_run_task_failed_popen(running_project, monkeypatch):
    assert running_project.set("tool", "builtin", "format", "json")

    def dummy_popen(*args, **kwargs):
        raise RuntimeError("something bad happened")
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(TaskError, match="Unable to start found/exe: something bad happened"):
            runtool.run_task('.', False, "info", False, None, None)


@pytest.mark.parametrize("nice", [-5, 0, 5])
def test_run_task_nice(running_project, nice, monkeypatch):
    assert running_project.set("tool", "builtin", "format", "json")

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
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, nice, None) == 0


def test_run_task_timeout(running_project, monkeypatch, patch_psutil):
    assert running_project.set("tool", "builtin", "format", "json")

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
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(TaskTimeout, match="^$"):
            runtool.run_task('.', False, "info", False, None, 2)


def test_run_task_memory_limit(running_project, monkeypatch, patch_psutil, caplog):
    assert running_project.set("tool", "builtin", "format", "json")

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
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == 0

    assert "Current system memory usage is 91.2%" in caplog.text


@pytest.mark.parametrize("error", [PermissionError, imported_psutil.Error])
def test_run_task_exceptions_loop(running_project, monkeypatch, patch_psutil, error):
    assert running_project.set("tool", "builtin", "format", "json")

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
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == 0


def test_run_task_contl_c(running_project, monkeypatch, patch_psutil, caplog):
    assert running_project.set("tool", "builtin", "format", "json")

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
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(TaskError, match="^$"):
            runtool.run_task('.', False, "info", False, None, None)

    assert "Received ctrl-c." in caplog.text


def test_run_task_breakpoint_valid(running_project, monkeypatch):
    pytest.importorskip('pty')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    with running_project.get_nop().runtime(running_project) as runtool:
        with patch("pty.spawn", autospec=True) as spawn:
            spawn.return_value = 1
            assert runtool.run_task('.', False, "info", True, None, None) == 1
            spawn.assert_called_once()
            spawn.assert_called_with(["found/exe"], ANY)


def test_run_task_breakpoint_not_used(running_project, monkeypatch):
    pytest.importorskip('pty')
    monkeypatch.setattr(dut_tool, "pty", None)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(running_project.get_nop(), 'get_exe', dummy_get_exe)

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 1

            def poll(self):
                return self.returncode
        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    with running_project.get_nop().runtime(running_project) as runtool:
        with patch("pty.spawn", autospec=True) as spawn:
            spawn.return_value = 1
            assert runtool.run_task('.', False, "info", True, None, None) == 1
            spawn.assert_not_called()


def test_run_task_run(running_project):
    class RunTool(NOPTask):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    EditableSchema(running_project.get("tool", "builtin", "task", field="schema")).insert(
        "nop", RunTool(), clobber=True)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", True, None, None) == 1
        assert runtool.call_count == 1


def test_run_task_run_error(running_project):
    class RunTool(NOPTask):
        call_count = 0

        def run(self):
            self.call_count += 1
            raise ValueError("run error")

    EditableSchema(running_project.get("tool", "builtin", "task", field="schema")).insert(
        "nop", RunTool(), clobber=True)

    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="run error"):
            runtool.run_task('.', False, "info", True, None, None)
        assert runtool.call_count == 1


@pytest.mark.skipif(imported_resource is None, reason="resource not available")
def test_run_task_run_failed_resource(running_project, monkeypatch):
    class RunTool(NOPTask):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    EditableSchema(running_project.get("tool", "builtin", "task", field="schema")).insert(
        "nop", RunTool(), clobber=True)

    def dummy_resource(*args, **kwargs):
        raise PermissionError
    monkeypatch.setattr(imported_resource, "getrusage", dummy_resource)

    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", True, None, None) == 1
        assert runtool.call_count == 1


def test_select_input_nodes_entry(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.select_input_nodes() == []


def test_select_input_nodes_entry_has_input(running_project):
    with running_project.get_nop().runtime(running_project, step="notrunning", index="0") as \
            runtool:
        assert runtool.select_input_nodes() == [('running', '0')]


def test_task_add_parameter():
    task = TaskSchema("testtask")

    assert task.getkeys("var") == tuple()

    assert isinstance(task.add_parameter("teststr", "str", "long form help"), Parameter)
    assert isinstance(task.add_parameter("testbool", "bool", "long form help"), Parameter)
    assert isinstance(task.add_parameter("testlist", "[str]", "long form help"), Parameter)

    assert task.getkeys("var") == ("teststr", "testbool", "testlist")

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


def test_task_add_parameter_defvalue():
    task = TaskSchema("testtask")

    task.add_parameter("teststr", "str", "long form help", defvalue="checkthis")

    assert task.get("var", "teststr") == "checkthis"


@pytest.mark.parametrize("filename,step,index,expect", [
    ("noext", "instep", "inindex", "noext.instepinindex"),
    ("file.ext0", "instep", "inindex", "file.instepinindex.ext0"),
    ("file.ext0.ext1.ext2", "instep", "inindex", "file.instepinindex.ext0.ext1.ext2"),
])
def test_compute_input_file_node_name(filename, step, index, expect):
    assert TaskSchema().compute_input_file_node_name(filename, step, index) == expect


def test_get_files_from_input_nodes_entry(running_project):
    with running_project.get_nop().runtime(running_project, step="running", index="0") as runtool:
        assert runtool.get_files_from_input_nodes() == {}


def test_get_files_from_input_nodes_end(running_project):
    running_project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                        step="running", index="0")

    with running_project.get_nop().runtime(running_project, step="notrunning", index="0") as \
            runtool:
        assert runtool.get_files_from_input_nodes() == {
            'file0.txt': [('running', '0')]
        }


def test_get_files_from_input_nodes_skipped(running_project):
    flow = running_project.get("flowgraph", "testflow", field="schema")
    flow.node("lastnode", nop)
    flow.edge("notrunning", "lastnode")

    running_project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                        step="running", index="0")
    running_project.set("record", "status", "skipped", step="notrunning", index="0")

    with running_project.get_nop().runtime(running_project, step="lastnode", index="0") as runtool:
        assert runtool.get_files_from_input_nodes() == {
            'file0.txt': [('running', '0')]
        }


def test_get_files_from_input_nodes_multiple(running_project):
    flow = running_project.get("flowgraph", "testflow", field="schema")
    flow.node("firstnode", nop)
    flow.edge("firstnode", "notrunning")

    running_project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                        step="running", index="0")
    running_project.set("tool", "builtin", "task", "nop", "output", "file0.txt",
                        step="firstnode", index="0")
    running_project.add("tool", "builtin", "task", "nop", "output", "file1.txt",
                        step="firstnode", index="0")

    with running_project.get_nop().runtime(running_project, step="notrunning", index="0") as \
            runtool:
        assert runtool.get_files_from_input_nodes() == {
            'file0.txt': [('running', '0'), ('firstnode', '0')],
            'file1.txt': [('firstnode', '0')]
        }


def test_add_required_key(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.add_required_key("this", "key", "is", "required")
        assert runtool.get("require") == ["this,key,is,required"]
        assert runtool.add_required_key("this", "key", "is", "required", "too")
        assert runtool.get("require") == ["this,key,is,required", "this,key,is,required,too"]


def test_add_required_key_invalid(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="key can only contain strings"):
            runtool.add_required_key("this", None, "is", "required")


def test_record_metric_with_units(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.record_metric("peakpower", 1.05e6, source_unit="uW")
    assert running_project.get("metric", "peakpower", field="unit") == "mw"
    assert running_project.get("metric", "peakpower", step="running", index="0") == 1.05e3

    assert running_project.get("tool", "builtin", "task", "nop", "report", "peakpower",
                               step="running", index="0") == []


def test_record_metric_without_units(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.record_metric("cells", 25)
    assert running_project.get("metric", "cells", step="running", index="0") == 25

    assert running_project.get("tool", "builtin", "task", "nop", "report", "cells",
                               step="running", index="0") == []


def test_record_metric_with_source(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.record_metric("cells", 25, "report.txt")
    assert running_project.get("metric", "cells", step="running", index="0") == 25

    assert running_project.get("tool", "builtin", "task", "nop", "report", "cells",
                               step="running", index="0") == ["report.txt"]


def test_record_metric_invalid_metric(running_project, caplog):
    with running_project.get_nop().runtime(running_project) as runtool:
        runtool.record_metric("notavalidmetric", 25, "report.txt")

    assert "notavalidmetric is not a valid metric" in caplog.text


def test_has_breakpoint(running_project):
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.has_breakpoint() is False

    running_project.set("option", "breakpoint", True, step="running")
    with running_project.get_nop().runtime(running_project) as runtool:
        assert runtool.has_breakpoint() is True


def test_search_path_resolution_not_special(running_project):
    assert running_project.get_nop()._find_files_search_paths("otherkey", "step", "index") == []


def test_search_path_resolution_script_no_ref(running_project):
    assert running_project.get_nop()._find_files_search_paths("script", "step", "index") == []


def test_search_path_resolution_script_with_ref(running_project):
    running_project.get_nop().set("refdir", "refdir")
    os.makedirs("refdir", exist_ok=True)

    assert running_project.get_nop()._find_files_search_paths("script", "step", "index") == [
        os.path.abspath("refdir")
    ]


def test_search_path_resolution_input(running_project):
    assert running_project.get_nop()._find_files_search_paths("input", "step", "index") == [
        os.path.abspath("inputs")
    ]


def test_search_path_resolution_report(running_project):
    assert running_project.get_nop()._find_files_search_paths("report", "step", "index") == [
        os.path.abspath("report")
    ]


def test_search_path_resolution_output(running_project):
    assert running_project.get_nop()._find_files_search_paths("output", "step", "index") == [
        os.path.abspath("outputs")
    ]
