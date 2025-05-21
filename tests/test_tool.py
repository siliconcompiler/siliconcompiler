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
from siliconcompiler.schema import EditableSchema
from siliconcompiler.tool import TaskSchema, TaskExecutableNotFound, TaskError, TaskTimeout
from siliconcompiler import Chip

from siliconcompiler import Flow
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
def running_chip():
    flow = Flow("testflow")
    flow.node("testflow", "running", nop)
    flow.node("testflow", "notrunning", nop)
    flow.edge("testflow", "running", "notrunning")
    chip = Chip('testdesign')
    chip.use(flow)
    chip.set('option', 'flow', 'testflow')
    chip.set('arg', 'step', "running")
    chip.set('arg', 'index', "0")
    return chip


def test_tasktimeout_init():
    timeout = TaskTimeout("somemsg", timeout=5.5)
    assert timeout.timeout == 5.5
    assert timeout.args == ("somemsg",)


def test_init():
    tool = ToolSchema()
    assert tool.node() == (None, None)
    assert tool.task() is None
    assert tool.logger() is None
    assert tool.schema() is None


def test_set_runtime_invalid_step(running_chip):
    running_chip.unset('arg', 'step')
    with pytest.raises(RuntimeError, match="step or index not specified"):
        ToolSchema().set_runtime(running_chip)


def test_set_runtime_invalid_index(running_chip):
    running_chip.unset('arg', 'index')
    with pytest.raises(RuntimeError, match="step or index not specified"):
        ToolSchema().set_runtime(running_chip)


def test_set_runtime_invalid_flow(running_chip):
    running_chip.unset('option', 'flow')
    with pytest.raises(RuntimeError, match="flow not specified"):
        ToolSchema().set_runtime(running_chip)


def test_set_runtime(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.node() == ('running', '0')
    assert tool.task() == 'nop'
    assert tool.logger() is running_chip.logger
    assert tool.schema() is running_chip.schema


def test_set_runtime_different(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip, step="notrunning", index="0")
    assert tool.node() == ('notrunning', '0')
    assert tool.task() == 'nop'
    assert tool.logger() is running_chip.logger
    assert tool.schema() is running_chip.schema


def test_schema_access(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.schema() is running_chip.schema
    assert isinstance(tool.schema("record"), RecordSchema)
    assert isinstance(tool.schema("metric"), MetricSchema)
    assert isinstance(tool.schema("flow"), FlowgraphSchema)


def test_schema_access_invalid(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    with pytest.raises(ValueError, match="invalid is not a schema section"):
        tool.schema("invalid")


def test_get_exe_empty(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.get_exe() is None


def test_get_exe_not_found(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    assert tool.set('exe', 'testexe')
    with pytest.raises(TaskExecutableNotFound, match="testexe could not be found"):
        tool.get_exe()


def test_get_exe_found(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
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
    assert tool.get_exe() == "found/exe"


def test_get_exe_version_no_vswitch(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    assert tool.set('exe', 'testexe')

    assert tool.get_exe_version() is None


def test_get_exe_version_no_exe(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    assert tool.set('vswitch', '-version')

    assert tool.get_exe_version() is None


def test_get_exe_version(running_chip, monkeypatch, caplog):
    class TestTool(ToolSchema):
        def parse_version(self, stdout):
            assert stdout == "myversion"
            return "1.0.0"

    tool = TestTool("testtool")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    assert tool.set('vswitch', 'testexe')
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class ret:
            returncode = 0
            stdout = "myversion"

        return ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    assert tool.get_exe_version() == "1.0.0"
    assert "Tool 'exe' found with version '1.0.0' in directory 'found'" in caplog.text


def test_get_exe_version_not_implemented(running_chip, monkeypatch):
    tool = ToolSchema("testtool")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    assert tool.set('vswitch', 'testexe')
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class ret:
            returncode = 0
            stdout = "myversion"

        return ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with pytest.raises(RuntimeError, match="testtool does not implement parse_version()"):
        tool.get_exe_version()


def test_get_exe_version_non_zero_return(running_chip, monkeypatch, caplog):
    class TestTool(ToolSchema):
        def parse_version(self, stdout):
            assert stdout == "myversion"
            return "1.0.0"

    tool = TestTool("testtool")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    tool.set_runtime(running_chip)
    assert tool.set('vswitch', 'testexe')
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class ret:
            returncode = 1
            stdout = "myversion"

        return ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    assert tool.get_exe_version() == "1.0.0"

    assert "Version check on 'exe' ended with code 1" in caplog.text


def test_get_exe_version_internal_error(running_chip, monkeypatch, caplog):
    class TestTool(ToolSchema):
        def parse_version(self, stdout):
            raise ValueError("look for this match")

    tool = TestTool("testtool")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    tool.set_runtime(running_chip)
    assert tool.set('vswitch', '-version')

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    def dummy_run(cmdlist, **kwargs):
        assert cmdlist == ['found/exe', '-version']

        class ret:
            returncode = 0
            stdout = "myversion"

        return ret()
    monkeypatch.setattr(imported_subprocess, 'run', dummy_run)

    with pytest.raises(ValueError, match="look for this match"):
        tool.get_exe_version()

    assert "testtool failed to parse version string: myversion" in caplog.text


def test_check_exe_version_not_set():
    tool = ToolSchema()
    assert tool.check_exe_version(None) is True


def test_check_exe_version_valid(running_chip, caplog):
    tool = ToolSchema()
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', '==1.0.0')
    assert tool.check_exe_version('1.0.0') is True
    assert caplog.text == ''


def test_check_exe_version_invalid(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', '!=1.0.0')
    assert tool.check_exe_version('1.0.0') is False
    assert "Version check failed for testtool. Check installation." in caplog.text
    assert "Found version 1.0.0, did not satisfy any version specifier set !=1.0.0" in caplog.text


def test_check_exe_version_value_ge(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', '>=1.0.0')
    assert tool.check_exe_version('1.0.0') is True
    assert caplog.text == ""


def test_check_exe_version_value_compound(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', ['>=1.0.0,!=2.0.0'])
    assert tool.check_exe_version('2.0.0') is False
    assert "Version check failed for testtool. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,!=2.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_fail(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', ['>=1.0.0,<2.0.0', '>3.0.0'])
    assert tool.check_exe_version('2.0.0') is False
    assert "Version check failed for testtool. Check installation." in caplog.text
    assert "Found version 2.0.0, did not satisfy any version specifier set >=1.0.0,<2.0.0; >3.0.0" \
        in caplog.text


def test_check_exe_version_value_multiple_pass(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', ['>=1.0.0,<2.0.0', '>3.0.0'])
    assert tool.check_exe_version('3.0.1') is True
    assert caplog.text == ""


def test_check_exe_version_value_invalid_spec(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', '1.0.0')
    assert tool.check_exe_version('1.0.0') is True
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text


def test_check_exe_version_value_invalid_spec_fail(running_chip, caplog):
    tool = ToolSchema("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
    tool.set('version', '1.0.0')
    assert tool.check_exe_version('1.0.1') is False
    assert "Invalid version specifier 1.0.0. Defaulting to ==1.0.0" in caplog.text
    assert "Found version 1.0.1, did not satisfy any version specifier set 1.0.0" in caplog.text


def test_check_exe_version_normalize_error(running_chip, caplog):
    class TestTool(ToolSchema):
        def normalize_version(self, reported_version):
            assert reported_version == "myversion"
            raise ValueError("match this error")

    tool = TestTool("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    tool.set('version', '==1.0.0')
    with pytest.raises(ValueError, match="match this error"):
        tool.check_exe_version('myversion')
    assert "Unable to normalize version for testtool: myversion" in caplog.text


def test_check_exe_version_normalize_pass(running_chip, caplog):
    class TestTool(ToolSchema):
        def normalize_version(self, reported_version):
            return "1.0.0"

    tool = TestTool("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    tool.set('version', '==1.0.0')
    assert tool.check_exe_version('myversion') is True
    assert caplog.text == ""


def test_check_exe_version_normalize_error_spec(running_chip, caplog):
    class TestTool(ToolSchema):
        def normalize_version(self, reported_version):
            if reported_version == "1.0.0":
                raise ValueError("match this error")
            return "1.0.0"

    tool = TestTool("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    tool.set('version', '==1.0.0')
    with pytest.raises(ValueError, match="match this error"):
        tool.check_exe_version('myversion')
    assert "Unable to normalize versions for testtool: ==1.0.0" in caplog.text


def test_check_exe_version_normalize_invalid_version(running_chip, caplog):
    class TestTool(ToolSchema):
        def normalize_version(self, reported_version):
            return "notvalid"

    tool = TestTool("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    tool.set('version', '==1.0.0')
    assert tool.check_exe_version('myversion') is False
    assert "Version notvalid reported by testtool does not match standard" in caplog.text


def test_check_exe_version_normalize_invalid_spec_version(running_chip, caplog):
    class TestTool(ToolSchema):
        def normalize_version(self, reported_version):
            if reported_version == "myversion":
                return "1.0.0"
            return "notvalid"

    tool = TestTool("testtool")
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    tool.set('version', '==1.0.0')
    assert tool.check_exe_version('myversion') is False
    assert "Version specifier set ==notvalid does not match standard" in caplog.text


def test_get_runtime_environmental_variables(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    assert tool.get_runtime_environmental_variables() == {'PATH': 'this:path'}


def test_get_runtime_environmental_variables_no_path(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    assert tool.get_runtime_environmental_variables(include_path=False) == {}


def test_get_runtime_environmental_variables_envs(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    running_chip.set('option', 'env', 'CHECK', 'THIS')
    running_chip.set('option', 'env', 'CHECKS', 'THAT')
    assert tool.set('licenseserver', 'ENV_LIC0', ('server0', 'server1'))
    assert tool.set('licenseserver', 'ENV_LIC1', ('server2', 'server3'))
    assert tool.set('task', tool.task(), 'env', 'CHECK', "helloworld")

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.setenv("LD_LIBRARY_PATH", "this:ld:path")

    assert tool.get_runtime_environmental_variables(include_path=False) == {
        'CHECK': 'helloworld',
        'CHECKS': 'THAT',
        'ENV_LIC0': 'server0:server1',
        'ENV_LIC1': 'server2:server3'
    }

    assert tool.get_runtime_environmental_variables() == {
        'CHECK': 'helloworld',
        'CHECKS': 'THAT',
        'ENV_LIC0': 'server0:server1',
        'ENV_LIC1': 'server2:server3',
        'PATH': 'this:path',
        'LD_LIBRARY_PATH': 'this:ld:path'
    }


def test_get_runtime_environmental_variables_tool_path(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    os.makedirs('./testpath', exist_ok=True)
    tool.set('path', './testpath')

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    expect_path = os.path.abspath('./testpath') + os.pathsep + "this:path"

    assert tool.get_runtime_environmental_variables(include_path=False) == {}
    assert tool.get_runtime_environmental_variables() == {
        'PATH': expect_path
    }


def test_get_runtime_arguments(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    assert tool.get_runtime_arguments() == []


def test_get_runtime_arguments_all(running_chip):
    class TestTool(ToolSchema):
        def runtime_options(self):
            return ['--arg3']
    tool = TestTool("builtin")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    with open("arg2.run", "w") as f:
        f.write("testfile")

    tool.set('task', tool.task(), 'option', ['--arg0', '--arg1'])
    running_chip.set('tool', 'builtin', 'task', tool.task(), 'script', 'arg2.run')

    assert tool.get_runtime_arguments() == [
        '--arg0',
        '--arg1',
        os.path.abspath("arg2.run"),
        '--arg3']


def test_get_runtime_arguments_error(running_chip, caplog):
    class TestTool(ToolSchema):
        def runtime_options(self):
            raise ValueError("match this error")
    tool = TestTool("builtin")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    with pytest.raises(ValueError, match="match this error"):
        tool.get_runtime_arguments()

    assert "Failed to get runtime options for builtin/nop" in caplog.text


def test_get_output_files(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    step, index = tool.node()
    tool.set('task', tool.task(), 'output', ["file0", "file1"], step=step, index=index)
    assert tool.get_output_files() == set(["file0", "file1"])


def test_parse_version_not_implemented():
    tool = ToolSchema()
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        tool.parse_version("nothing")


def test_normalize_version():
    tool = ToolSchema()
    assert tool.normalize_version("nothing") == "nothing"
    assert tool.normalize_version(None) is None


def test_setup():
    tool = ToolSchema()
    assert tool.setup() is None


def test_pre_process():
    tool = ToolSchema()
    assert tool.pre_process() is None


def test_runtime_options():
    tool = ToolSchema()
    assert tool.runtime_options() == []


def test_run_not_implemented():
    tool = ToolSchema()
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        tool.run()


def test_post_process():
    tool = ToolSchema()
    assert tool.post_process() is None


def test_resetting_state_in_copy(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.schema() is not None

    tool = copy.deepcopy(tool)
    assert tool.schema() is None


def test_generate_replay_script(running_chip, monkeypatch):
    tool = ToolSchema("builtin")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    assert tool.set('exe', 'testexe')
    assert tool.set('vswitch', '-version')
    tool.set('task', tool.task(), 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    tool.generate_replay_script('replay.sh', './')
    assert os.path.exists('replay.sh')
    assert os.access('replay.sh', os.X_OK)

    with open('replay.sh', 'r') as replay:
        replay_text = "\n".join(replay.read().splitlines())
    replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

    assert replay_hash == "6b93815de8247bcc11a9d0c102bc61fc"


def test_generate_replay_script_no_path(running_chip, monkeypatch):
    tool = ToolSchema("builtin")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    assert tool.set('exe', 'testexe')
    assert tool.set('vswitch', '-version')
    tool.set('task', tool.task(), 'option', [
        '--arg0', '--arg1', 'arg2', '--arg3', 'arg4', 'arg5',
        '/filehere', 'arg6'])

    monkeypatch.setenv("PATH", "this:path")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)

    tool.generate_replay_script('replay.sh', './', include_path=False)
    assert os.path.exists('replay.sh')
    assert os.access('replay.sh', os.X_OK)

    with open('replay.sh', 'r') as replay:
        replay_text = "\n".join(replay.read().splitlines())
    replay_hash = hashlib.md5(replay_text.encode()).hexdigest()

    assert replay_hash == "de125830f9267465ded0e4c6541d7d50"


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


def test_write_task_manifest_none(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    tool.write_task_manifest('.')
    assert os.listdir() == []


@pytest.mark.parametrize("suffix", ("tcl", "json", "yaml"))
def test_write_task_manifest(running_chip, suffix):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    tool.set("format", suffix)

    tool.write_task_manifest('.')
    assert os.listdir() == [f'sc_manifest.{suffix}']


def test_write_task_manifest_with_backup(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    tool.set("format", "json")

    tool.write_task_manifest('.')
    assert os.listdir() == ['sc_manifest.json']
    tool.write_task_manifest('.')
    assert set(os.listdir()) == set(['sc_manifest.json', 'sc_manifest.json.bak'])


def test_write_task_manifest_without_backup(running_chip):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    tool.set("format", "json")

    tool.write_task_manifest('.')
    assert os.listdir() == ['sc_manifest.json']
    tool.write_task_manifest('.', backup=False)
    assert os.listdir() == ['sc_manifest.json']


@pytest.mark.parametrize("exitcode", [0, 1])
def test_run_task(running_chip, exitcode, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
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

    assert running_chip.get("record", "toolargs", step="running", index="0") is None
    assert running_chip.get("record", "toolexitcode", step="running", index="0") is None
    assert running_chip.get("metric", "exetime", step="running", index="0") is None
    assert running_chip.get("metric", "memory", step="running", index="0") is None

    assert tool.run_task('.', False, "info", False, None, None) == exitcode

    assert running_chip.get("record", "toolargs", step="running", index="0") == ""
    assert running_chip.get("record", "toolexitcode", step="running", index="0") == exitcode
    assert running_chip.get("metric", "exetime", step="running", index="0") >= 0
    assert running_chip.get("metric", "memory", step="running", index="0") >= 0


def test_run_task_failed_popen(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
    assert tool.set("format", "json")

    def dummy_popen(*args, **kwargs):
        raise RuntimeError("something bad happened")
    monkeypatch.setattr(imported_subprocess, 'Popen', dummy_popen)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with pytest.raises(TaskError, match="Unable to start found/exe: something bad happened"):
        tool.run_task('.', False, "info", False, None, None)


@pytest.mark.parametrize("nice", [-5, 0, 5])
def test_run_task_nice(running_chip, nice, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
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

    assert tool.run_task('.', False, "info", False, nice, None) == 0


def test_run_task_timeout(running_chip, monkeypatch, patch_psutil):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
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

    with pytest.raises(TaskTimeout, match="^$"):
        tool.run_task('.', False, "info", False, None, 2)


def test_run_task_memory_limit(running_chip, monkeypatch, patch_psutil, caplog):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
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

    assert tool.run_task('.', False, "info", False, None, None) == 0

    assert "Current system memory usage is 91.2%" in caplog.text


@pytest.mark.parametrize("error", [PermissionError, imported_psutil.Error])
def test_run_task_exceptions_loop(running_chip, monkeypatch, patch_psutil, error):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)
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

    assert tool.run_task('.', False, "info", False, None, None) == 0


def test_run_task_contl_c(running_chip, monkeypatch, patch_psutil, caplog):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)
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

    with pytest.raises(TaskError, match="^$"):
        tool.run_task('.', False, "info", False, None, None)

    assert "Received ctrl-c." in caplog.text


def test_run_task_breakpoint_valid(running_chip, monkeypatch):
    pytest.importorskip('pty')
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with patch("pty.spawn", autospec=True) as spawn:
        spawn.return_value = 1
        assert tool.run_task('.', False, "info", True, None, None) == 1
        spawn.assert_called_once()
        spawn.assert_called_with(["found/exe"], ANY)


def test_run_task_breakpoint_not_used(running_chip, monkeypatch):
    pytest.importorskip('pty')
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

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

    with patch("pty.spawn", autospec=True) as spawn:
        spawn.return_value = 1
        assert tool.run_task('.', False, "info", True, None, None) == 1
        spawn.assert_not_called()


def test_run_task_run(running_chip, monkeypatch):
    class RunTool(ToolSchema):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    tool = RunTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    assert tool.run_task('.', False, "info", True, None, None) == 1
    assert tool.call_count == 1


def test_run_task_run_error(running_chip, monkeypatch):
    class RunTool(ToolSchema):
        call_count = 0

        def run(self):
            self.call_count += 1
            raise ValueError("run error")

    tool = RunTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    with pytest.raises(ValueError, match="run error"):
        tool.run_task('.', False, "info", True, None, None)
    assert tool.call_count == 1


@pytest.mark.skipif(imported_resource is None, reason="resource not available")
def test_run_task_run_failed_resource(running_chip, monkeypatch):
    class RunTool(ToolSchema):
        call_count = 0

        def run(self):
            self.call_count += 1
            return 1

    tool = RunTool()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    def dummy_resource(*args, **kwargs):
        raise PermissionError
    monkeypatch.setattr(imported_resource, "getrusage", dummy_resource)

    assert tool.run_task('.', False, "info", True, None, None) == 1
    assert tool.call_count == 1


def test_select_input_nodes_entry(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.select_input_nodes() == []


def test_select_input_nodes_entry_has_input(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip, step="notrunning", index="0")
    assert tool.select_input_nodes() == [('running', '0')]
