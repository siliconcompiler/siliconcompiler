# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import pytest


##################################
def test_nop():
    '''API test for nop methods
    '''

    chip = siliconcompiler.Chip('gcd')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'flow', 'test')
    chip.node('test', 'import', 'surelog')
    chip.node('test', 'nop1', 'nop')
    chip.node('test', 'nop2', 'nop')
    chip.edge('test', 'import', 'nop1')
    chip.edge('test', 'nop1', 'nop2')
    chip.check_manifest()
    chip.write_flowgraph("nop.png")

#########################
if __name__ == "__main__":
    test_nop()
