# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import siliconcompiler

@pytest.fixture
def chip():
    return siliconcompiler.Chip('top')

def test_basic_setget(chip):
    design = chip.get('design')
    assert design == "top"

def test_list_access(chip):
    #Check list access
    inlist = ['import','syn']
    chip.set('option', 'steplist', inlist)
    assert inlist == chip.get('option', 'steplist')

def test_scalar_to_list_access(chip):
    inscalar = 'import'
    chip.set('option', 'steplist', 'import')
    outlist = chip.get('option', 'steplist')
    assert outlist == [inscalar]

def test_illegal_key(chip):
    #check illegal key (expected error)
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('badquery', 'top')

def test_error_scalar_add(chip):
    #check error on scalar add
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.add('design', 'top')

def test_error_assign_list(chip):
    #check assigning list to scalar
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('design', ['top'])
