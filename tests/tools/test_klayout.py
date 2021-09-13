# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import pytest
import os
import siliconcompiler
import importlib

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_klayout():
    '''Klayout setup unit test
    '''

    chip = siliconcompiler.Chip()
    chip.target("freepdk45")

    # set variables
    tool = 'klayout'
    step = 'export'
    chip.set('design', 'mytopmodule')

    # template / boiler plate code
    searchdir = "siliconcompiler.tools." + tool
    modulename = '.'+tool+'_setup'
    module = importlib.import_module(modulename, package=searchdir)
    setup_tool = getattr(module, "setup_tool")
    setup_tool(chip, step, '0')

    # test results
    localcfg = chip.getcfg('eda',tool)
    chip.writecfg(tool + '_setup.json', cfg=localcfg)
    assert os.path.isfile(tool+'_setup.json')

    return localcfg


#########################
if __name__ == "__main__":
    test_klayout()
