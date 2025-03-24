# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
from siliconcompiler.targets import freepdk45_demo


def test_valid():

    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)
    # basic
    valid = chip.valid('design')
    assert valid
    # nest
    valid = chip.valid('pdk', 'freepdk45', 'foundry')
    assert valid
    # dynamic valid
    valid = chip.valid('pdk', 'freepdk45', 'aprtech', 'openroad', '10M', '10t', 'lef')
    assert valid
    # valid b/c of default (valid for set), changed metal stack to something not yet loaded
    valid = chip.valid('pdk', 'freepdk45', 'aprtech', 'openroad', 'M10', '10t', 'lef',
                       default_valid=True)
    assert valid
    # dynamic with default fields
    valid = chip.valid('constraint', 'timing', 'default', 'voltage', 'default')
    assert valid
    # not working
    valid = chip.valid('blah')
    assert not valid


def test_valid_check_complete():

    chip = siliconcompiler.Chip('test')
    valid = chip.valid('constraint', check_complete=False)
    assert valid


def test_valid_check_partial():

    chip = siliconcompiler.Chip('test')
    valid = chip.valid('constraint', check_complete=True)
    assert not valid
