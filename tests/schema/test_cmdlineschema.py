import logging
import pytest

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import PerNode
from siliconcompiler.schema import CommandLineSchema


@pytest.fixture
def schema():
    class CLISchema(BaseSchema, CommandLineSchema):
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
                switch=[
                    "-O<int>"]))
            schema.insert("test6", Parameter(
                "str",
                switch=[
                    "-D<str>"]))
            schema.insert("test7", Parameter(
                "dir",
                switch=[
                    "+incdir+<dir>"]))
    return CLISchema


def test_invalid_argument(schema, monkeypatch):
    monkeypatch.setattr('sys.argv', ['testprog', '-trst', 'checkthis'])

    with pytest.raises(SystemExit):
        schema().create_cmdline("testprog")


def test_str(schema, monkeypatch):
    monkeypatch.setattr('sys.argv', ['testprog', '-test', 'checkthis'])
    check_schema = schema()
    args = check_schema.create_cmdline("testprog")

    assert args is None
    assert check_schema.get('test0', 'test1') == 'checkthis'


def test_list(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-test_list', 'checkthis0', '-test_list', 'checkthis1'])
    check_schema = schema()
    args = check_schema.create_cmdline("testprog")

    assert args is None
    assert check_schema.get('test0', 'test2') == ['checkthis0', 'checkthis1']


def test_invalid_argument_in_switchlist(schema):
    with pytest.raises(ValueError, match="-invalid is not a valid commandline argument"):
        schema().create_cmdline("testprog", switchlist=["-invalid"])


def test_addversion(schema, capfd, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-version'])
    with pytest.raises(SystemExit):
        schema().create_cmdline("testprog", version="thisversion")

    assert "thisversion" in capfd.readouterr().out


def test_logmessages(schema, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-test', 'thisargument',
                         '-test_opt', 'globalvalue',
                         '-test_opt', 'thisstep stepvalue',
                         '-test_opt', 'thisstep thisindex stepindexvalue'])
    schema().create_cmdline("testprog", logger=logging.getLogger())

    assert "Command line argument entered: [test0,test1] Value: thisargument\n" in caplog.text
    assert "Command line argument entered: [test3] Value: globalvalue\n" in caplog.text
    assert "Command line argument entered: [test3] Value: stepvalue step: thisstep\n" in caplog.text
    assert "Command line argument entered: [test3] Value: stepindexvalue step: " \
        "thisstep index: thisindex\n" in caplog.text


def test_extra_args(schema, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-extra0', 'thisextra'])
    args = schema().create_cmdline("testprog", logger=logging.getLogger(), additional_args={
        "-extra0": {
            "type": str,
            "dest": "thisdest"
        }
    })

    assert args == {"thisdest": "thisextra"}

    assert "Command line argument entered: \"thisdest\" Value: thisextra\n" in caplog.text


def test_extra_args_no_print(schema, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-extra0', 'thisextra'])
    args = schema().create_cmdline("testprog", logger=logging.getLogger(), additional_args={
        "-extra0": {
            "type": str,
            "dest": "thisdest",
            "sc_print": False
        }
    })

    assert args == {"thisdest": "thisextra"}

    assert "Command line argument entered: \"thisdest\" Value: thisextra\n" not in caplog.text


def test_banner(schema, capfd, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog'])

    def print_banner():
        print("THISBANNER")
    schema().create_cmdline("testprog", print_banner=print_banner)

    assert "THISBANNER" in capfd.readouterr().out


def test_post_process(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-test_bool'])

    def post_process(cmdargs, extra_params):
        assert extra_params is None
        assert cmdargs == {'test4': ['true']}

        return "thisreturn"

    assert schema().create_cmdline("testprog", post_process=post_process) == "thisreturn"


def test_preprocess_keys(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-test_bool'])

    def preprocess_keys(keypath, value):
        assert keypath == ('test4',)
        assert value == "true"

        return "false"

    check_schema = schema()
    check_schema.create_cmdline("testprog", preprocess_keys=preprocess_keys)
    assert check_schema.get('test4') is False


def test_input_map_handler(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', 'file0', 'file1'])

    check_schema = schema()
    assert check_schema.get('test4') is False

    def input_map_handler(files):
        assert files == ['file0', 'file1']

        check_schema.set('test4', True)

    check_schema.create_cmdline("testprog", input_map_handler=input_map_handler)
    assert check_schema.get('test4') is True


def test_read_cfg(schema, monkeypatch):
    check_schema = schema()
    check_schema.set("test4", True)
    check_schema.write_manifest("test.json")

    monkeypatch.setattr('sys.argv',
                        ['testprog', '-cfg', 'test.json'])

    new_schema = schema()
    assert new_schema.get('test4') is False

    new_schema.create_cmdline("testprog")
    assert new_schema.get('test4') is True


def test_loglevel_set_logger(schema, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-loglevel', 'info'])

    new_schema = schema()
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    assert logger.level == logging.CRITICAL
    new_schema.create_cmdline("testprog", logger=logger)
    assert logger.level == logging.INFO


def test_banner_quiet(schema, capfd, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog', '-loglevel', 'quiet'])

    def print_banner():
        print("THISBANNER")
    schema().create_cmdline("testprog", print_banner=print_banner)

    assert "THISBANNER" not in capfd.readouterr().out


def test_custom_args(schema, capfd, monkeypatch):
    monkeypatch.setattr('sys.argv',
                        ['testprog',
                         '-O3',
                         '-DCFG_ASIC=1',
                         '+incdir+/path'])

    new_schema = schema()
    new_schema.create_cmdline("testprog")

    assert new_schema.get('test5') == 3
    assert new_schema.get('test6') == "CFG_ASIC=1"
    assert new_schema.get('test7') == "/path"
