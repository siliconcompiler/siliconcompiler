# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import re
import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

def test_valid():

    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)
    #basic
    valid =  chip.valid('design')
    assert valid
    #nest
    valid = chip.valid('pdk', 'freepdk45', 'foundry')
    assert valid
    #dynamic valid
    valid = chip.valid('pdk', 'freepdk45', 'grid', '10M', 'metal1', 'name')
    assert valid
    #valid b/c of default (valid for set)
    valid = chip.valid('pdk', 'freepdk45', 'grid', 'M10', 'metal1', 'name', default_valid=True)
    assert valid
    #dynamic with default fields
    valid = chip.valid('pdk', 'freepdk45', 'grid', 'default', 'default', 'name')
    assert  valid
    #not working
    valid = chip.valid('blah')
    assert not valid


#########################
if __name__ == "__main__":
    test_valid()
