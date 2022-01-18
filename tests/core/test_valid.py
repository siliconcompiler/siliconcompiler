# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import re

def test_valid():

    chip = siliconcompiler.Chip()
    chip.target("freepdk45")
    #basic
    valid =  chip.valid('design')
    assert valid
    #nest
    valid = chip.valid('asic','minlayer')
    assert valid
    #dynamic valid
    valid = chip.valid('pdk','grid', '10M', 'metal1', 'name')
    assert valid
    #valid b/c of default (valid for set)
    valid = chip.valid('pdk','grid', 'M10', 'metal1', 'name', default_valid=True)
    assert valid
    #dynamic with default fields
    valid = chip.valid('pdk','grid', 'default', 'default', 'name')
    assert  valid
    #not working
    valid = chip.valid('blah')
    assert not valid


#########################
if __name__ == "__main__":
    test_valid()
