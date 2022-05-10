# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
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

#########################
if __name__ == "__main__":
    test_write_manifest()
