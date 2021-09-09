# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

##################################
def test_api_show():
    '''API test for show method
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()
    chip.target("freepdk45_asicflow")
    chip.set("quiet", True)
    chip.show("examples/gcd/gcd_golden.def.gz")
    chip.show("examples/gcd/gcd_golden.pkg.json.gz")
    chip.show("examples/gcd/gcd.NOT_SUPPORTED")

#########################
if __name__ == "__main__":
    test_api_show()
