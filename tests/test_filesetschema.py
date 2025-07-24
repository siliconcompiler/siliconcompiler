import pytest

import os.path

from pathlib import Path

from siliconcompiler.filesetschema import FileSetSchema
from siliconcompiler.schema import NamedSchema


def test_design_keys():
    golden_keys = set([
        ('fileset', 'default', 'file', 'default'),
        ('dataroot', 'default', 'path'),
        ('dataroot', 'default', 'tag')
    ])

    assert set(FileSetSchema().allkeys()) == golden_keys


def test_add_file_single():
    d = FileSetSchema()

    assert d.add_file('one.v', 'rtl', filetype='verilog')
    assert d.add_file('two.v', 'rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']


def test_add_file_none():
    d = FileSetSchema()

    with pytest.raises(ValueError, match="add_file cannot process None"):
        d.add_file(None, "rtl")


def test_add_file_clobber():
    d = FileSetSchema()

    assert d.add_file('one.v', 'rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v']
    assert d.add_file('two.v', 'rtl', filetype='verilog', clobber=True)
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['two.v']


def test_add_file():
    d = FileSetSchema()

    assert d.add_file(['one.v', 'two.v'], 'rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']


def test_add_file_with_fileset():
    d = FileSetSchema()

    with d.active_fileset("rtl"):
        assert d.add_file(['one.v', 'two.v'], filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']


def test_add_file_with_fileset_with_dataroot():
    d = FileSetSchema()

    d.set_dataroot("root", __file__)

    with d.active_dataroot("root"):
        with d.active_fileset("rtl"):
            assert d.add_file(['one.v', 'two.v'], filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']
    assert d.get('fileset', 'rtl', 'file', 'verilog', field='package') == ['root', 'root']


def test_add_file_with_fileset_with_dataroot_passed():
    d = FileSetSchema()

    d.set_dataroot("root", __file__)
    d.set_dataroot("test", __file__)

    with d.active_dataroot("root"):
        with d.active_fileset("rtl"):
            assert d.add_file(['one.v', 'two.v'], filetype='verilog', dataroot="test")
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']
    assert d.get('fileset', 'rtl', 'file', 'verilog', field='package') == ['test', 'test']


def test_add_file_with_filetype():
    d = FileSetSchema()

    assert d.add_file(['tb.v', 'dut.v'], 'testbench')
    assert d.get('fileset', 'testbench', 'file', 'verilog') == ['tb.v', 'dut.v']


def test_add_file_invalid_filetype():
    d = FileSetSchema()

    with pytest.raises(ValueError, match="Unrecognized file extension: ver"):
        d.add_file('tb.ver', 'testbench')


def test_add_file_invalid_fileset():
    d = FileSetSchema()

    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.add_file('tb.ver', 3)


def test_get_file_multiple_filesets():
    d = FileSetSchema()

    Path("one.v").touch()
    Path("tb.v").touch()
    Path("one.vhdl").touch()

    d.add_file(['one.v'], 'rtl', filetype='verilog')
    d.add_file(['tb.v'], 'testbench')
    d.add_file(['one.vhdl'], 'rtl')

    assert d.get_file(fileset=['rtl', 'testbench']) == [
        os.path.abspath('one.v'),
        os.path.abspath('one.vhdl'),
        os.path.abspath('tb.v')
    ]


def test_get_file_one_fileset():
    d = FileSetSchema()

    Path("one.v").touch()
    Path("one.vhdl").touch()

    d.add_file(['one.v'], 'rtl', filetype='verilog')
    d.add_file(['tb.v'], 'testbench')
    d.add_file(['one.vhdl'], 'rtl')

    assert d.get_file(fileset='rtl') == [
        os.path.abspath('one.v'),
        os.path.abspath('one.vhdl')
    ]


def test_get_file_filetype():
    d = FileSetSchema()

    Path("one.v").touch()

    d.add_file(['one.v'], 'rtl', filetype='verilog')
    d.add_file(['tb.v'], 'testbench')
    d.add_file(['one.vhdl'], 'rtl')

    # get verilog rtl only
    assert d.get_file(fileset='rtl', filetype='verilog') == [os.path.abspath('one.v')]


def test_get_file_filetype_vhdl():
    d = FileSetSchema()

    Path("one.vhdl").touch()

    d.add_file(['one.v'], 'rtl', filetype='verilog')
    d.add_file(['tb.v'], 'testbench')
    d.add_file(['one.vhdl'], 'rtl')

    # get verilog rtl only
    assert d.get_file(fileset=['rtl', 'testbench'], filetype='vhdl') == [
        os.path.abspath('one.vhdl')
    ]


def test_get_file_one_invalid_fileset():
    with pytest.raises(ValueError, match="fileset key must be a string"):
        FileSetSchema().get_file(fileset=4)


def test_active_fileset_invalid_none():
    with pytest.raises(TypeError, match="fileset must a string"):
        with FileSetSchema().active_fileset(None):
            pass


def test_active_fileset_invalid_empty():
    with pytest.raises(ValueError, match="fileset cannot be an empty string"):
        with FileSetSchema().active_fileset(""):
            pass


def test_add_file_active_fileset():
    d = FileSetSchema()

    Path('one.v').touch()
    Path('two.v').touch()

    with d.active_fileset("rtl"):
        # explicit file add
        d.add_file(['one.v', 'two.v'], filetype='verilog')
        assert d.get_file(filetype="verilog") == [
            os.path.abspath("one.v"),
            os.path.abspath("two.v")
        ]
    assert d.get('fileset', "rtl", 'file', 'verilog') == [
        "one.v",
        "two.v"
    ]

    Path('tb.v').touch()
    Path('dut.v').touch()

    with d.active_fileset("testbench"):
        # filetype mapping
        d.add_file('tb.v')
        d.add_file('dut.v')
        assert d.get_file() == [
            os.path.abspath("tb.v"),
            os.path.abspath("dut.v")
        ]
    assert d.get('fileset', 'testbench', 'file', 'verilog') == ['tb.v', 'dut.v']


def test_copy_fileset():
    schema = FileSetSchema()

    with schema.active_fileset("rtl"):
        assert schema.add_file("top.v")

    schema.copy_fileset("rtl", "rtl.other")
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v"]

    with schema.active_fileset("rtl.other"):
        assert schema.add_file("test.v")

    assert schema.get("fileset", "rtl", "file", "verilog") == ["top.v"]
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v", "test.v"]


def test_copy_fileset_fail_overwrite():
    schema = FileSetSchema()

    with schema.active_fileset("rtl"):
        assert schema.add_file("top.v")

    with pytest.raises(ValueError, match="rtl already exists"):
        schema.copy_fileset("rtl", "rtl")


def test_copy_fileset_overwrite():
    schema = FileSetSchema()

    with schema.active_fileset("rtl"):
        assert schema.add_file("top.v")

    schema.copy_fileset("rtl", "rtl.other")
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v"]

    with schema.active_fileset("rtl.other"):
        assert schema.add_file("test.v")

    assert schema.get("fileset", "rtl", "file", "verilog") == ["top.v"]
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v", "test.v"]

    schema.copy_fileset("rtl.other", "rtl", clobber=True)

    assert schema.get("fileset", "rtl", "file", "verilog") == ["top.v", "test.v"]
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v", "test.v"]


def test_assert_fileset_pass():
    schema = FileSetSchema()

    with schema.active_fileset("rtl"):
        assert schema.add_file("top.v")
    schema._assert_fileset("rtl")


def test_assert_fileset_fail():
    with pytest.raises(LookupError, match="^rtl is not defined$"):
        FileSetSchema()._assert_fileset("rtl")


def test_assert_fileset_failwith_name():
    class Test(FileSetSchema, NamedSchema):
        def __init__(self):
            super().__init__()
            self.set_name("thisname")

    with pytest.raises(LookupError, match="^rtl is not defined in thisname$"):
        Test()._assert_fileset("rtl")


def test_assert_fileset_with_none():
    with pytest.raises(TypeError, match="^fileset must be a string$"):
        FileSetSchema()._assert_fileset(None)


def test_assert_fileset_with_int():
    with pytest.raises(TypeError, match="^fileset must be a string$"):
        FileSetSchema()._assert_fileset(1)
