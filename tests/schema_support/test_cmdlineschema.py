import logging
import pytest

from unittest.mock import patch

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import PerNode
from siliconcompiler.schema_support.cmdlineschema import CommandLineSchema


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
    with pytest.raises(ValueError, match=r"^-invalid is/are not a valid commandline arguments$"):
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


@pytest.mark.parametrize("type,switchtype", [
    ("str", "<str>"),
    ("bool", "<bool>"),
    ("int", "<int>"),
    ("[str]", "<str>"),
    ("[file]", "<file>"),
    ("[dir]", "<dir>"),
    ("{str}", "<str>"),
    ("[(str,str)]", "<(str,str)>")
])
def test_add_cmdarg_with_auto_switch(schema, type, switchtype):
    schema = schema()
    schema._add_commandline_argument("testarg", type, "help string")
    assert schema.getkeys("cmdarg") == ("testarg",)
    assert schema.get("cmdarg", "testarg", field="switch") == [f"-testarg {switchtype}"]


def test_add_cmdarg_with_no_switch(schema):
    schema = schema()
    schema._add_commandline_argument("string", "str", "help string", ...)
    assert schema.getkeys("cmdarg") == ("string",)
    assert schema.get("cmdarg", "string", field="switch") == []


def test_add_cmdarg_with_missing_switch(schema):
    schema = schema()
    with pytest.raises(ValueError, match=r"^switch is required$"):
        schema._add_commandline_argument("string", "str", "help string", "")


def test_wrong_cfg_read_fail(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-cfg', "test.json"])

    class TestSchema2(BaseSchema):
        @classmethod
        def _getdict_type(cls):
            return "testschema2"

    TestSchema2().write_manifest("test.json")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "testschema2": TestSchema2
        }
        with pytest.raises(TypeError, match=r"^Schema is not a commandline class$"):
            schema.create_cmdline("testprog", use_cfg=True)


def test_wrong_cfg_read_okay(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-cfg', "test.json"])

    class TestSchema3(BaseSchema):
        @classmethod
        def _getdict_type(cls):
            return "testschema3"

    TestSchema3().write_manifest("test.json")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "testschema3": TestSchema3
        }
        check_schema = schema.create_cmdline("testprog", use_cfg=True, use_sources=False)
    assert isinstance(check_schema, TestSchema3)


def test_add_cmdarg_with_non_string_help(schema):
    schema = schema()
    with pytest.raises(TypeError, match=r"^help must be a string$"):
        schema._add_commandline_argument("testarg", "str", 123)


def test_add_cmdarg_with_defvalue(schema):
    schema = schema()
    schema._add_commandline_argument("testarg", "str", "help string", defvalue="defaultval")
    assert schema.getkeys("cmdarg") == ("testarg",)
    # defvalue sets the default - verify it by reading the value
    assert schema.get("cmdarg", "testarg") == "defaultval"


def test_progname_as_file_path(schema, monkeypatch, tmp_path):
    # Create a test file
    test_file = tmp_path / "testprog.py"
    test_file.touch()

    monkeypatch.setattr('sys.argv', [str(test_file)])
    check_schema = schema.create_cmdline(progname=str(test_file), use_sources=False)
    assert check_schema is not None


def test_cfg_file_in_middle_of_argv(schema, monkeypatch):
    check_schema = schema()
    check_schema.set("test4", True)
    check_schema.write_manifest("test2.json")

    # Test when -cfg is not at the beginning
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-test', 'value', '-cfg', 'test2.json'])

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            f"{schema.__module__}/{schema.__name__}": schema
        }
        new_schema = schema.create_cmdline("testprog", use_cfg=True)

    assert new_schema.get('test4') is True
    assert new_schema.get('test0', 'test1') == 'value'


def test_use_sources_with_existing_cmdarg_input(schema, monkeypatch):
    '''Test that use_sources handles existing cmdarg.input gracefully.'''
    # Create a schema that already has cmdarg.input defined
    schema = schema()
    schema._add_commandline_argument("input", "[file]", "existing input files", ...)

    monkeypatch.setattr('sys.argv', ['testprog', 'file1.txt', 'file2.txt'])

    new_schema = schema.create_cmdline("testprog", use_sources=True)

    # Should have both files in input
    assert new_schema.get("cmdarg", "input") == ["file1.txt", "file2.txt"]


def test_cfg_not_in_argv(schema, monkeypatch):
    '''Test when -cfg flag is enabled but not provided in argv.'''
    monkeypatch.setattr('sys.argv', ['testprog', '-test', 'value'])

    new_schema = schema.create_cmdline("testprog", use_cfg=True)

    # Should create a new schema, not load from cfg
    assert new_schema.get('test0', 'test1') == 'value'


def test_cfg_at_end_of_argv(schema, monkeypatch):
    '''Test when -cfg is at the end without a file.'''
    check_schema = schema()
    check_schema.set("test4", True)
    check_schema.write_manifest("test3.json")

    # -cfg is the last arg - no file follows, so it should be ignored
    # and argparse will handle it
    monkeypatch.setattr('sys.argv', ['testprog', '-test', 'value', '-cfg'])

    # This should raise an error from argparse since -cfg requires an argument
    with pytest.raises(SystemExit):
        schema.create_cmdline("testprog", use_cfg=True)


def test_use_sources_false_no_input(schema, monkeypatch):
    '''Test use_sources=False prevents input files from being added.'''
    monkeypatch.setattr('sys.argv', ['testprog', '-test', 'value'])

    new_schema = schema.create_cmdline("testprog", use_sources=False)

    # Should not have 'input' in cmdarg keys if there's no cmdarg at all
    try:
        cmdarg_keys = new_schema.getkeys("cmdarg")
        assert "input" not in cmdarg_keys
    except KeyError:
        # cmdarg doesn't exist, which is also fine
        pass
    assert new_schema.get('test0', 'test1') == 'value'


def test_use_sources_with_schema_without_cmdarg(monkeypatch):
    '''Test use_sources when the schema doesn't have cmdarg initially.'''
    class SimpleSchema(CommandLineSchema, BaseSchema):
        def __init__(self):
            super().__init__()
            # Don't add any cmdarg parameters

    monkeypatch.setattr('sys.argv', ['testprog', 'file1.txt'])

    new_schema = SimpleSchema.create_cmdline("testprog", use_sources=True)

    # Should have added input parameter
    assert new_schema.get("cmdarg", "input") == ["file1.txt"]


def test_use_sources_when_getkeys_raises_error(monkeypatch):
    '''Test use_sources when schema.getkeys() raises a KeyError for cmdarg.'''
    class SchemaWithCmdargButNoInput(CommandLineSchema, BaseSchema):
        def __init__(self):
            super().__init__()
            # Add a cmdarg but not input
            schema = EditableSchema(self)
            schema.insert("cmdarg", "other", Parameter("str"))

    monkeypatch.setattr('sys.argv', ['testprog', 'file1.txt'])

    new_schema = SchemaWithCmdargButNoInput.create_cmdline("testprog", use_sources=True)

    # Should have added input parameter even though cmdarg exists
    assert new_schema.get("cmdarg", "input") == ["file1.txt"]
    assert new_schema.get("cmdarg", "other") is None  # default value


def test_use_sources_when_schema_getkeys_fails(monkeypatch):
    '''Test exception handling when getkeys itself raises a KeyError.'''
    class BrokenSchema(CommandLineSchema, BaseSchema):
        def __init__(self):
            super().__init__()

        def getkeys(self, *keypath):
            # Simulate a broken getkeys that raises KeyError
            raise KeyError("Simulated error")

    monkeypatch.setattr('sys.argv', ['testprog', 'file1.txt'])

    new_schema = BrokenSchema.create_cmdline("testprog", use_sources=True)

    # Should still add input parameter despite the error
    assert new_schema.get("cmdarg", "input") == ["file1.txt"]
