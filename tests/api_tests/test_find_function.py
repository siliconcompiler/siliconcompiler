# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_find_function():

    chip = siliconcompiler.Chip()

    # pdk
    f = chip.find_function('freepdk45', 'pdk', 'setup_pdk')
    assert f is not None

    # flow
    f = chip.find_function('asicflow', 'flow', 'setup_flow')
    assert f is not None

    # tool
    chip.set('arg', 'step', 'yosys')
    chip.set('arg', 'index', '0')
    f = chip.find_function('yosys', 'tool', 'setup_tool')
    assert f is not None

    # write results
    chip.write_manifest("module.json")
    assert (os.path.isfile('module.json'))

#########################
if __name__ == "__main__":
    test_find_function()
