# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_check_manifest():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("asicflow_freepdk45")
    chip.set('source', 'examples/gcd/gcd.v')

    step = "syn"
    index = "0"
    tool = chip.get('flowgraph', step, index, 'tool')
    chip.set('arg', 'step', step)
    chip.set('arg', 'index', index)
    chip.set('design', 'test')

    setup_tool = chip.find_function('yosys', 'tool', 'setup_tool')
    assert setup_tool is not None

    setup_tool(chip)
    assert chip.check_manifest() == 0

#########################
if __name__ == "__main__":
    test_check_manifest()
