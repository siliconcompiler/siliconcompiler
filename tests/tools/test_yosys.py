# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import pytest
import os
import siliconcompiler
from siliconcompiler.tools.yosys.yosys_setup import setup_tool

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_yosys():
    '''Yosys setup unit test
    '''

    chip = siliconcompiler.Chip()

    # set variables
    chip.set('design', 'mytopmodule')
    # run setup
    setup_tool(chip, step='syn', index='0')
    # write out dictionary
    localcfg = chip.copy('eda','yosys')
    chip.writecfg('yosys_setup.json', cfg=localcfg)
    # check that file was written
    assert os.path.isfile('yosys_setup.json')
    return localcfg

#########################
if __name__ == "__main__":
    test_yosys()
