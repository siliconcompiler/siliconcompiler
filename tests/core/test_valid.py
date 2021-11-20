# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import re

def test_valid():

    chip = siliconcompiler.Chip()
    valid =  chip.valid('design')
    assert valid
    valid = chip.valid('blah')
    assert not valid


#########################
if __name__ == "__main__":
    test_valid()
