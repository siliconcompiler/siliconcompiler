from siliconcompiler.design import DesignSchema


def test_design_keys():
    assert sorted(DesignSchema().getkeys('default')) == sorted([
        'top',
        'file',
        'idir',
        'lib',
        'libdir',
        'libext',
        'define',
        'undefine',
        'param'])


def test_design_params():
    d = DesignSchema()

    # top module
    top = 'mytop'
    assert d.set('rtl', 'top', top)
    assert d.get('rtl', 'top') == top

    # files
    files = ['one.v', 'two.v']
    assert d.set('rtl', 'file', 'verilog', files)
    assert d.get('rtl', 'file', 'verilog') == files

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    assert d.set('rtl', 'idir', idirs)
    assert d.get('rtl', 'idir', ) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    assert d.set('hls', 'libdir', libdirs)
    assert d.get('hls', 'libdir', ) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    assert d.set('rtl', 'lib', libs)
    assert d.get('rtl', 'lib', ) == libs

    # libext
    libexts = ['sv', 'v']
    assert d.set('rtl', 'lib', libexts)
    assert d.get('rtl', 'lib', ) == libexts

    # define
    defs = ['CFG_TARGET=FPGA']
    assert d.set('rtl', 'define', defs)
    assert d.get('rtl', 'define') == defs

    # undefine
    undefs = ['CFG_TARGET']
    assert d.set('rtl', 'undefine', undefs)
    assert d.get('rtl', 'undefine') == undefs

    # param
    val = '2'
    assert d.set('rtl', 'param', 'N', val)
    assert d.get('rtl', 'param', 'N') == val
