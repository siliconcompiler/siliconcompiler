# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_write_manifest():

    chip = siliconcompiler.Chip('top')
    chip.add('source', 'sdc','top.sdc')
    chip.add('source', 'verilog', 'top.v')
    chip.add('source', 'verilog', 'a.v')
    chip.add('source', 'verilog', 'b.v')
    chip.add('source', 'verilog', 'c.v')

    chip.write_manifest('top.pkg.json')
    chip.write_manifest('top.csv')
    chip.write_manifest('top.tcl', prune=False)
    chip.write_manifest('top.yaml')

#########################
if __name__ == "__main__":
    test_write_manifest()
