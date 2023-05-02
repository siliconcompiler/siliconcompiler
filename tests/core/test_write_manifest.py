# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import csv

import pytest

import siliconcompiler


def test_write_manifest():

    chip = siliconcompiler.Chip('top')
    chip.input('top.sdc')
    chip.input('top.v')
    chip.input('a.v')
    chip.input('b.v')
    chip.input('c.v')

    chip.write_manifest('top.pkg.json')
    chip.write_manifest('top.csv')
    chip.write_manifest('top.tcl', prune=False)
    chip.write_manifest('top.yaml')


def test_advanced_tcl(monkeypatch):
    # Tkinter module is part of Python standard library, but may not be
    # available depending on if the system has the python3-tk package installed.
    # This line will import tkinter if it's available, and skip the test
    # otherwise.
    tkinter = pytest.importorskip('tkinter')

    chip = siliconcompiler.Chip('top')

    # Test complex strings
    desc = '''This description is potentially problematic since it includes
multiple lines, spaces, and TCL special characters. This package costs $5 {for real}!'''
    chip.set('package', 'description', desc)

    # Test tuples
    chip.add('constraint', 'outline', (0, 0))
    chip.add('constraint', 'outline', (30, 40))

    # Test bools
    chip.set('option', 'quiet', True)

    # Test envvars
    chip.input('rtl/$TOPMOD.v')

    chip.write_manifest('top.tcl')

    # Read from config in TCL as test
    tcl = tkinter.Tcl()

    # Set env var to test ['input', 'verilog']
    monkeypatch.setenv('TOPMOD', 'design')

    def tcl_eval(expr):
        script = f'''
        source top.tcl
        return {expr}'''
        return tcl.eval(script)

    # When the TCL shell displays a multiline string, it gets surrounded in {}.
    expected_desc = '{' + desc + '}'
    assert tcl_eval('[dict get $sc_cfg package description]') == expected_desc

    assert tcl_eval('[lindex [lindex [dict get $sc_cfg constraint outline] 1] 0]') == '30.0'
    assert tcl_eval('[dict get $sc_cfg option quiet]') == 'true'
    assert tcl_eval('[dict get $sc_cfg input rtl verilog]') == 'rtl/design.v'


def test_csv():
    chip = siliconcompiler.Chip('test')
    chip.input('source.v')
    chip.add('asic', 'logiclib', 'mainlib')
    chip.add('asic', 'logiclib', 'synlib', step='syn')
    chip.add('asic', 'logiclib', 'syn1lib', step='syn', index=1)

    chip.write_manifest('test.csv')

    with open('test.csv', 'r', newline='') as f:
        csvreader = csv.reader(f)
        data = {}
        for row in csvreader:
            assert len(row) == 2

            keypath, val = row
            data[keypath] = val

    assert data['design'] == 'test'
    assert data['input,rtl,verilog'] == 'source.v'
    assert data['asic,logiclib'] == 'mainlib'
    assert data['asic,logiclib,syn,default'] == 'synlib'
    assert data['asic,logiclib,syn,1'] == 'syn1lib'


#########################
if __name__ == "__main__":
    test_write_manifest()
