# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_write_manifest():

    chip = siliconcompiler.Chip()
    chip.add('constraint', 'top.sdc')
    chip.set('projversion', '0.1')
    chip.set('description', 'A dummy project')
    chip.add('source', 'top.v')
    chip.add('source', 'a.v')
    chip.add('source', 'b.v')
    chip.add('source', 'c.v')
    chip.set('design', 'top')

    chip.write_manifest('top.core')
    chip.write_manifest('top.pkg.json')
    chip.write_manifest('top.csv')
    chip.write_manifest('top.tcl')
    chip.write_manifest('top.yaml')

#########################
if __name__ == "__main__":
    test_write_manifest()
