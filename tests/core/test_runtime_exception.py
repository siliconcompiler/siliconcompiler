# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import csv

import pytest

import siliconcompiler

def test_version():
    chip = siliconcompiler.Chip('test')

    org_find_func = siliconcompiler.Chip.find_function
    # Replace find_function so we can throw an error
    def find_function(modulename, funcname, moduletype=None, moduletask=None):
        if funcname == 'parse_version':
            def parse_version(text):
                raise IndexError('This is an index error')
            return parse_version
        else:
            return org_find_func(chip, modulename, funcname, moduletype=moduletype, moduletask=moduletask)
    chip.find_function = find_function

    chip.load_target('asic_demo')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run()
