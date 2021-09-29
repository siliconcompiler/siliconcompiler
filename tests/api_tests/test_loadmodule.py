# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_loadmodule():

    chip = siliconcompiler.Chip()

    # pdk
    chip.loadmodule("freepdk45", "pdk")

    # flow
    chip.loadmodule("asicflow", "flow")

    # tool
    chip.set('arg', 'step', 'yosys')
    chip.set('arg', 'index', '0')
    chip.loadmodule("yosys", "tool")

    # write results
    chip.writecfg("module.json")
    assert (os.path.isfile('module.json'))

#########################
if __name__ == "__main__":
    test_loadmodule()
