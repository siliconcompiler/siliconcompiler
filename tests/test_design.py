import re
import shutil

import os.path
from pathlib import Path
import pytest
from siliconcompiler.design import DesignSchema


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
        ('package', 'default', 'root'),
        ('package', 'default', 'tag'),
    ])

    assert set(DesignSchema("test").allkeys()) == golden_keys


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
    fileset = 'rtl'
    files = ['one.v', 'two.v']
    d.add_file(files, fileset, filetype='verilog')
    assert d.get('fileset', fileset, 'file', 'verilog') == files

    # filetype mapping
    fileset = 'testbench'
    files = ['tb.v', 'dut.v']
    d.add_file(files, fileset)
    assert d.get('fileset', 'testbench', 'file', 'verilog') == files


def test_get_file():
    d = DesignSchema("test")

    d.add_file(['one.v'], 'rtl', filetype='verilog')
    d.add_file(['tb.v'], 'testbench')
    d.add_file(['one.vhdl'], 'rtl')

    # get all files
    assert d.get_file(fileset=['rtl', 'testbench']) == (['one.v'] +
                                                        ['one.vhdl'] +
                                                        ['tb.v'])
    # get rtl only
    assert d.get_file(fileset='rtl') == ['one.v'] + ['one.vhdl']

    # get verilog rtl only
    assert d.get_file(fileset='rtl', filetype='verilog') == ['one.v']


def test_dependency_fileset():
    d = DesignSchema("test")
    assert d.add_dependency_fileset("obj0", "rtl", "rtl")
    assert d.add_dependency_fileset("obj0", "rtl.tech", "rtl")
    assert d.add_dependency_fileset("obj0", "testbench.this", "testbench")

    assert d.get_dependency_fileset("rtl") == [
        ('obj0', 'rtl'),
        ('obj0', 'rtl.tech')]
    assert d.get_dependency_fileset("testbench") == [('obj0', 'testbench.this')]


def test_options():

    d = DesignSchema("test")

    # create fileset context
    fileset = 'rtl'

    # top module
    top = 'mytop'
    d.set_topmodule(top, fileset)
    assert d.get_topmodule(fileset) == top

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    for item in idirs:
        d.add_idir(item, fileset)
    assert d.get_idir(fileset) == idirs

    # libdirs
    libdirs = ['/usr/lib1', '/usr/lib2']
    for item in libdirs:
        d.add_libdir(item, fileset)
    assert d.get_libdir(fileset) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    for item in libs:
        d.add_lib(item, fileset)
    assert d.get_lib(fileset) == libs

    # define
    defs = ['CFG_TARGET=FPGA', 'VERILATOR']
    for item in defs:
        d.add_define(item, fileset)
    assert d.get_define(fileset) == defs

    # undefine
    undefs = ['CFG_TARGET', 'CFG_SIM']
    for item in undefs:
        d.add_undefine(item, fileset)
    assert d.get_undefine(fileset) == undefs


def test_errors():

    d = DesignSchema("test")

    fileset = 'rtl'

    # check invalid fileset types
    dummy = 'mytop'
    for item in [None, [], (0, 1), 1.1]:
        with pytest.raises(ValueError, match="fileset key must be a string"):
            d.set_topmodule(dummy, item)
        with pytest.raises(ValueError, match="fileset key must be a string"):
            d.get_topmodule(item)

    # checking general types
    for value in [None, (0, 1), 1.1]:
        with pytest.raises(ValueError, match="value must be of type string"):
            d.add_libdir(value, fileset)
        with pytest.raises(ValueError, match="value must be of type string"):
            d.set_topmodule(value, fileset)

    # check valid topmodule strings
    for value in ["0abc", "abc$", ""]:
        with pytest.raises(ValueError, match=re.escape(f"{value} is not a legal topmodule string")):
            d.set_topmodule(value, fileset)

    # check valid filename
    with pytest.raises(ValueError, match="add_file cannot process None"):
        d.add_file(None, fileset)

    # check valid extension
    with pytest.raises(ValueError, match="illegal file extension"):
        d.add_file("tmp.badex", fileset)


def test_param():

    d = DesignSchema("test")

    name = 'N'
    val = '2'
    fileset = 'rtl'

    d.set_param(name, val, fileset)
    assert d.get_param(name, fileset) == val


def test_add_dep():

    fileset = 'rtl'
    lib = DesignSchema('mylib')
    lib.add_file('mylib.v', fileset)

    d = DesignSchema("test")
    d.add_dep(lib)
    lib = d.get_dep('mylib')
    assert lib.get_file(fileset) == ['mylib.v']


def test_write_fileset(datadir):
    d = DesignSchema("test")
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


def test_read_fileset(datadir):
    d = DesignSchema("test")

    d.read_fileset(os.path.join(datadir, "heartbeat.f"), fileset="rtl")
    assert d.getkeys("package") == ('flist-test-rtl-heartbeat.f-0', )
    assert d.get("package", "flist-test-rtl-heartbeat.f-0", "root") == os.path.abspath(datadir)
    assert d.get_idir("rtl") == ["."]
    assert d.get_define("rtl") == ['ASIC']
    assert d.get_file("rtl") == ['heartbeat.v', 'increment.v']


def test_read_fileset_multiple_packages(datadir):
    d = DesignSchema("test")

    os.makedirs("files1", exist_ok=True)
    os.makedirs("files2", exist_ok=True)
    shutil.copy(os.path.join(datadir, "heartbeat.v"), "files1")
    shutil.copy(os.path.join(datadir, "increment.v"), "files2")

    with open("flist.f", "w") as f:
        f.write("files1/heartbeat.v\n")
        f.write("files2/increment.v\n")

    d.read_fileset("flist.f", fileset="rtl")

    assert d.getkeys("package") == ('flist-test-rtl-flist.f-0', 'flist-test-rtl-flist.f-1')
    assert d.get("package", "flist-test-rtl-flist.f-0", "root") == os.path.abspath("files1")
    assert d.get("package", "flist-test-rtl-flist.f-1", "root") == os.path.abspath("files2")
    assert d.get_idir("rtl") == []
    assert d.get_define("rtl") == []
    assert d.get_file("rtl") == ['heartbeat.v', 'increment.v']

    assert d.find_files("fileset", "rtl", "file", "verilog") == [
        os.path.abspath("files1/heartbeat.v"),
        os.path.abspath("files2/increment.v"),
    ]


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
            self.add_dep(Increment())
            self.add_dependency_fileset("increment", "rtl", "rtl")

    dut = Heartbeat()
    assert dut.get("deps") == ["increment"]

    dut.write_fileset(filename="heartbeat.f", fileset=['rtl', 'testbench'])

    assert Path("heartbeat.f").read_text().splitlines() == [
        '// heartbeat / rtl / verilog files',
        f'{Path(os.path.abspath(os.path.join(datadir, "heartbeat_increment.v"))).as_posix()}',
        '// increment / rtl / verilog files',
        f'{Path(os.path.abspath(os.path.join(datadir, "increment.v"))).as_posix()}',
        '// heartbeat / testbench / verilog files',
        f'{Path(os.path.abspath(os.path.join(datadir, "heartbeat_tb.v"))).as_posix()}'
    ]


def test_active_fileset_invalid():
    d = DesignSchema("test")

    with pytest.raises(TypeError, match="fileset must a string"):
        with d.active_fileset(None):
            pass

    with pytest.raises(ValueError, match="fileset cannot be an empty string"):
        with d.active_fileset(""):
            pass


def test_options_active_fileset():
    d = DesignSchema("test")

    # create fileset context
    with d.active_fileset("rtl"):
        # top module
        d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'

        # idir
        idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
        for item in idirs:
            d.add_idir(item)
        assert d.get_idir() == idirs

        # libdirs
        libdirs = ['/usr/lib1', '/usr/lib2']
        for item in libdirs:
            d.add_libdir(item)
        assert d.get_libdir() == libdirs

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
    d = DesignSchema("test")

    # create fileset context
    with d.active_fileset("rtl"):
        # top module
        d.set_topmodule('mytop')
        assert d.get_topmodule() == 'mytop'
        d.set_topmodule('mytop_other', fileset="notrtl")
        assert d.get_topmodule() == 'mytop'
        assert d.get_topmodule("notrtl") == 'mytop_other'


def test_options_active_fileset_nested():
    d = DesignSchema("test")

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


def test_options_active_fileset_ensure_no_leftovers():
    d = DesignSchema("test")

    assert d._DesignSchema__fileset is None
    # create fileset context
    with d.active_fileset("rtl"):
        assert d._DesignSchema__fileset == "rtl"
    assert d._DesignSchema__fileset is None


def test_add_file_active_fileset():
    d = DesignSchema("test")

    with d.active_fileset("rtl"):
        # explicit file add
        files = ['one.v', 'two.v']
        d.add_file(files, filetype='verilog')
        assert d.get_file(filetype="verilog") == files
    assert d.get('fileset', "rtl", 'file', 'verilog') == files

    with d.active_fileset("testbench"):
        # filetype mapping
        d.add_file('tb.v')
        d.add_file('dut.v')
        assert d.get_file() == ['tb.v', 'dut.v']
    assert d.get('fileset', 'testbench', 'file', 'verilog') == ['tb.v', 'dut.v']


def test_get_fileset_mapping():
    class Increment(DesignSchema):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(DesignSchema):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_dependency_fileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")

    dut = Heartbeat()
    assert dut.get_fileset_mapping("rtl") == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
    ]

    assert dut.get_fileset_mapping(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
        (dut, 'testbench')
    ]

    with pytest.raises(ValueError, match="constraint is not defined in heartbeat"):
        dut.get_fileset_mapping("constraint")


def test_get_fileset_mapping_duplicate():
    class Increment(DesignSchema):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(DesignSchema):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_dependency_fileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")
                self.add_dependency_fileset("increment", "rtl.increment")

    dut = Heartbeat()
    assert dut.get_fileset_mapping(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
        (dut, 'testbench')
    ]


def test_get_fileset_mapping_alias():
    class IncrementAlias(DesignSchema):
        def __init__(self):
            super().__init__('increment_alias')

            with self.active_fileset("rtl.alias"):
                self.add_file("alias.v")
            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    class Increment(DesignSchema):
        def __init__(self):
            super().__init__('increment')

            with self.active_fileset("rtl.increment"):
                self.add_file("increment.v")

    incr_object = Increment()

    class Heartbeat(DesignSchema):
        def __init__(self):
            super().__init__('heartbeat')

            # dependencies
            self.add_dep(incr_object)
            with self.active_fileset("rtl"):
                self.add_file("heartbeat_increment.v")
                self.add_dependency_fileset("increment", "rtl.increment")

            with self.active_fileset("testbench"):
                self.add_file("tb.v")
                self.add_dependency_fileset("increment", "rtl.increment")

    dut = Heartbeat()
    assert dut.get_fileset_mapping(["rtl", "testbench"]) == [
        (dut, 'rtl'),
        (incr_object, 'rtl.increment'),
        (dut, 'testbench')
    ]

    alias = IncrementAlias()

    assert dut.get_fileset_mapping(
        ["rtl", "testbench"],
        alias={("increment", "rtl.increment"): (alias, "rtl.alias")}) == [
        (dut, 'rtl'),
        (alias, 'rtl.alias'),
        (dut, 'testbench')
    ]
    assert dut.get_fileset_mapping(
        ["rtl", "testbench"],
        alias={("increment", "rtl.increment"): (alias, None)}) == [
        (dut, 'rtl'),
        (alias, 'rtl.increment'),
        (dut, 'testbench')
    ]
    assert dut.get_fileset_mapping(
        ["rtl", "testbench"],
        alias={("increment", "rtl.increment"): (None, None)}) == [
        (dut, 'rtl'),
        (dut, 'testbench')
    ]
