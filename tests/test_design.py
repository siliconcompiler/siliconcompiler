import pytest
import re
import shutil

import os.path

from pathlib import Path

from siliconcompiler import Design
from siliconcompiler.schema import BaseSchema


def test_design_keys():
    golden_keys = set([
        ('deps',),
        ('fileset', 'default', 'file', 'default'),
        ('fileset', 'default', 'topmodule'),
        ('fileset', 'default', 'libdir'),
        ('fileset', 'default', 'lib'),
        ('fileset', 'default', 'idir'),
        ('fileset', 'default', 'define'),
        ('fileset', 'default', 'undefine'),
        ('fileset', 'default', 'param', 'default'),
        ('fileset', 'default', 'depfileset'),
        ('dataroot', 'default', 'path'),
        ('dataroot', 'default', 'tag'),
        ('package', 'author', 'default', 'email'),
        ('package', 'author', 'default', 'name'),
        ('package', 'author', 'default', 'organization'),
        ('package', 'description'),
        ('package', 'doc', 'datasheet'),
        ('package', 'doc', 'quickstart'),
        ('package', 'doc', 'reference'),
        ('package', 'doc', 'releasenotes'),
        ('package', 'doc', 'signoff'),
        ('package', 'doc', 'testplan'),
        ('package', 'doc', 'tutorial'),
        ('package', 'doc', 'userguide'),
        ('package', 'license'),
        ('package', 'licensefile'),
        ('package', 'vendor'),
        ('package', 'version')
    ])

    assert set(Design("test").allkeys()) == golden_keys


@pytest.mark.parametrize("arg,value", [
    (("topmodule",), "mytop"),
    (("file", "verilog"), ['one.v', 'two.v']),
    (("idir",), ['/home/acme/incdir1', '/home/acme/incdir2']),
    (("libdir",), ['/usr/lib']),
    (("lib",), ['lib1', 'lib2']),
    (("define",), ['CFG_TARGET=FPGA']),
    (("undefine",), ['CFG_TARGET']),
    (("param", "N"), "64"),
])
def test_design_values(arg, value):
    design = Design("test")

    assert design.set("fileset", "rtl", *arg, value)
    assert design.get("fileset", "rtl", *arg) == value


def test_options_topmodule():
    d = Design("test")

    assert d.set_topmodule('mytop', 'rtl')
    assert d.get_topmodule('rtl') == 'mytop'


def test_options_topmodule_with_fileset():
    d = Design("test")

    with d.active_fileset("rtl"):
        assert d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'
    assert d.get_topmodule('rtl') == 'mytop'


def test_options_topmodule_fileset_error():
    d = Design("test")

    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.set_topmodule('mytop', 2.3)
    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.get_topmodule(2.3)


def test_options_topmodule_value_error():
    d = Design("test")

    with pytest.raises(ValueError, match="value must be of type string"):
        d.set_topmodule(4, "rtl")


def test_options_topmodule_with_none():
    with pytest.raises(ValueError, match="value must be of type string"):
        Design("test").set_topmodule(None, 'rtl')


@pytest.mark.parametrize("name", [
    "0abc", "abc$", ""
])
def test_options_topmodule_invalid_name(name):
    with pytest.raises(ValueError, match=re.escape(f"{name} is not a legal topmodule string")):
        Design("test").set_topmodule(name, "rtl")


def test_options_idir():
    d = Design("test")

    os.makedirs("incdir1", exist_ok=True)
    os.makedirs("incdir2", exist_ok=True)

    for item in ["incdir1", "incdir2"]:
        assert d.add_idir(item, 'rtl')
    assert d.get_idir('rtl') == [os.path.abspath("incdir1"), os.path.abspath("incdir2")]
    assert d.has_idir('rtl0') is False
    assert d.has_idir('rtl') is True


def test_options_idir_with_fileset():
    d = Design("test")

    os.makedirs("incdir1", exist_ok=True)
    os.makedirs("incdir2", exist_ok=True)

    with d.active_fileset("rtl"):
        for item in ["incdir1", "incdir2"]:
            assert d.add_idir(item)
        assert d.get_idir() == [os.path.abspath("incdir1"), os.path.abspath("incdir2")]
    assert d.get_idir('rtl') == [os.path.abspath("incdir1"), os.path.abspath("incdir2")]


def test_options_idir_with_none():
    with pytest.raises(ValueError, match="value must be of type string"):
        Design("test").add_idir(None, 'rtl')


def test_options_idir_fileset_error():
    d = Design("test")

    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.add_idir('mytop', 2.3)
    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.get_idir(2.3)


def test_options_idir_value_error():
    d = Design("test")

    with pytest.raises(ValueError, match="value must be of type string"):
        d.add_idir(4, "rtl")


def test_options_libdir():
    d = Design("test")

    os.makedirs("lib1", exist_ok=True)
    os.makedirs("lib2", exist_ok=True)

    for item in ["lib1", "lib2"]:
        assert d.add_libdir(item, 'rtl')
    assert d.get_libdir('rtl') == [os.path.abspath("lib1"), os.path.abspath("lib2")]
    assert d.has_libdir('rtl0') is False
    assert d.has_libdir('rtl') is True


def test_options_libdir_with_none():
    with pytest.raises(ValueError, match="value must be of type string"):
        Design("test").add_libdir(None, 'rtl')


def test_options_libdir_with_fileset():
    d = Design("test")

    os.makedirs("lib1", exist_ok=True)
    os.makedirs("lib2", exist_ok=True)

    with d.active_fileset("rtl"):
        for item in ["lib1", "lib2"]:
            assert d.add_libdir(item)
        assert d.get_libdir() == [os.path.abspath("lib1"), os.path.abspath("lib2")]
    assert d.get_libdir('rtl') == [os.path.abspath("lib1"), os.path.abspath("lib2")]


def test_options_lib():
    d = Design("test")

    for item in ['lib1', 'lib2']:
        assert d.add_lib(item, 'rtl')
    assert d.get_lib('rtl') == ['lib1', 'lib2']


def test_options_lib_with_none():
    with pytest.raises(ValueError, match="value must be of type string"):
        Design("test").add_lib(None, 'rtl')


def test_options_lib_with_fileset():
    d = Design("test")

    with d.active_fileset("rtl"):
        for item in ['lib1', 'lib2']:
            assert d.add_lib(item)
        assert d.get_lib() == ['lib1', 'lib2']
    assert d.get_lib('rtl') == ['lib1', 'lib2']


def test_options_define():
    d = Design("test")

    for item in ['CFG_TARGET=FPGA', 'VERILATOR']:
        assert d.add_define(item, 'rtl')
    assert d.get_define('rtl') == ['CFG_TARGET=FPGA', 'VERILATOR']


def test_options_define_with_none():
    with pytest.raises(ValueError, match="value must be of type string"):
        Design("test").add_define(None, 'rtl')


def test_options_define_with_fileset():
    d = Design("test")

    with d.active_fileset("rtl"):
        for item in ['CFG_TARGET=FPGA', 'VERILATOR']:
            assert d.add_define(item)
        assert d.get_define() == ['CFG_TARGET=FPGA', 'VERILATOR']
    assert d.get_define('rtl') == ['CFG_TARGET=FPGA', 'VERILATOR']


def test_options_undefine():
    d = Design("test")

    for item in ['CFG_TARGET', 'CFG_SIM']:
        assert d.add_undefine(item, 'rtl')
    assert d.get_undefine('rtl') == ['CFG_TARGET', 'CFG_SIM']


def test_options_undefine_with_none():
    with pytest.raises(ValueError, match="value must be of type string"):
        Design("test").add_undefine(None, 'rtl')


def test_options_undefine_with_fileset():
    d = Design("test")

    with d.active_fileset("rtl"):
        for item in ['CFG_TARGET', 'CFG_SIM']:
            assert d.add_undefine(item)
        assert d.get_undefine() == ['CFG_TARGET', 'CFG_SIM']
    assert d.get_undefine('rtl') == ['CFG_TARGET', 'CFG_SIM']


def test_options_param():
    d = Design("test")

    assert d.set_param('N', '2', 'rtl')
    assert d.get_param('N', 'rtl') == '2'


def test_options_set_param_error_fileset():
    with pytest.raises(ValueError, match="fileset key must be a string"):
        Design("test").set_param('N', '2', 123)


def test_options_set_param_error_param():
    with pytest.raises(ValueError, match="param value must be a string"):
        Design("test").set_param("N", 2, "rtl")


def test_options_get_param_error_fileset():
    with pytest.raises(ValueError, match="fileset key must be a string"):
        Design("test").get_param('N', 123)


def test_options_param_with_fileset():
    d = Design("test")

    with d.active_fileset("rtl"):
        assert d.set_param('N', '2')
        assert d.get_param('N') == '2'
    assert d.get_param('N', 'rtl') == '2'


def test_options_depfileset():
    d = Design("test")
    obj0 = Design("obj0")
    obj0.set_topmodule("test", "rtl")
    obj0.set_topmodule("test", "rtl.tech")
    obj0.set_topmodule("test", "testbench.this")
    d.add_dep(obj0)

    assert d.add_depfileset("obj0", "rtl", "rtl")
    assert d.add_depfileset("obj0", "rtl.tech", "rtl")
    assert d.add_depfileset("obj0", "testbench.this", "testbench")

    assert d.get_depfileset("rtl") == [
        ('obj0', 'rtl'),
        ('obj0', 'rtl.tech')]
    assert d.get_depfileset("testbench") == [('obj0', 'testbench.this')]


def test_options_depfileset_with_object():
    dep = Design("thisdep")
    dep.set_topmodule("test", "rtl")

    d = Design("test")
    assert d.add_depfileset(dep, "rtl", "rtl")
    assert d.get_dep("thisdep") is dep
    assert d.get("fileset", "rtl", "depfileset") == [("thisdep", "rtl")]


def test_options_depfileset_with_self():
    d = Design("test")
    d.set_topmodule("test", "rtl")
    d.set_topmodule("test", "rtl2")
    assert d.add_depfileset(d, "rtl2", "rtl")
    assert d.get("fileset", "rtl", "depfileset") == [("test", "rtl2")]


def test_options_depfileset_with_selfname():
    d = Design("test")
    d.set_topmodule("test", "rtl")
    d.set_topmodule("test", "rtl2")
    assert d.add_depfileset("test", "rtl2", "rtl")
    assert d.get("fileset", "rtl", "depfileset") == [("test", "rtl2")]


def test_options_depfileset_with_invalid_input():
    with pytest.raises(TypeError, match="dep is not a valid type"):
        Design("test").add_depfileset(1, "rtl", "rtl")


def test_options_depfileset_with_fileset():
    d = Design("test")
    obj0 = Design("obj0")
    obj0.set_topmodule("test", "rtl")
    obj0.set_topmodule("test", "rtl.tech")
    obj0.set_topmodule("test", "testbench.this")
    d.add_dep(obj0)

    with d.active_fileset("rtl"):
        assert d.add_depfileset("obj0", "rtl")
        assert d.add_depfileset("obj0", "rtl.tech")
        assert d.get_depfileset() == [
            ('obj0', 'rtl'),
            ('obj0', 'rtl.tech')]
    with d.active_fileset("testbench"):
        assert d.add_depfileset("obj0", "testbench.this")
        assert d.get_depfileset() == [('obj0', 'testbench.this')]

    assert d.get_depfileset("rtl") == [
        ('obj0', 'rtl'),
        ('obj0', 'rtl.tech')]
    assert d.get_depfileset("testbench") == [('obj0', 'testbench.this')]


def test_options_add_depfileset_invalid_fileset():
    d = Design("test")

    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.add_depfileset("obj0", "rtl", fileset=1)


def test_options_get_depfileset_invalid_fileset():
    d = Design("test")

    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.get_depfileset(fileset=1)


def test_add_file_single():
    d = Design("test")

    assert d.add_file('one.v', 'rtl', filetype='verilog')
    assert d.add_file('two.v', 'rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']


def test_add_file_none():
    d = Design("test")

    with pytest.raises(ValueError, match="add_file cannot process None"):
        d.add_file(None, "rtl")


def test_add_file_clobber():
    d = Design("test")

    assert d.add_file('one.v', 'rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v']
    assert d.add_file('two.v', 'rtl', filetype='verilog', clobber=True)
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['two.v']


def test_add_file():
    d = Design("test")

    assert d.add_file(['one.v', 'two.v'], 'rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']


def test_add_file_with_fileset():
    d = Design("test")

    with d.active_fileset("rtl"):
        assert d.add_file(['one.v', 'two.v'], filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == ['one.v', 'two.v']


def test_add_file_with_filetype():
    d = Design("test")

    assert d.add_file(['tb.v', 'dut.v'], 'testbench')
    assert d.get('fileset', 'testbench', 'file', 'verilog') == ['tb.v', 'dut.v']


def test_add_file_default_to_ext():
    d = Design("test")

    assert d.add_file('tb.ver', 'testbench')
    assert d.get("fileset", "testbench", "file", "ver") == ["tb.ver"]


def test_add_file_invalid_fileset():
    d = Design("test")

    with pytest.raises(ValueError, match="fileset key must be a string"):
        d.add_file('tb.ver', 3)


def test_get_file_multiple_filesets():
    d = Design("test")

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
    d = Design("test")

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
    d = Design("test")

    Path("one.v").touch()

    d.add_file(['one.v'], 'rtl', filetype='verilog')
    d.add_file(['tb.v'], 'testbench')
    d.add_file(['one.vhdl'], 'rtl')

    # get verilog rtl only
    assert d.get_file(fileset='rtl', filetype='verilog') == [os.path.abspath('one.v')]


def test_get_file_filetype_vhdl():
    d = Design("test")

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
        Design("test").get_file(fileset=4)


def test_add_dep():

    fileset = 'rtl'
    lib = Design('mylib')
    lib.add_file('mylib.v', fileset)

    Path("mylib.v").touch()

    d = Design("test")
    d.add_dep(lib)
    lib = d.get_dep('mylib')
    assert lib.get_file(fileset) == [os.path.abspath('mylib.v')]


def test_write_fileset_no_filepath():
    with pytest.raises(ValueError, match="filename cannot be None"):
        Design("test").write_fileset(None)


def test_write_fileset_invalid_fileset():
    with pytest.raises(ValueError, match="fileset key must be a string"):
        Design("test").write_fileset("test.f", fileset=[None])


def test_write_fileset_invalid_filetype():
    with pytest.raises(ValueError, match="Unable to determine filetype of: test.invalid"):
        Design("test").write_fileset("test.invalid", fileset="rtl")


def test_write_fileset_invalid_fileformat():
    with pytest.raises(ValueError, match="invalid is not a supported filetype"):
        Design("test").write_fileset("test.f", fileset="rtl", fileformat="invalid")


def test_write_fileset(datadir):
    d = Design("test")
    d.cwd = os.path.dirname(datadir)

    fileset = 'rtl'
    d.add_file(['data/heartbeat.v', 'data/increment.v'], fileset)
    d.add_define('ASIC', fileset)
    d.add_idir('./data', fileset)
    d.set_topmodule('heartbeat', fileset)

    fileset = 'tb'
    d.add_file('data/heartbeat_tb.v', fileset)
    d.add_define('VERILATOR', fileset)

    d.write_fileset(filename="heartbeat.f", fileset=['rtl', 'tb'])

    assert Path("heartbeat.f").read_text().splitlines() == [
        '// test / rtl / include directories',
        f'+incdir+{os.path.abspath(datadir)}',
        '// test / rtl / defines',
        '+define+ASIC',
        '// test / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat.v"))}',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// test / tb / defines',
        '+define+VERILATOR',
        '// test / tb / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}',
    ]


def test_write_fileset_using_fileformat(datadir):
    d = Design("test")
    d.cwd = os.path.dirname(datadir)

    fileset = 'rtl'
    d.add_file(['data/heartbeat.v', 'data/increment.v'], fileset)
    d.add_define('ASIC', fileset)
    d.add_idir('./data', fileset)
    d.set_topmodule('heartbeat', fileset)

    fileset = 'tb'
    d.add_file('data/heartbeat_tb.v', fileset)
    d.add_define('VERILATOR', fileset)

    d.write_fileset(filename="heartbeat.cmd", fileset=['rtl', 'tb'], fileformat="flist")

    assert Path("heartbeat.cmd").read_text().splitlines() == [
        '// test / rtl / include directories',
        f'+incdir+{os.path.abspath(datadir)}',
        '// test / rtl / defines',
        '+define+ASIC',
        '// test / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat.v"))}',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// test / tb / defines',
        '+define+VERILATOR',
        '// test / tb / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}',
    ]


def test_write_fileset_duplicate(datadir):
    d = Design("test")
    d.cwd = os.path.dirname(datadir)

    fileset = 'rtl'
    d.add_file(['data/heartbeat.v', 'data/increment.v'], fileset)
    d.add_define('ASIC', fileset)
    d.add_define('VERILATOR', fileset)
    d.add_idir('./data', fileset)
    d.set_topmodule('heartbeat', fileset)

    fileset = 'tb'
    d.add_file('data/heartbeat_tb.v', fileset)
    d.add_define('VERILATOR', fileset)

    d.write_fileset(filename="heartbeat.f", fileset=['rtl', 'tb'])

    assert Path("heartbeat.f").read_text().splitlines() == [
        '// test / rtl / include directories',
        f'+incdir+{os.path.abspath(datadir)}',
        '// test / rtl / defines',
        '+define+ASIC',
        '+define+VERILATOR',
        '// test / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat.v"))}',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// test / tb / defines',
        '// +define+VERILATOR',
        '// test / tb / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}',
    ]


def test_write_fileset_with_fileset(datadir):
    d = Design("test")
    d.cwd = os.path.dirname(datadir)

    fileset = 'rtl'
    d.add_file(['data/heartbeat.v', 'data/increment.v'], fileset)
    d.add_define('ASIC', fileset)
    d.add_idir('./data', fileset)
    d.set_topmodule('heartbeat', fileset)

    with d.active_fileset("rtl"):
        d.write_fileset(filename="heartbeat.f")

    assert Path("heartbeat.f").read_text().splitlines() == [
        '// test / rtl / include directories',
        f'+incdir+{os.path.abspath(datadir)}',
        '// test / rtl / defines',
        '+define+ASIC',
        '// test / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat.v"))}',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}'
    ]


def test_read_fileset(datadir):
    d = Design("test")

    d.read_fileset(os.path.join(datadir, "heartbeat.f"), fileset="rtl")
    assert d.getkeys("dataroot") == ('flist-test-rtl-heartbeat.f-0', )
    assert d.get("dataroot", "flist-test-rtl-heartbeat.f-0", "path") == os.path.abspath(datadir)
    assert d.get_idir("rtl") == [os.path.abspath(datadir)]
    assert d.get_define("rtl") == ['ASIC']
    assert d.get_file("rtl") == [
        os.path.abspath(os.path.join(datadir, 'heartbeat.v')),
        os.path.abspath(os.path.join(datadir, 'increment.v'))
    ]
    assert d.get("fileset", "rtl", "file", "verilog") == [
        'heartbeat.v',
        'increment.v'
    ]
    assert d.get("fileset", "rtl", "file", "verilog", field="package") == [
        'flist-test-rtl-heartbeat.f-0',
        'flist-test-rtl-heartbeat.f-0'
    ]


def test_read_fileset_with_abspath(datadir):
    d = Design("test")
    d.add_file([datadir + '/heartbeat.v', datadir + '/increment.v'], "rtl")
    d.write_fileset("test.f", fileset="rtl")

    d = Design("new")
    d.read_fileset("test.f", fileset="test")

    assert d.getkeys("dataroot") == ('flist-new-test-test.f-0', )
    assert d.get("dataroot", "flist-new-test-test.f-0", "path") == os.path.abspath(datadir)
    assert d.get_file("test") == [
        os.path.abspath(os.path.join(datadir, 'heartbeat.v')),
        os.path.abspath(os.path.join(datadir, 'increment.v'))
    ]


def test_read_fileset_with_fileset(datadir):
    d = Design("test")

    with d.active_fileset("rtl"):
        d.read_fileset(os.path.join(datadir, "heartbeat.f"))
    assert d.getkeys("dataroot") == ('flist-test-rtl-heartbeat.f-0', )
    assert d.get("dataroot", "flist-test-rtl-heartbeat.f-0", "path") == os.path.abspath(datadir)
    assert d.get_idir("rtl") == [os.path.abspath(datadir)]
    assert d.get_define("rtl") == ['ASIC']
    assert d.get_file("rtl") == [
        os.path.abspath(os.path.join(datadir, 'heartbeat.v')),
        os.path.abspath(os.path.join(datadir, 'increment.v'))
    ]


def test_read_fileset_no_filepath():
    with pytest.raises(ValueError, match="filename cannot be None"):
        Design("test").read_fileset(None)


def test_read_fileset_invalid_filetype():
    with pytest.raises(ValueError, match="Unable to determine filetype of: test.invalid"):
        Design("test").read_fileset("test.invalid")


def test_read_fileset_invalid_fileformat():
    with pytest.raises(ValueError, match="invalid is not a supported filetype"):
        Design("test").read_fileset("test.f", fileformat="invalid")


def test_read_fileset_multiple_packages(datadir):
    d = Design("test")

    os.makedirs("files1", exist_ok=True)
    os.makedirs("files2", exist_ok=True)
    shutil.copy(os.path.join(datadir, "heartbeat.v"), "files1")
    shutil.copy(os.path.join(datadir, "increment.v"), "files2")

    with open("flist.f", "w") as f:
        f.write("files1/heartbeat.v\n")
        f.write("files2/increment.v\n")

    d.read_fileset("flist.f", fileset="rtl")

    assert d.getkeys("dataroot") == ('flist-test-rtl-flist.f-0', 'flist-test-rtl-flist.f-1')
    assert d.get("dataroot", "flist-test-rtl-flist.f-0", "path") == os.path.abspath("files1")
    assert d.get("dataroot", "flist-test-rtl-flist.f-1", "path") == os.path.abspath("files2")
    assert d.get_idir("rtl") == []
    assert d.get_define("rtl") == []
    assert d.get_file("rtl") == [
        os.path.abspath("files1/heartbeat.v"),
        os.path.abspath("files2/increment.v"),
    ]


def test_heartbeat_example(datadir):
    datadir = Path(datadir)

    class Increment(Design):
        def __init__(self):
            super().__init__('increment')

            # rtl
            fileset = 'rtl'
            self.set_topmodule('increment', fileset)
            self.add_file(datadir / 'increment.v', fileset)

    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            # rtl
            fileset = 'rtl'
            self.set_topmodule('heartbeat', fileset)
            self.add_file(datadir / 'heartbeat_increment.v', fileset)

            # constraints
            fileset = 'constraint'
            self.add_file(datadir / 'heartbeat.sdc', fileset)

            # tb
            fileset = 'testbench'
            self.set_topmodule('tb', fileset)
            self.add_file(datadir / 'heartbeat_tb.v', fileset)

            # dependencies
            self.add_dep(Increment())
            with self.active_fileset("rtl"):
                self.add_depfileset("increment", "rtl")

    dut = Heartbeat()
    assert dut.get("deps") == ["increment"]

    dut.write_fileset(filename="heartbeat.f", fileset=['rtl', 'testbench'])

    assert Path("heartbeat.f").read_text().splitlines() == [
        '// heartbeat / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_increment.v"))}',
        '// increment / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// heartbeat / testbench / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}'
    ]


def test_active_fileset_invalid():
    d = Design("test")

    with pytest.raises(TypeError, match="fileset must a string"):
        with d.active_fileset(None):
            pass

    with pytest.raises(ValueError, match="fileset cannot be an empty string"):
        with d.active_fileset(""):
            pass


def test_options_active_fileset():
    d = Design("test")

    # create fileset context
    with d.active_fileset("rtl"):
        # top module
        d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'

        Path("incdir1").mkdir(exist_ok=True)
        Path("incdir2").mkdir(exist_ok=True)

        # idir
        for item in ['incdir1', 'incdir2']:
            d.add_idir(item)
        assert d.get_idir() == [
            os.path.abspath("incdir1"),
            os.path.abspath("incdir2")
        ]

        Path("libdir1").mkdir(exist_ok=True)
        Path("libdir2").mkdir(exist_ok=True)

        # libdirs
        for item in ["libdir1", "libdir2"]:
            d.add_libdir(item)
        assert d.get_libdir() == [
            os.path.abspath("libdir1"),
            os.path.abspath("libdir2")
        ]

        # libs
        libs = ['lib1', 'lib2']
        for item in libs:
            d.add_lib(item)
        assert d.get_lib() == libs

        # define
        defs = ['CFG_TARGET=FPGA', 'VERILATOR']
        for item in defs:
            d.add_define(item)
        assert d.get_define() == defs

        # undefine
        undefs = ['CFG_TARGET', 'CFG_SIM']
        for item in undefs:
            d.add_undefine(item)
        assert d.get_undefine() == undefs


def test_options_active_fileset_overide_context():
    d = Design("test")

    # create fileset context
    with d.active_fileset("rtl"):
        # top module
        d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'
        d.set_topmodule('mytop_other', fileset="notrtl")
        assert d.get_topmodule() == 'mytop'
        assert d.get_topmodule("notrtl") == 'mytop_other'


def test_options_active_fileset_nested():
    d = Design("test")

    # create fileset context
    with d.active_fileset("rtl"):
        # top module
        d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'

        with d.active_fileset("notrtl"):
            d.set_topmodule('mytop_other')
            assert d.get_topmodule() == 'mytop_other'
        assert d.get_topmodule() == 'mytop'
        assert d.get_topmodule("notrtl") == 'mytop_other'


def test_add_file_active_fileset():
    d = Design("test")

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


def test_get_fileset():
    class Increment(Design):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_depfileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")

    dut = Heartbeat()
    assert dut.get_fileset("rtl") == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
    ]

    assert dut.get_fileset(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
        (dut, 'testbench')
    ]

    with pytest.raises(LookupError, match="constraint is not defined in heartbeat"):
        dut.get_fileset("constraint")


def test_get_fileset_self():
    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_depfileset(self, "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")

    dut = Heartbeat()
    assert dut.get_fileset("rtl") == [
        (dut, 'rtl'),
        (dut, 'rtl.increment'),
    ]

    assert dut.get_fileset(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (dut, 'rtl.increment'),
        (dut, 'testbench')
    ]


def test_get_fileset_duplicate():
    class Increment(Design):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_depfileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")
                self.add_depfileset("increment", "rtl.increment")

    dut = Heartbeat()
    assert dut.get_fileset(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
        (dut, 'testbench')
    ]


def test_get_fileset_alias():
    class IncrementAlias(Design):
        def __init__(self):
            super().__init__('increment_alias')

            with self.active_fileset("rtl.alias"):
                self.add_file("alias.v")
            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    class Increment(Design):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_depfileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")
                self.add_depfileset("increment", "rtl.increment")

    dut = Heartbeat()
    assert dut.get_fileset(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
        (dut, 'testbench')
    ]

    alias = IncrementAlias()

    assert dut.get_fileset(
        ["rtl", "testbench"],
        alias={("increment", "rtl.increment"): (alias, "rtl.alias")}) == [
        (dut, 'rtl'),
        (alias, 'rtl.alias'),
        (dut, 'testbench')
    ]
    assert dut.get_fileset(
        ["rtl", "testbench"],
        alias={("increment", "rtl.increment"): (alias, None)}) == [
        (dut, 'rtl'),
        (alias, 'rtl.increment'),
        (dut, 'testbench')
    ]
    assert dut.get_fileset(
        ["rtl", "testbench"],
        alias={("increment", "rtl.increment"): (None, None)}) == [
        (dut, 'rtl'),
        (dut, 'testbench')
    ]


def test_write_fileset_alias(datadir):
    datadir = Path(datadir)

    class IncrementAlias(Design):
        def __init__(self):
            super().__init__('increment_alias')

            with self.active_fileset("rtl.alias"):
                self.add_file(datadir / "increment.v")

            with self.active_fileset("rtl.alias_other"):
                self.add_file(datadir / "increment.v")

    class Increment(Design):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file(datadir / "increment.v")

    incr_object = Increment()

    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file(datadir / "heartbeat_increment.v")
                self.add_depfileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file(datadir / "heartbeat_tb.v")
                self.add_depfileset("increment", "rtl.increment")

    dut = Heartbeat()
    alias = IncrementAlias()

    dut.write_fileset(
        "fileset.f",
        ["rtl", "testbench"],
        depalias={("increment", "rtl.increment"): (alias, "rtl.alias")})

    assert Path("fileset.f").read_text().splitlines() == [
        '// heartbeat / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_increment.v"))}',
        '// increment_alias / rtl.alias / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// heartbeat / testbench / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}',
    ]

    dut.write_fileset(
        "fileset_double.f",
        ["rtl", "testbench"],
        depalias={("increment", "rtl.increment"): (alias, ["rtl.alias", "rtl.alias_other"])})

    assert Path("fileset_double.f").read_text().splitlines() == [
        '// heartbeat / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_increment.v"))}',
        '// increment_alias / rtl.alias / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// increment_alias / rtl.alias_other / verilog files',
        f'// {os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// heartbeat / testbench / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}',
    ]


def test_write_fileset_same_datroot_name(datadir):
    dataroot0 = Path(datadir)
    dataroot1 = Path(dataroot0.parent)

    class Increment(Design):
        def __init__(self):
            super().__init__('increment')

            self.set_dataroot("root", dataroot0)

            with self.active_fileset("rtl.increment"), self.active_dataroot("root"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(Design):
        def __init__(self):
            super().__init__('heartbeat')

            self.set_dataroot("root", dataroot1)

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"), self.active_dataroot("root"):
                self.add_file("data/heartbeat_increment.v")
                self.add_depfileset("increment", "rtl.increment")

            with self.active_fileset("testbench"), self.active_dataroot("root"):
                self.add_file("data/heartbeat_tb.v")

    dut = Heartbeat()

    assert dut.get("dataroot", "root", "path") != incr_object.get("dataroot", "root", "path")

    dut.write_fileset("fileset.f",  ["rtl", "testbench"])

    assert Path("fileset.f").read_text().splitlines() == [
        '// heartbeat / rtl / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_increment.v"))}',
        '// increment / rtl.increment / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "increment.v"))}',
        '// heartbeat / testbench / verilog files',
        f'{os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))}',
    ]


def test_add_dep_invalid():
    schema = Design()

    with pytest.raises(TypeError,
                       match="Cannot add an object of type: <class "
                       "'siliconcompiler.schema.baseschema.BaseSchema'>"):
        schema.add_dep(BaseSchema())


def test_add_dep_same_name():
    schema = Design("name0")

    with pytest.raises(ValueError, match="Cannot add a dependency with the same name"):
        schema.add_dep(Design("name0"))


def test_copy_fileset():
    schema = Design()

    with schema.active_fileset("rtl"):
        assert schema.set_topmodule("top")
        assert schema.add_define("def")
        assert schema.set_param("P", "1")
        assert schema.add_file("top.v")

    schema.copy_fileset("rtl", "rtl.other")
    assert schema.get("fileset", "rtl.other", "topmodule") == "top"
    assert schema.get("fileset", "rtl.other", "define") == ["def"]
    assert schema.get("fileset", "rtl.other", "param", "P") == "1"
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v"]

    with schema.active_fileset("rtl.other"):
        assert schema.set_topmodule("test")

    assert schema.get("fileset", "rtl", "topmodule") == "top"
    assert schema.get("fileset", "rtl.other", "topmodule") == "test"


def test_copy_fileset_fail_overwrite():
    schema = Design()

    with schema.active_fileset("rtl"):
        assert schema.set_topmodule("top")
        assert schema.add_define("def")
        assert schema.set_param("P", "1")
        assert schema.add_file("top.v")

    with pytest.raises(ValueError, match="rtl already exists"):
        schema.copy_fileset("rtl", "rtl")


def test_copy_fileset_overwrite():
    schema = Design()

    with schema.active_fileset("rtl"):
        assert schema.set_topmodule("top")
        assert schema.add_define("def")
        assert schema.set_param("P", "1")
        assert schema.add_file("top.v")

    schema.copy_fileset("rtl", "rtl.other")
    assert schema.get("fileset", "rtl.other", "topmodule") == "top"
    assert schema.get("fileset", "rtl.other", "define") == ["def"]
    assert schema.get("fileset", "rtl.other", "param", "P") == "1"
    assert schema.get("fileset", "rtl.other", "file", "verilog") == ["top.v"]

    with schema.active_fileset("rtl.other"):
        assert schema.set_topmodule("test")

    assert schema.get("fileset", "rtl", "topmodule") == "top"
    schema.copy_fileset("rtl.other", "rtl", clobber=True)
    assert schema.get("fileset", "rtl", "topmodule") == "test"
    assert schema.get("fileset", "rtl.other", "topmodule") == "test"
