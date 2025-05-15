import copy
import logging
import pytest
import os

import os.path

from siliconcompiler import ToolSchema
from siliconcompiler import RecordSchema, MetricSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.tool import TaskSchema, TaskExecutableNotFound
from siliconcompiler import Chip

from siliconcompiler import Flow
from siliconcompiler.tools.builtin import nop

from siliconcompiler.tool import shutil as imported_shutil
from siliconcompiler.tool import subprocess as imported_subprocess


@pytest.fixture
def running_chip():
    flow = Flow("testflow")
    flow.node("testflow", "running", nop)
    chip = Chip('testdesign')
    chip.use(flow)
    chip.set('option', 'flow', 'testflow')
    chip.set('arg', 'step', "running")
    chip.set('arg', 'index', "0")
    return chip


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


def test_schema_access(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.schema() is running_chip.schema
    assert isinstance(tool.schema("record"), RecordSchema)
    assert isinstance(tool.schema("metric"), MetricSchema)


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


def test_get_runtime_command(running_chip, monkeypatch):
    tool = ToolSchema()
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    tool.set_runtime(running_chip)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    assert tool.get_runtime_command() == ['found/exe']


def test_get_runtime_command_all(running_chip, monkeypatch):
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

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    assert tool.get_runtime_command() == [
        'found/exe',
        '--arg0',
        '--arg1',
        os.path.abspath("arg2.run"),
        '--arg3']


def test_get_runtime_command_error(running_chip, monkeypatch, caplog):
    class TestTool(ToolSchema):
        def runtime_options(self):
            raise ValueError("match this error")
    tool = TestTool("builtin")
    # Insert empty task to provide access
    EditableSchema(tool).insert('task', 'nop', TaskSchema())
    running_chip.logger = logging.getLogger()
    running_chip.logger.setLevel(logging.INFO)
    tool.set_runtime(running_chip)

    def dummy_get_exe(*args, **kwargs):
        return "found/exe"
    monkeypatch.setattr(tool, 'get_exe', dummy_get_exe)

    with pytest.raises(ValueError, match="match this error"):
        tool.get_runtime_command()

    assert "Failed to get runtime options for builtin/nop" in caplog.text


def test_parse_version_not_implemented():
    tool = ToolSchema()
    with pytest.raises(NotImplementedError,
                       match="must be implemented by the implementation class"):
        tool.parse_version("nothing")


def test_normalize_version():
    tool = ToolSchema()
    assert tool.normalize_version("nothing") == "nothing"
    assert tool.normalize_version(None) is None


def test_runtime_options():
    tool = ToolSchema()
    assert tool.runtime_options() == []


def test_resetting_state_in_copy(running_chip):
    tool = ToolSchema()
    tool.set_runtime(running_chip)
    assert tool.schema() is not None

    tool = copy.deepcopy(tool)
    assert tool.schema() is None
