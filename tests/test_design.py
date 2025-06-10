import re
import os.path
from pathlib import Path
import pytest
from siliconcompiler.design import DesignSchema


def test_design_keys():

    golden_keys = sorted([('fileset', 'default', 'file', 'default'),
                          ('fileset', 'default', 'topmodule'),
                          ('fileset', 'default', 'libdir'),
                          ('fileset', 'default', 'lib'),
                          ('fileset', 'default', 'idir'),
                          ('fileset', 'default', 'define'),
                          ('fileset', 'default', 'undefine'),
                          ('fileset', 'default', 'param', 'default')
                          ])

    assert sorted(DesignSchema("test").allkeys()) == golden_keys


def test_design_values():
    d = DesignSchema("test")

    # top module
    top = 'mytop'
    assert d.set('fileset', 'rtl', 'topmodule', top)
    assert d.get('fileset', 'rtl', 'topmodule') == top

    # files
    files = ['one.v', 'two.v']
    assert d.set('fileset', 'rtl', 'file', 'verilog', files)
    assert d.get('fileset', 'rtl', 'file', 'verilog') == files

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    assert d.set('fileset', 'rtl', 'idir', idirs)
    assert d.get('fileset', 'rtl', 'idir', ) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    assert d.set('fileset', 'hls', 'libdir', libdirs)
    assert d.get('fileset', 'hls', 'libdir', ) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    assert d.set('fileset', 'rtl', 'lib', libs)
    assert d.get('fileset', 'rtl', 'lib', ) == libs

    # define
    defs = ['CFG_TARGET=FPGA']
    assert d.set('fileset', 'rtl', 'define', defs)
    assert d.get('fileset', 'rtl', 'define') == defs

    # undefine
    undefs = ['CFG_TARGET']
    assert d.set('fileset', 'rtl', 'undefine', undefs)
    assert d.get('fileset', 'rtl', 'undefine') == undefs

    # param
    val = '2'
    assert d.set('fileset', 'rtl', 'param', 'N', val)
    assert d.get('fileset', 'rtl', 'param', 'N') == val


def test_add_file():
    d = DesignSchema("test")

    # explicit file add
    files = ['one.v', 'two.v']
    d.add_file('rtl', files, filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == files

    # filetype mapping
    files = ['tb.v', 'dut.v']
    d.add_file('testbench', files)
    assert d.get('fileset', 'testbench', 'file', 'verilog') == files


def test_get_file():
    d = DesignSchema("test")

    d.add_file('rtl', ['one.v'], filetype='verilog')
    d.add_file('testbench', ['tb.v'])
    d.add_file('rtl', ['one.vhdl'])

    # get all files
    assert d.get_file(fileset=['rtl', 'testbench']) == (['one.v'] +
                                                        ['one.vhdl'] +
                                                        ['tb.v'])
    # get rtl only
    assert d.get_file(fileset='rtl') == ['one.v'] + ['one.vhdl']

    # get verilog rtl only
    assert d.get_file(fileset='rtl', filetype='verilog') == ['one.v']


def test_options():

    d = DesignSchema("test")

    # create fileset context
    fileset = 'rtl'

    # top module
    top = 'mytop'
    d.set_topmodule(fileset, top)
    assert d.get_topmodule(fileset) == top

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    d.set_idir(fileset, idirs)
    assert d.get_idir(fileset) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    d.set_libdir(fileset, libdirs)
    assert d.get_libdir(fileset) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    d.set_lib(fileset, libs)
    assert d.get_lib(fileset) == libs

    # define
    defs = ['CFG_TARGET=FPGA']
    d.set_define(fileset, defs)
    assert d.get_define(fileset) == defs

    # undefine
    undefs = ['CFG_TARGET']
    d.set_undefine(fileset, undefs)
    assert d.get_undefine(fileset) == undefs


def test_errors():

    d = DesignSchema("test")

    # check invalid fileset types
    for item in [None, [], (0, 1), 1.1]:
        with pytest.raises(ValueError, match="fileset key must be a string"):
            d.set_topmodule(item, "aaaa")
        with pytest.raises(ValueError, match="fileset key must be a string"):
            d.get_topmodule(item)

    # checking general types
    for value in [None, (0, 1), 1.1]:
        with pytest.raises(ValueError, match="value type must be str or List"):
            d.set_libdir("aaaa", value)
        with pytest.raises(ValueError, match="value type must be str or List"):
            d.set_topmodule("aaaa", value)

    # check valid topmodule strings
    for value in ["0abc", "abc$", ""]:
        with pytest.raises(ValueError, match=re.escape(f"{value} is not a legal topmodule string")):
            d.set_topmodule("aaaa", value)

    # check valid filename
    with pytest.raises(ValueError, match="add_file cannot process None"):
        d.add_file("aaaa", None)

    # check valid extension
    with pytest.raises(ValueError, match="illegal file extension"):
        d.add_file("aaaa", "tmp.badex")


def test_param():

    d = DesignSchema("test")

    name = 'N'
    val = '2'
    fileset = 'rtl'

    d.set_param(fileset, name, val)
    assert d.get_param(fileset, name) == val


@pytest.mark.skip(reason="waiting for use schema impl")
def test_use():

    fileset = 'rtl'
    lib = DesignSchema('mylib')
    lib.add_file('mylib.v', fileset)

    d = DesignSchema("test")
    d.use(lib)
    lib = d.depends('mylib')
    assert lib[0].get_file(fileset) == ['mylib.v']


def test_write_fileset(datadir):

    d = DesignSchema("test")

    fileset = 'rtl'
    d.add_file(fileset, ['data/heartbeat.v', 'data/increment.v'])
    d.set_define(fileset, 'ASIC')
    d.set_idir(fileset, './data')
    d.set_topmodule(fileset, 'heartbeat')

    fileset = 'tb'
    d.add_file(fileset, ['data/tb.v'])
    d.set_define(fileset, 'VERILATOR')

    d.write_fileset(fileset=['rtl', 'tb'], filename="heartbeat.f")

    golden = Path(os.path.join(datadir, 'heartbeat.f'))
    assert Path('heartbeat.f').read_text() == golden.read_text()


@pytest.mark.skip(reason="waiting for use schema impl")
def test_heartbeat_example(datadir):
    datadir = Path(datadir)

    class Increment(DesignSchema):
        def __init__(self):
            super().__init__('increment')

            # rtl
            fileset = 'rtl'
            self.set_topmodule('increment', fileset)
            self.add_file(datadir / 'increment.v', fileset)

    class Heartbeat(DesignSchema):
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
            self.use(Increment())

    dut = Heartbeat()
    assert 'increment' in dut.__dependency
