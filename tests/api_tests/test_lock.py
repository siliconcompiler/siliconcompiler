# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

##################################
def test_lock():
    '''API test for show method
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()
    chip.target('asicflow_freepdk45')
    chip.set('design', "gcd")
    chip.set('design', "true", field="lock")
    chip.set('design', "FAIL")

    assert (chip.get('design') == "gcd")

#########################
if __name__ == "__main__":
    test_lock()
