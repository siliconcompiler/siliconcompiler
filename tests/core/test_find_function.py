# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_find_function():

    chip = siliconcompiler.Chip('test')

    # pdk
    f = chip.find_function('freepdk45', 'setup', 'pdks')
    assert f is not None

    # flow
    f = chip.find_function('asicflow', 'setup', 'flows')
    assert f is not None

    # tool
    chip.set('arg', 'step', 'yosys')
    chip.set('arg', 'index', '0')
    f = chip.find_function('yosys', 'setup', 'tools')
    assert f is not None

    # write results
    chip.write_manifest("module.json")
    assert (os.path.isfile('module.json'))

#########################
if __name__ == "__main__":
    test_find_function()
