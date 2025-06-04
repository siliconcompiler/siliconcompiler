from siliconcompiler.design import DesignSchema

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

def test_option():

    d = DesignSchema()

    mytop='mytop'
    d.option(fileset='rtl', topmodule=mytop)
    assert d.get('fileset', 'rtl', 'topmodule') == mytop

    mydirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    d.option(fileset='rtl', idir=mydirs)
    assert d.get('fileset', 'rtl', 'idir') == mydirs

def test_use():

    lib = DesignSchema('lib')
    lib.add_file('lib.v')

    d = DesignSchema()
    d.use(lib)
    assert d.dependency[lib.name].get('fileset', 'rtl', 'file', 'verilog') == ['lib.v']
