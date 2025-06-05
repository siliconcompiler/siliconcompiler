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
                          ('dependency',) # TODO: why does schema returna  comma for one key?
                          ])

    assert sorted(DesignSchema().allkeys()) == golden_keys


def test_design_values():
    d = DesignSchema()

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
    assert d.get('fileset', 'rtl', 'param', 'N')  == val

    # dependency
    val = ['mylib']
    assert d.set('dependency', val)
    assert d.get('dependency')  == val
