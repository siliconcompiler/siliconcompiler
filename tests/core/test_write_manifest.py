# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import csv

import pytest

import siliconcompiler

def test_write_manifest():

    chip = siliconcompiler.Chip('top')
    chip.add('input', 'asic', 'sdc','top.sdc')
    chip.add('input', 'rtl', 'verilog', 'top.v')
    chip.add('input', 'rtl', 'verilog', 'a.v')
    chip.add('input', 'rtl', 'verilog', 'b.v')
    chip.add('input', 'rtl', 'verilog', 'c.v')

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
    chip.add('asic', 'diearea', (0, 0))
    chip.add('asic', 'diearea', (30, 40))

    # Test bools
    chip.set('option', 'quiet', True)

    # Test envvars
    chip.set('input', 'rtl', 'verilog', 'rtl/$TOPMOD.v')

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

    assert tcl_eval('[lindex [lindex [dict get $sc_cfg asic diearea] 1] 0]') == '30.0'
    assert tcl_eval('[dict get $sc_cfg option quiet]') == 'true'
    assert tcl_eval('[dict get $sc_cfg input rtl verilog]') == 'rtl/design.v'

def test_csv():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'source.v')

    chip.write_manifest('test.csv')

    design_found = False
    input_found = False
    with open('test.csv', 'r', newline='') as f:
        csvreader = csv.reader(f)
        for row in csvreader:
            assert len(row) == 2

            keypath, val = row
            if keypath == 'design':
                assert val == 'test'
                design_found = True
            elif keypath == 'input,rtl,verilog':
                assert val == 'source.v'
                input_found = True
    assert design_found
    assert input_found

#########################
if __name__ == "__main__":
    test_write_manifest()
