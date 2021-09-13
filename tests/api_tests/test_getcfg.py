# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_getcfg():

    chip = siliconcompiler.Chip()
    chip.target('freepdk45')
    localcfg = chip.getcfg('pdk')

#########################
if __name__ == "__main__":
    test_getcfg()
