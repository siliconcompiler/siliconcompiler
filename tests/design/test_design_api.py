from pathlib import Path
from siliconcompiler.design import DesignSchema


def test_add_file():
    d = DesignSchema("test")

    # explicit file add
    files = ['one.v', 'two.v']
    d.add_file(files, fileset='rtl', filetype='verilog')
    assert d.get('fileset', 'rtl', 'file', 'verilog') == files

    # filetype mapping
    files = ['tb.v', 'dut.v']
    d.add_file(files, fileset='testbench')
    assert d.get('fileset', 'testbench', 'file', 'verilog') == files

    # filetype and fileset mapping
    files = ['one.vhdl']
    d.add_file(files)
    assert d.get('fileset', 'rtl', 'file', 'vhdl') == files


def test_get_file():
    d = DesignSchema("test")

    d.add_file(['one.v'], fileset='rtl', filetype='verilog')
    d.add_file(['tb.v'], fileset='testbench')
    d.add_file(['one.vhdl'])

    # get all files
    assert d.get_file(fileset=['rtl','testbench']) == (['one.v'] +
                                                       ['one.vhdl'] +
                                                       ['tb.v'])
    # get rtl only
    assert d.get_file(fileset='rtl') == ['one.v'] + ['one.vhdl']

    # get verilog rtl only
    assert d.get_file(fileset='rtl', filetype='verilog') == ['one.v']


def test_options():

    d = DesignSchema("test")

    # create fileset context
    d.set_fileset('rtl')

    # top module
    top = 'mytop'
    d.set_topmodule(top)
    assert d.get_topmodule() == top

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    d.set_idir(idirs)
    assert d.get_idir() == idirs

    # libdirs
    libdirs = ['/usr/lib']
    d.set_libdir(libdirs)
    assert d.get_libdir() == libdirs

    # libs
    libs = ['lib1', 'lib2']
    d.set_lib(libs)
    assert d.get_lib() == libs

    # define
    defs = ['CFG_TARGET=FPGA']
    d.set_define(defs)
    assert d.get_define() == defs

    # undefine
    undefs = ['CFG_TARGET']
    d.set_undefine(undefs)
    assert d.get_undefine() == undefs


def test_param():

    d = DesignSchema("test")

    d.set_fileset('rtl')

    # param
    name = 'N'
    val = '2'
    d.set_param(name, val)
    assert d.get_param(name)  == val


def test_use():

    lib = DesignSchema('mylib')
    lib.set_fileset('rtl')
    lib.add_file('mylib.v')

    d = DesignSchema("test")
    d.use(lib)
    l = d.depends('mylib')
    assert l[0].get_file(fileset='rtl') == ['mylib.v']


def test_write():

    d = DesignSchema("test")

    golden = Path(__file__).parent/'data'/'heartbeat.f'

    d.set_fileset('rtl')
    d.add_file(['data/heartbeat.v', 'data/increment.v'])
    d.set_define('ASIC')
    d.set_idir('./data')
    d.set_topmodule('heartbeat')

    d.set_fileset('tb')
    d.add_file(['data/tb.v'])
    d.set_define('VERILATOR')

    d.write("heartbeat.f", fileset=['rtl', 'tb'])

    assert Path('heartbeat.f').read_text() == golden.read_text()
