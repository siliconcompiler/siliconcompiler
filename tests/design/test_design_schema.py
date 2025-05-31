from siliconcompiler.design import DesignSchema


def test_keys():
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


def test_setget():
    schema = DesignSchema()

    # top module
    top = 'mytop'
    assert schema.set('rtl', 'top', top)
    assert schema.get('rtl', 'top') == top

    # files
    files = ['one.v', 'two.v']
    assert schema.set('rtl', 'file', 'verilog', files)
    assert schema.get('rtl', 'file', 'verilog') == files

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    assert schema.set('rtl', 'idir', idirs)
    assert schema.get('rtl', 'idir', ) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    assert schema.set('hls', 'libdir', libdirs)
    assert schema.get('hls', 'libdir', ) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    assert schema.set('rtl', 'lib', libs)
    assert schema.get('rtl', 'lib', ) == libs

    # libext
    libexts = ['sv', 'v']
    assert schema.set('rtl', 'lib', libexts)
    assert schema.get('rtl', 'lib', ) == libexts

    # define
    defs = ['CFG_TARGET=FPGA']
    assert schema.set('rtl', 'define', defs)
    assert schema.get('rtl', 'define') == defs

    # undefine
    undefs = ['CFG_TARGET']
    assert schema.set('rtl', 'undefine', undefs)
    assert schema.get('rtl', 'undefine') == undefs

    # param
    val = '2'
    assert schema.set('rtl', 'param', 'N', val)
    assert schema.get('rtl', 'param', 'N') == val
