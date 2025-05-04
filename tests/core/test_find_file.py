# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import pytest

import siliconcompiler
from siliconcompiler.core import SiliconCompilerError
from siliconcompiler.targets import freepdk45_demo


def test_invalid_script():
    '''Regression test: find_files(missing_ok=False) should error out if script
    not found.'''
    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)

    chip.set('tool', 'yosys', 'task', 'syn_asic', 'script', 'fakescript.tcl')

    with pytest.raises(SiliconCompilerError):
        chip.find_files('tool', 'yosys', 'task', 'syn_asic', 'script',
                        missing_ok=False, step='syn', index='0')
