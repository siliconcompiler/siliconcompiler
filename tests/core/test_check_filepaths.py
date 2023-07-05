# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

import os

import pytest


@pytest.mark.quick
def test_check_filepaths_pass():
    chip = siliconcompiler.Chip('gcd')
    chip.load_target("freepdk45_demo")
    chip.input('gcd.v')

    with open('gcd.v', 'w') as f:
        f.write('test')

    assert chip.check_filepaths()


@pytest.mark.quick
def test_check_filepaths_faildir():
    chip = siliconcompiler.Chip('gcd')
    chip.load_target("freepdk45_demo")
    chip.input('gcd.v')

    with open('gcd.v', 'w') as f:
        f.write('test')

    chip.add('option', 'dir', 'test_dir', 'does_not_exist')

    assert not chip.check_filepaths()


@pytest.mark.quick
def test_check_filepaths_failfile():
    chip = siliconcompiler.Chip('gcd')
    chip.load_target("freepdk45_demo")
    chip.input('examples/gcd/gcd1.v')

    # Create build dir
    os.makedirs('build')
    assert not chip.check_filepaths()
