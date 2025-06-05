from siliconcompiler.design import DesignSchema, Options

def test_add_file():
    d = DesignSchema()

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


def test_options():

    d = DesignSchema()

    # create fileset context
    d.set_fileset('rtl')

    # top module
    top = 'mytop'
    d.set_option(Options.topmodule, top)
    assert d.get_option(Options.topmodule) == top

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    d.set_option(Options.idir, idirs)
    assert d.get_option(Options.idir) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    d.set_option(Options.libdir, libdirs)
    assert d.get_option(Options.libdir) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    d.set_option(Options.lib, libs)
    assert d.get_option(Options.lib) == libs

    # define
    defs = ['CFG_TARGET=FPGA']
    d.set_option(Options.define, defs)
    assert d.get_option(Options.define) == defs

    # undefine
    undefs = ['CFG_TARGET']
    d.set_option(Options.undefine, undefs)
    assert d.get_option(Options.undefine) == undefs

def test_param():

    d = DesignSchema()

    d.set_fileset('rtl')

    # param
    name = 'N'
    val = '2'
    d.set_param(name, val)
    assert d.get_param(name)  == val

def test_use():

    lib = DesignSchema('lib')
    lib.add_file('lib.v')

    #d = DesignSchema()
    #d.use(lib)
    #assert d.dependency[lib.name].get('fileset', 'rtl', 'file', 'verilog') == ['lib.v']

def test_export():

    lib = DesignSchema('lib')
    lib.add_file('lib.v')

    #d = DesignSchema()
    #d.use(lib)
    #assert d.dependency[lib.name].get('fileset', 'rtl', 'file', 'verilog') == ['lib.v']
