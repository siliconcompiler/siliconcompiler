# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

##################################
def test_show_file():
    '''API test for show method
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()
    chip.target('asicflow_freepdk45')
    chip.set("quiet", True)

    # TODO: showing these files is not supported, plus it's hard to test showing
    # regular DEF files. How should we test this function?
    chip.show_file("examples/gcd/gcd_golden.def.gz")
    chip.show_file("examples/gcd/gcd_golden.pkg.json.gz")
    chip.show_file("examples/gcd/gcd.NOT_SUPPORTED")

#########################
if __name__ == "__main__":
    test_show_file()
