import os.path

from pathlib import Path

from siliconcompiler.design import DesignSchema


def test_design_keys():

    golden_keys = sorted([('fileset', 'default', 'file', 'default'),
                          ('fileset', 'default', 'topmodule'),
                          ('fileset', 'default', 'libdir'),
                          ('fileset', 'default', 'lib'),
                          ('fileset', 'default', 'idir'),
                          ('fileset', 'default', 'define'),
                          ('fileset', 'default', 'undefine'),
                          ('fileset', 'default', 'param', 'default'),
                          ('dependency',)
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

    # dependency
    val = ['mylib']
    assert d.set('dependency', val)
    assert d.get('dependency') == val


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
    d.set_fileset(fileset)

    # top module
    top = 'mytop'
    d.set_topmodule(top)
    assert d.get_topmodule(fileset) == top

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    d.set_idir(idirs)
    assert d.get_idir(fileset) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    d.set_libdir(libdirs)
    assert d.get_libdir(fileset) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    d.set_lib(libs)
    assert d.get_lib(fileset) == libs

    # define
    defs = ['CFG_TARGET=FPGA']
    d.set_define(defs)
    assert d.get_define(fileset) == defs

    # undefine
    undefs = ['CFG_TARGET']
    d.set_undefine(undefs)
    assert d.get_undefine(fileset) == undefs


def test_param():

    d = DesignSchema("test")

    fileset = 'rtl'
    d.set_fileset(fileset)

    # param
    name = 'N'
    val = '2'
    d.set_param(name, val)
    assert d.get_param(name, fileset) == val


def test_use():

    lib = DesignSchema('mylib')
    lib.set_fileset('rtl')
    lib.add_file('mylib.v')

    d = DesignSchema("test")
    d.use(lib)
    lib = d.depends('mylib')
    assert lib[0].get_file(fileset='rtl') == ['mylib.v']


def test_write(datadir):

    d = DesignSchema("test")

    d.set_fileset('rtl')
    d.add_file(['data/heartbeat.v', 'data/increment.v'])
    d.set_define('ASIC')
    d.set_idir('./data')
    d.set_topmodule('heartbeat')

    d.set_fileset('tb')
    d.add_file(['data/tb.v'])
    d.set_define('VERILATOR')

    d.write("heartbeat.f", fileset=['rtl', 'tb'])

    golden = Path(os.path.join(datadir, 'heartbeat.f'))
    assert Path('heartbeat.f').read_text() == golden.read_text()


def test_heartbeat_example(datadir):
    datadir = Path(datadir)

    class Increment(DesignSchema):
        def __init__(self):
            super().__init__('increment')

            # rtl
            self.set_fileset('rtl')
            self.set_topmodule('increment')
            self.add_file(datadir / 'increment.v')

    class Heartbeat(DesignSchema):
        def __init__(self):
            super().__init__('heartbeat')

            # rtl
            self.set_fileset('rtl')
            self.set_topmodule('heartbeat')
            self.add_file(datadir / 'heartbeat_increment.v')

            # constraints
            self.set_fileset('constraint')
            self.add_file(datadir / 'heartbeat.sdc')

            # tb
            self.set_fileset('testbench')
            self.set_topmodule('tb')
            self.add_file(datadir / 'heartbeat_tb.v')

            # dependencies
            self.use(Increment())

    dut = Heartbeat()
    assert dut.get("dependency") == ["increment"]
