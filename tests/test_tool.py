import copy
import hashlib
import logging
import pytest
import os
import time

import os.path

from unittest.mock import patch, ANY

from siliconcompiler import ToolSchema
from siliconcompiler import RecordSchema, MetricSchema, FlowgraphSchema
from siliconcompiler.packageschema import PackageSchema
from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, SafeSchema
from siliconcompiler.schema.parameter import PerNode, Scope
from siliconcompiler.tool import TaskSchema, TaskExecutableNotFound, TaskError, TaskTimeout

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
            schema.insert("option", "flow", Parameter("str"))
            schema.insert("option", "strict", Parameter("bool"))
            schema.insert("option", "prune", Parameter("[(str,str)]"))
            schema.insert("option", "env", "default", Parameter("str"))

            schema.insert("tool", "default", ToolSchema(None))
            schema.insert("package", PackageSchema())

        def top(self):
            return self.design

    project = TestProject()
    project.set('option', 'flow', 'testflow')
    project.set('arg', 'step', "running")
    project.set('arg', 'index', "0")
    return project


@pytest.fixture
def nop_tool_task():
    class TestTool(ToolSchema):
        def __init__(self):
            super().__init__()
            self.set_name("testtool")

        def tool(self):
            return "builtin"

        def task(self):
            return "nop"

    return TestTool


def test_tasktimeout_init():
    timeout = TaskTimeout("somemsg", timeout=5.5)
    assert timeout.timeout == 5.5
    assert timeout.args == ("somemsg",)


def test_init():
    tool = ToolSchema("testtool")
    assert tool.node() == (None, None)
    assert tool.logger() is None
    assert tool.schema() is None


def test_tool():
    with pytest.raises(NotImplementedError,
                       match="tool name must be implemented by the child class"):
        ToolSchema("testtool").tool()


def test_task():
    with pytest.raises(NotImplementedError,
                       match="task name must be implemented by the child class"):
        ToolSchema("testtool").task()


def test_runtime_invalid_step(running_project):
    running_project.unset('arg', 'step')
    with pytest.raises(RuntimeError, match="step or index not specified"):
        with ToolSchema("testtool").runtime(running_project):
            pass


def test_set_runtime_invalid_index(running_project):
    running_project.unset('arg', 'index')
    with pytest.raises(RuntimeError, match="step or index not specified"):
        with ToolSchema("testtool").runtime(running_project):
            pass


def test_set_runtime_invalid_flow(running_project):
    running_project.unset('option', 'flow')
    with pytest.raises(RuntimeError, match="flow not specified"):
        with ToolSchema("testtool").runtime(running_project):
            pass


def test_runtime(running_project):
    tool = ToolSchema("testtool")

    with tool.runtime(running_project) as runtool:
        assert runtool.node() == ('running', '0')
        assert runtool.logger() is running_project.logger
        assert runtool.schema() is running_project.schema


def test_runtime_different(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project, step="notrunning", index="0") as runtool:
        assert runtool.node() == ('notrunning', '0')
        assert runtool.logger() is running_project.logger
        assert runtool.schema() is running_project.schema


def test_schema_access(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project) as runtool:
        assert runtool.schema() is running_project.schema
        assert isinstance(runtool.schema("record"), RecordSchema)
        assert isinstance(runtool.schema("metric"), MetricSchema)
        assert isinstance(runtool.schema("flow"), FlowgraphSchema)


def test_schema_access_invalid(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="invalid is not a schema section"):
            runtool.schema("invalid")


def test_get_exe_empty(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project) as runtool:
        assert runtool.get_exe() is None


def test_get_exe_not_found(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('exe', 'testexe')
    with tool.runtime(running_project) as runtool:
        with pytest.raises(TaskExecutableNotFound, match="testexe could not be found"):
            runtool.get_exe()


def test_get_exe_found(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('exe', 'testexe')

    def dummy_env(*args, **kwargs):
        assert "include_path" in kwargs
        assert kwargs["include_path"] is True
        return {"PATH": "search:this:path:set"}

    monkeypatch.setattr(tool, 'get_runtime_environmental_variables', dummy_env)

    def dummy_which(*args, **kwargs):
        assert "path" in kwargs
        assert kwargs["path"] == "search:this:path:set"
        return "found/exe"

    monkeypatch.setattr(imported_shutil, 'which', dummy_which)
    with tool.runtime(running_project) as runtool:
        assert runtool.get_exe() == "found/exe"


def test_get_exe_version_no_vswitch(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        assert runtool.set('exe', 'testexe')

        assert runtool.get_exe_version() is None


def test_get_exe_version_no_exe(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        assert runtool.set('vswitch', '-version')

        assert runtool.get_exe_version() is None


def test_get_exe_version(nop_tool_task, running_project, monkeypatch, caplog):
    class TestTool(nop_tool_task):
        def parse_version(self, stdout):
            assert stdout == "myversion"
            return "1.0.0"

    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('vswitch', 'testexe')
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with tool.runtime(running_project) as runtool:
        assert runtool.get_exe_version() == "1.0.0"
    assert "Tool 'exe' found with version '1.0.0' in directory 'found'" in caplog.text


def test_get_exe_version_not_implemented(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('vswitch', 'testexe')
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with tool.runtime(running_project) as runtool:
        with pytest.raises(RuntimeError, match=r"builtin/nop does not implement parse_version\(\)"):
            runtool.get_exe_version()


def test_get_exe_version_non_zero_return(nop_tool_task, running_project, monkeypatch, caplog):
    class TestTool(nop_tool_task):
        def parse_version(self, stdout):
            assert stdout == "myversion"
            return "1.0.0"

    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('vswitch', 'testexe')
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 1
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with tool.runtime(running_project) as runtool:
        assert runtool.get_exe_version() == "1.0.0"

    assert "Version check on 'exe' ended with code 1" in caplog.text


def test_get_exe_version_internal_error(nop_tool_task, running_project, monkeypatch, caplog):
    class TestTool(nop_tool_task):
        def parse_version(self, stdout):
            raise ValueError("look for this match")

    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class Ret:
            returncode = 0
            stdout = "myversion"

        return Ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with tool.runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="look for this match"):
            runtool.get_exe_version()

    assert "builtin/nop failed to parse version string: myversion" in caplog.text


def test_check_exe_version_not_set():
    tool = ToolSchema("testtool")
    assert tool.check_exe_version(None) is True


def test_check_exe_version_valid(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', '==1.0.0')
        assert runtool.check_exe_version('1.0.0') is True
    assert caplog.text == ''


def test_check_exe_version_invalid(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', '!=1.0.0')
        assert runtool.check_exe_version('1.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 1.0.0, did not satisfy any version specifier set !=1.0.0" in caplog.text


def test_check_exe_version_value_ge(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', '>=1.0.0')
        assert runtool.check_exe_version('1.0.0') is True
    assert caplog.text == ""


def test_check_exe_version_value_compound(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', ['>=1.0.0,!=2.0.0'])
        assert runtool.check_exe_version('2.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,!=2.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_fail(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', ['>=1.0.0,<2.0.0', '>3.0.0'])
        assert runtool.check_exe_version('2.0.0') is False
    assert "Version check failed for builtin/nop. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,<2.0.0; >3.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_pass(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', ['>=1.0.0,<2.0.0', '>3.0.0'])
        assert runtool.check_exe_version('3.0.1') is True
    assert caplog.text == ""


def test_check_exe_version_value_invalid_spec(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', '1.0.0')
        assert runtool.check_exe_version('1.0.0') is True
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text


def test_check_exe_version_value_invalid_spec_fail(nop_tool_task, running_project, caplog):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', '1.0.0')
        assert runtool.check_exe_version('1.0.1') is False
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text
    assert "Found version 1.0.1, did not satisfy any version specifier set 1.0.0" in caplog.text


def test_check_exe_version_normalize_error(nop_tool_task, running_project, caplog):
    class TestTool(nop_tool_task):
        def normalize_version(self, reported_version):
            assert reported_version == "myversion"
            raise ValueError("match this error")

    tool = TestTool()
    with tool.runtime(running_project) as runtool:
        runtool.set('version', '==1.0.0')
        with pytest.raises(ValueError, match="match this error"):
            runtool.check_exe_version('myversion')
    assert "Unable to normalize version for builtin/nop: myversion" in caplog.text


def test_check_exe_version_normalize_pass(nop_tool_task, running_project, caplog):
    class TestTool(nop_tool_task):
        def normalize_version(self, reported_version):
            return "1.0.0"

    tool = TestTool()
    tool.set('version', '==1.0.0')
    with tool.runtime(running_project) as runtool:
        assert runtool.check_exe_version('myversion') is True
    assert caplog.text == ""


def test_check_exe_version_normalize_error_spec(nop_tool_task, running_project, caplog):
    class TestTool(nop_tool_task):
        def normalize_version(self, reported_version):
            if reported_version == "1.0.0":
                raise ValueError("match this error")
            return "1.0.0"

    tool = TestTool()
    tool.set('version', '==1.0.0')
    with tool.runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="match this error"):
            runtool.check_exe_version('myversion')
    assert "Unable to normalize versions for builtin/nop: ==1.0.0" in caplog.text


def test_check_exe_version_normalize_invalid_version(nop_tool_task, running_project, caplog):
    class TestTool(nop_tool_task):
        def normalize_version(self, reported_version):
            return "notvalid"

    tool = TestTool()
    tool.set('version', '==1.0.0')
    with tool.runtime(running_project) as runtool:
        runtool.check_exe_version('myversion') is False
    assert "Version notvalid reported by builtin/nop does not match standard" in caplog.text


def test_check_exe_version_normalize_invalid_spec_version(nop_tool_task, running_project, caplog):
    class TestTool(nop_tool_task):
        def normalize_version(self, reported_version):
            if reported_version == "myversion":
                return "1.0.0"
            return "notvalid"

    tool = TestTool()
    tool.set('version', '==1.0.0')
    with tool.runtime(running_project) as runtool:
        runtool.check_exe_version('myversion') is False
    assert "Version specifier set ==notvalid does not match standard" in caplog.text


def test_get_runtime_environmental_variables(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with tool.runtime(running_project) as runtool:
        assert runtool.get_runtime_environmental_variables() == {'PATH': 'this:path'}


def test_get_runtime_environmental_variables_no_path(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with tool.runtime(running_project) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {}


def test_get_runtime_environmental_variables_envs(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    running_project.set('option', 'env', 'CHECK', 'THIS')
    running_project.set('option', 'env', 'CHECKS', 'THAT')
    assert tool.set('licenseserver', 'ENV_LIC0', ('server0', 'server1'))
    assert tool.set('licenseserver', 'ENV_LIC1', ('server2', 'server3'))
    assert tool.set('task', tool.task(), 'env', 'CHECK', "helloworld")

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.setenv("LD_LIBRARY_PATH", "this:ld:path")

    with tool.runtime(running_project) as runtool:
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


def test_get_runtime_environmental_variables_tool_path(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    os.makedirs('./testpath', exist_ok=True)
    tool.set('path', './testpath')

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    expect_path = os.path.abspath('./testpath') + os.pathsep + "this:path"

    with tool.runtime(running_project) as runtool:
        assert runtool.get_runtime_environmental_variables(include_path=False) == {}
        assert runtool.get_runtime_environmental_variables() == {
            'PATH': expect_path
        }


def test_get_runtime_arguments(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        assert runtool.get_runtime_arguments() == []


def test_get_runtime_arguments_all(nop_tool_task, running_project):
    class TestTool(nop_tool_task):
        def runtime_options(self):
            options = super().runtime_options()
            options.append("--arg3")
            return options
    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with open("arg2.run", "w") as f:
        f.write("testfile")

    tool.set('task', tool.task(), 'option', ['--arg0', '--arg1'])
    running_project.set('tool', tool.tool(), 'task', tool.task(), 'script', 'arg2.run')

    with tool.runtime(running_project) as runtool:
        assert runtool.get_runtime_arguments() == [
            '--arg0',
            '--arg1',
            os.path.abspath("arg2.run"),
            '--arg3']


def test_get_runtime_arguments_all_relative(nop_tool_task, running_project):
    class TestTool(nop_tool_task):
        def runtime_options(self):
            options = super().runtime_options()
            options.append("--arg3")
            return options
    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with open("arg2.run", "w") as f:
        f.write("testfile")

    tool.set('task', tool.task(), 'option', ['--arg0', '--arg1'])
    running_project.set('tool', tool.tool(), 'task', tool.task(), 'script', 'arg2.run')

    with tool.runtime(running_project, relpath=os.getcwd()) as runtool:
        assert runtool.get_runtime_arguments() == [
            '--arg0',
            '--arg1',
            "arg2.run",
            '--arg3']


def test_get_runtime_arguments_overwrite(nop_tool_task, running_project):
    class TestTool(nop_tool_task):
        def runtime_options(self):
            return ['--arg3']
    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with open("arg2.run", "w") as f:
        f.write("testfile")

    tool.set('task', tool.task(), 'option', ['--arg0', '--arg1'])
    running_project.set('tool', tool.tool(), 'task', tool.task(), 'script', 'arg2.run')

    with tool.runtime(running_project) as runtool:
        assert runtool.get_runtime_arguments() == ['--arg3']


def test_get_runtime_arguments_error(nop_tool_task, running_project, caplog):
    class TestTool(nop_tool_task):
        def runtime_options(self):
            raise ValueError("match this error")
    tool = TestTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="match this error"):
            runtool.get_runtime_arguments()

    assert "Failed to get runtime options for builtin/nop" in caplog.text


def test_get_output_files(nop_tool_task, running_project):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        step, index = runtool.node()
        runtool.set('task', tool.task(), 'output', ["file0", "file1"], step=step, index=index)
        assert runtool.get_output_files() == set(["file0", "file1"])


def test_parse_version_not_implemented():
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        ToolSchema("testtool").parse_version("nothing")


def test_normalize_version():
    tool = ToolSchema("testtool")
    assert tool.normalize_version("nothing") == "nothing"
    assert tool.normalize_version(None) is None


def test_setup():
    tool = ToolSchema("testtool")
    assert tool.setup() is None


def test_pre_process():
    tool = ToolSchema("testtool")
    assert tool.pre_process() is None


def test_runtime_options(nop_tool_task, running_project):
    tool = nop_tool_task()
    with tool.runtime(running_project) as runtool:
        assert runtool.runtime_options() == []


def test_runtime_options_with_aruments(nop_tool_task, running_project):
    tool = nop_tool_task()
    tool.set('task', tool.task(), 'option', ['--arg0', '--arg1'])
    with tool.runtime(running_project) as runtool:
        with open("arg2.run", "w") as f:
            f.write("test")

        running_project.set('tool', tool.tool(), 'task', tool.task(), 'script', 'arg2.run')
        assert runtool.runtime_options() == [
            '--arg0',
            '--arg1',
            os.path.abspath("arg2.run")
        ]


def test_run_not_implemented():
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        ToolSchema("testtool").run()


def test_post_process():
    tool = ToolSchema("testtool")
    assert tool.post_process() is None


def test_resetting_state_in_copy(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project) as runtool:
        assert runtool.schema() is not None

        tool = copy.deepcopy(runtool)
        assert tool.schema() is None


def test_generate_replay_script(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('exe', 'testexe')
    assert tool.set('vswitch', '-version')
    tool.set('task', tool.task(), 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])
    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with tool.runtime(running_project) as runtool:
        runtool.generate_replay_script('replay.sh', './')
        assert os.path.exists('replay.sh')
        assert os.access('replay.sh', os.X_OK)

        with open('replay.sh', 'r') as replay:
            replay_text = "\n".join(replay.read().splitlines())
        replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

    assert replay_hash == "d86d8d1a38c5acf8a8954670cb0f802c"


def test_generate_replay_script_no_path(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set('exe', 'testexe')
    assert tool.set('vswitch', '-version')
    tool.set('task', tool.task(), 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    with tool.runtime(running_project) as runtool:
        runtool.generate_replay_script('replay.sh', './', include_path=False)
        assert os.path.exists('replay.sh')
        assert os.access('replay.sh', os.X_OK)

        with open('replay.sh', 'r') as replay:
            replay_text = "\n".join(replay.read().splitlines())
        replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

        assert replay_hash == "ecf2e9d93e49feb3ce734fc3185e7480"


def test_setup_work_directory():
    tool = ToolSchema("builtin")

    os.makedirs("testwork", exist_ok=True)

    assert os.path.isdir("testwork")
    assert os.listdir("testwork") == []

    tool.setup_work_directory("testwork")

    assert os.path.isdir("testwork/inputs")
    assert os.path.isdir("testwork/outputs")
    assert os.path.isdir("testwork/reports")
    assert set(os.listdir("testwork")) == set(["inputs", "outputs", "reports"])


def test_setup_work_directory_ensure_clean():
    tool = ToolSchema("builtin")

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
    tool = ToolSchema("builtin")

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


def test_write_task_manifest_none(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == []


@pytest.mark.parametrize("suffix", ("tcl", "json", "yaml"))
def test_write_task_manifest(nop_tool_task, running_project, suffix):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    tool.set("format", suffix)
    with tool.runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == [f'sc_manifest.{suffix}']


def test_write_task_manifest_abspath(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    tool.set("format", "json")
    running_project.set("tool", tool.tool(), "task", tool.task(), "refdir", ".")
    with tool.runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']

    check = SafeSchema.from_manifest(filepath="sc_manifest.json")
    assert check.get("tool", tool.tool(), "task", tool.task(), "refdir") == [os.path.abspath(".")]


def test_write_task_manifest_relative(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    tool.set("format", "json")
    running_project.set("tool", tool.tool(), "task", tool.task(), "refdir", ".")
    with tool.runtime(running_project, relpath=os.getcwd()) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']

    check = SafeSchema.from_manifest(filepath="sc_manifest.json")
    assert check.get("tool", tool.tool(), "task", tool.task(), "refdir") == ["."]


def test_write_task_manifest_with_backup(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    tool.set("format", "json")
    with tool.runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']
        runtool.write_task_manifest('.')
        assert set(os.listdir()) == set(['sc_manifest.json', 'sc_manifest.json.bak'])


def test_write_task_manifest_without_backup(nop_tool_task, running_project):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    tool.set("format", "json")
    with tool.runtime(running_project) as runtool:
        runtool.write_task_manifest('.')
        assert os.listdir() == ['sc_manifest.json']
        runtool.write_task_manifest('.', backup=False)
        assert os.listdir() == ['sc_manifest.json']


@pytest.mark.parametrize("exitcode", [0, 1])
def test_run_task(nop_tool_task, running_project, exitcode, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

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
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    assert running_project.get("record", "toolargs", step="running", index="0") is None
    assert running_project.get("record", "toolexitcode", step="running", index="0") is None
    assert running_project.get("metric", "exetime", step="running", index="0") is None
    assert running_project.get("metric", "memory", step="running", index="0") is None

    with tool.runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == exitcode

    assert running_project.get("record", "toolargs", step="running", index="0") == ""
    assert running_project.get("record", "toolexitcode", step="running", index="0") == exitcode
    assert running_project.get("metric", "exetime", step="running", index="0") >= 0
    assert running_project.get("metric", "memory", step="running", index="0") >= 0


def test_run_task_failed_popen(nop_tool_task, running_project, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

    def dummy_popen(*args, **kwargs):
        raise RuntimeError("something bad happened")
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        with pytest.raises(TaskError, match="Unable to start found/exe: something bad happened"):
            runtool.run_task('.', False, "info", False, None, None)


@pytest.mark.parametrize("nice", [-5, 0, 5])
def test_run_task_nice(nop_tool_task, running_project, nice, monkeypatch):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

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
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, nice, None) == 0


def test_run_task_timeout(nop_tool_task, running_project, monkeypatch, patch_psutil):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

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
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        with pytest.raises(TaskTimeout, match="^$"):
            runtool.run_task('.', False, "info", False, None, 2)


def test_run_task_memory_limit(nop_tool_task, running_project, monkeypatch, patch_psutil, caplog):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

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
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == 0

    assert "Current system memory usage is 91.2%" in caplog.text


@pytest.mark.parametrize("error", [PermissionError, imported_psutil.Error])
def test_run_task_exceptions_loop(nop_tool_task, running_project, monkeypatch, patch_psutil, error):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

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
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", False, None, None) == 0


def test_run_task_contl_c(nop_tool_task, running_project, monkeypatch, patch_psutil, caplog):
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    assert tool.set("format", "json")

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
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        with pytest.raises(TaskError, match="^$"):
            runtool.run_task('.', False, "info", False, None, None)

    assert "Received ctrl-c." in caplog.text


def test_run_task_breakpoint_valid(nop_tool_task, running_project, monkeypatch):
    pytest.importorskip('pty')
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with tool.runtime(running_project) as runtool:
        with patch("pty.spawn", autospec=True) as spawn:
            spawn.return_value = 1
            assert runtool.run_task('.', False, "info", True, None, None) == 1
            spawn.assert_called_once()
            spawn.assert_called_with(["found/exe"], ANY)


def test_run_task_breakpoint_not_used(nop_tool_task, running_project, monkeypatch):
    pytest.importorskip('pty')
    tool = nop_tool_task()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    monkeypatch.setattr(dut_tool, "pty", None)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_popen(*args, **kwargs):
        assert args == (["found/exe"],)
        assert kwargs["preexec_fn"] is None

        class Popen:
            returncode = 1

            def poll(self):
                return self.returncode
        return Popen()
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    with tool.runtime(running_project) as runtool:
        with patch("pty.spawn", autospec=True) as spawn:
            spawn.return_value = 1
            assert runtool.run_task('.', False, "info", True, None, None) == 1
            spawn.assert_not_called()


def test_run_task_run(nop_tool_task, running_project, monkeypatch):
    class RunTool(nop_tool_task):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    tool = RunTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", True, None, None) == 1
        assert runtool.call_count == 1


def test_run_task_run_error(nop_tool_task, running_project):
    class RunTool(nop_tool_task):
        call_count = 0

        def run(self):
            self.call_count += 1
            raise ValueError("run error")

    tool = RunTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))
    with tool.runtime(running_project) as runtool:
        with pytest.raises(ValueError, match="run error"):
            runtool.run_task('.', False, "info", True, None, None)
        assert runtool.call_count == 1


@pytest.mark.skipif(imported_resource is None, reason="resource not available")
def test_run_task_run_failed_resource(nop_tool_task, running_project, monkeypatch):
    class RunTool(nop_tool_task):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    tool = RunTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', tool.task(), TaskSchema(tool.task()))

    def dummy_resource(*args, **kwargs):
        raise PermissionError
    monkeypatch.setattr(imported_resource, "getrusage", dummy_resource)

    with tool.runtime(running_project) as runtool:
        assert runtool.run_task('.', False, "info", True, None, None) == 1
        assert runtool.call_count == 1


def test_select_input_nodes_entry(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project) as runtool:
        assert runtool.select_input_nodes() == []


def test_select_input_nodes_entry_has_input(running_project):
    tool = ToolSchema("testtool")
    with tool.runtime(running_project, step="notrunning", index="0") as runtool:
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
