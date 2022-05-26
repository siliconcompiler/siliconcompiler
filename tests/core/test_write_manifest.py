# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import siliconcompiler

def test_write_manifest():

    chip = siliconcompiler.Chip('top')
    chip.add('input', 'sdc','top.sdc')
    chip.add('input', 'verilog', 'top.v')
    chip.add('input', 'verilog', 'a.v')
    chip.add('input', 'verilog', 'b.v')
    chip.add('input', 'verilog', 'c.v')

    chip.write_manifest('top.pkg.json')
    chip.write_manifest('top.csv')
    chip.write_manifest('top.tcl', prune=False)
    chip.write_manifest('top.yaml')

def test_advanced_tcl(monkeypatch):
    # Tkinter module is part of Python standard library, but may not be
    # available depending on if the system has the python3-tk installed. This
    # line will import tkinter if it's available, and skip the test otherwise.
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
    chip.set('input', 'verilog', 'rtl/$TOPMOD.v')

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

    # When we call puts on a multiline string, it does get mangled a bit. It
    # stays surrounded by {}, and {} within the string are still escaped.
    # TODO: is this problematic? I think it is okay for now since we don't
    # really read these strings within TCL, they just need to not break sourcing
    # the manifest.
    expected_desc = '{' + desc.replace('{', '\\{').replace('}', '\\}') + '}'
    assert tcl_eval('[dict get $sc_cfg package description]') == expected_desc

    assert tcl_eval('[lindex [lindex [dict get $sc_cfg asic diearea] 1] 0]') == '30.0'
    assert tcl_eval('[dict get $sc_cfg option quiet]') == 'true'
    assert tcl_eval('[dict get $sc_cfg input verilog]') == 'rtl/design.v'

#########################
if __name__ == "__main__":
    test_write_manifest()
