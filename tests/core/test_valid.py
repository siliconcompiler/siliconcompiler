# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import re

def test_valid():

    chip = siliconcompiler.Chip('test')
    chip.load_target("freepdk45_demo")
    #basic
    valid =  chip.valid('design')
    assert valid
    #nest
    valid = chip.valid('asic','minlayer')
    assert valid
    #dynamic valid
    valid = chip.valid('pdk', 'freepdk45', 'aprtech', 'openroad', '10M', '10t', 'lef')
    assert valid
    #valid b/c of default (valid for set), changed metal stack to something not yet loaded
    valid = chip.valid('pdk', 'freepdk45', 'aprtech', 'openroad', 'M10', '10t', 'lef', default_valid=True)
    assert valid
    #dynamic with default fields
    valid = chip.valid('constraint', 'timing', 'default', 'voltage')
    assert  valid
    #not working
    valid = chip.valid('blah')
    assert not valid


#########################
if __name__ == "__main__":
    test_valid()
