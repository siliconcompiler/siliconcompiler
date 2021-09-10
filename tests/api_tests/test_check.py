# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import importlib

def test_check():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("freepdk45_asicflow")
    chip.set('source', 'examples/gcd/gcd.v')

    step = "syn"
    index = "0"
    tool = chip.get('flowgraph', step, index, 'tool')
    searchdir = "siliconcompiler.tools." + tool
    modulename = '.'+tool+'_setup'
    module = importlib.import_module(modulename, package=searchdir)
    setup_tool = getattr(module, "setup_tool")
    setup_tool(chip, step, index)

    assert (chip.check(step,index) == 0)

#########################
if __name__ == "__main__":
    test_check()
