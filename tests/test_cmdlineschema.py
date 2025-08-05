import logging
import pytest

from unittest.mock import patch

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import PerNode
from siliconcompiler.cmdlineschema import CommandLineSchema


@pytest.fixture
def schema():
    class CLISchema(CommandLineSchema, BaseSchema):
        def __init__(self):
            super().__init__()

            schema = EditableSchema(self)
            schema.insert("test0", "test1", Parameter("str", switch=["-test <str>"]))
            schema.insert("test0", "test2", Parameter("[str]", switch=["-test_list <str>"]))
            schema.insert("test3", Parameter("str", switch=["-test_opt <str>"],
                                             pernode=PerNode.OPTIONAL))
            schema.insert("test4", Parameter("bool", switch=["-test_bool <bool>"],
                                             pernode=PerNode.OPTIONAL))
            schema.insert("option", "cfg", Parameter("[file]", switch=["-cfg <file>"]))
            schema.insert("option", "loglevel", Parameter("str", switch=["-loglevel <str>"],
                                                          pernode=PerNode.OPTIONAL))
            schema.insert("test5", Parameter(
                "int",
                switch=["-O<int>"]))
            schema.insert("test6", Parameter(
                "str",
                switch=["-D<str>"]))
            schema.insert("test7", Parameter(
                "dir",
                switch=["+incdir+<dir>"]))
    return CLISchema


def test_invalid_argument(schema, monkeypatch):
    monkeypatch.setattr('sys.argv', ['testprog', '-trst', 'checkthis'])

    with pytest.raises(SystemExit):
        schema().create_cmdline("testprog")


def test_str(schema, monkeypatch):
    monkeypatch.setattr('sys.argv', ['testprog', '-test', 'checkthis'])
    check_schema = schema.create_cmdline("testprog")

    assert check_schema is not schema
    assert check_schema.get('test0', 'test1') == 'checkthis'


def test_list(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-test_list', 'checkthis0', '-test_list', 'checkthis1'])
    check_schema = schema.create_cmdline("testprog")

    assert check_schema is not schema
    assert check_schema.get('test0', 'test2') == ['checkthis0', 'checkthis1']


def test_invalid_argument_in_switchlist(schema):
    with pytest.raises(ValueError, match="-invalid is/are not a valid commandline arguments"):
        schema().create_cmdline("testprog", switchlist=["-invalid"])


def test_addversion(schema, capfd, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-version'])
    with pytest.raises(SystemExit):
        schema().create_cmdline("testprog", version="thisversion")

    assert "thisversion" in capfd.readouterr().out


def test_logmessages(schema, caplog, monkeypatch):
    class LogSchema(schema):
        logger = logging.getLogger()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-test', 'thisargument',
                         '-test_opt', 'globalvalue',
                         '-test_opt', 'thisstep stepvalue',
                         '-test_opt', 'thisstep thisindex stepindexvalue'])
    LogSchema.create_cmdline("testprog")

    assert "Command line argument entered: [test0,test1] Value: thisargument\n" in caplog.text
    assert "Command line argument entered: [test3] Value: globalvalue\n" in caplog.text
    assert "Command line argument entered: [test3] Value: stepvalue step: thisstep\n" in caplog.text
    assert "Command line argument entered: [test3] Value: stepindexvalue step: " \
        "thisstep index: thisindex\n" in caplog.text


def test_extra_args(schema, caplog, monkeypatch):
    class Extra(schema):
        def __init__(self):
            super().__init__()

            self._add_commandline_argument(
                "testvalue", "str", "this is a test parameter", "-extra <str>")
        logger = logging.getLogger()

    caplog.set_level(logging.INFO)
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-extra', 'thisextra'])
    check_schema = Extra.create_cmdline("testprog")

    assert check_schema.get("cmdarg", "testvalue") == "thisextra"

    assert "Command line argument entered: [cmdarg,testvalue] Value: thisextra\n" in caplog.text


def test_banner(schema, capsys, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog'])

    schema().create_cmdline("testprog", print_banner=True)

    assert "Version: " in capsys.readouterr().out


def test_banner_no_banner(schema, capsys, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog'])

    schema().create_cmdline("testprog", print_banner=False)

    assert capsys.readouterr().out == ""


def test_input_files(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', 'file0', 'file1'])

    check_schema = schema.create_cmdline("testprog")
    assert check_schema.get('cmdarg', 'input') == ["file0", "file1"]


def test_read_cfg(schema, monkeypatch):
    check_schema = schema()
    check_schema.set("test4", True)
    check_schema.write_manifest("test.json")

    monkeypatch.setattr('sys.argv',
                        ['testprog', '-cfg', 'test.json'])

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            f"{schema.__module__}/{schema.__name__}": schema
        }

        new_schema = schema.create_cmdline("testprog", use_cfg=True)

    assert new_schema.get('test4') is True


def test_custom_args(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-O3',
                         '-DCFG_ASIC=1',
                         '+incdir+/path'])

    new_schema = schema.create_cmdline("testprog")

    assert new_schema.get('test5') == 3
    assert new_schema.get('test6') == "CFG_ASIC=1"
    assert new_schema.get('test7') == "/path"


def test_add_cmdarg_with_auto_switch(schema):
    schema = schema()
    schema._add_commandline_argument("string", "str", "help string")
    assert schema.getkeys("cmdarg") == ("string",)
    assert schema.get("cmdarg", "string", field="switch") == ["-string <str>"]


def test_add_cmdarg_with_no_switch(schema):
    schema = schema()
    schema._add_commandline_argument("string", "str", "help string", ...)
    assert schema.getkeys("cmdarg") == ("string",)
    assert schema.get("cmdarg", "string", field="switch") == []


def test_add_cmdarg_with_missing_switch(schema):
    schema = schema()
    with pytest.raises(ValueError, match="switch is required"):
        schema._add_commandline_argument("string", "str", "help string", "")


def test_wrong_cfg_read_fail(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-cfg', "test.json"])

    class TestSchema(BaseSchema):
        @classmethod
        def _getdict_type(cls):
            return "testschema"

    TestSchema().write_manifest("test.json")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "testschema": TestSchema
        }
        with pytest.raises(TypeError, match="Schema is not a commandline class"):
            schema.create_cmdline("testprog", use_cfg=True)


def test_wrong_cfg_read_okay(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-cfg', "test.json"])

    class TestSchema(BaseSchema):
        @classmethod
        def _getdict_type(cls):
            return "testschema"

    TestSchema().write_manifest("test.json")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "testschema": TestSchema
        }
        check_schema = schema.create_cmdline("testprog", use_cfg=True, use_sources=False)
    assert isinstance(check_schema, TestSchema)
