import os
import pytest
import json
from pathlib import Path
from siliconcompiler.design import DesignSchema, Option

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
    d.set_option(Option.topmodule, top)
    assert d.get_option(Option.topmodule) == top

    # idir
    idirs = ['/home/acme/incdir1', '/home/acme/incdir2']
    d.set_option(Option.idir, idirs)
    assert d.get_option(Option.idir) == idirs

    # libdirs
    libdirs = ['/usr/lib']
    d.set_option(Option.libdir, libdirs)
    assert d.get_option(Option.libdir) == libdirs

    # libs
    libs = ['lib1', 'lib2']
    d.set_option(Option.lib, libs)
    assert d.get_option(Option.lib) == libs

    # define
    defs = ['CFG_TARGET=FPGA']
    d.set_option(Option.define, defs)
    assert d.get_option(Option.define) == defs

    # undefine
    undefs = ['CFG_TARGET']
    d.set_option(Option.undefine, undefs)
    assert d.get_option(Option.undefine) == undefs

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

    d = DesignSchema()

    golden = Path(__file__).parent/'data'/'heartbeat.f'

    d.set_fileset('rtl')
    d.add_file(['data/heartbeat.v', 'data/increment.v'])
    d.set_option(Option.define, 'ASIC')
    d.set_option(Option.idir, './data')
    d.set_option(Option.topmodule, 'heartbeat')

    d.set_fileset('tb')
    d.add_file(['data/tb.v'])
    d.set_option(Option.define, 'VERILATOR')

    d.export("heartbeat.f", fileset=['rtl', 'tb'])

    assert Path('heartbeat.f').read_text() == golden.read_text()
