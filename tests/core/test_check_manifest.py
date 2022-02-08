# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

import os

import pytest

def test_check_manifest():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_project("freepdk45_demo")
    chip.set('source', 'examples/gcd/gcd.v')
    flow = chip.get('target', 'flow')
    index = "0"
    steps = ['import', 'syn']
    for step in steps:
        tool = chip.get('flowgraph', flow, step, index, 'tool')
        chip.set('arg', 'step', step)
        chip.set('arg', 'index', index)
        chip.set('design', 'gcd')

        setup = chip.find_function(tool, 'setup', 'tools')
        assert setup is not None
        setup(chip)

    chip.set('steplist', steps)

    chip.set('arg', 'step', None)
    chip.set('arg', 'index', None)
    assert chip.check_manifest() == 0

@pytest.mark.eda
@pytest.mark.quick
def test_check_allowed_filepaths_pass(scroot, monkeypatch):
    chip = siliconcompiler.Chip()
    chip.set('design', 'gcd')

    chip.set('source', os.path.join(scroot, 'examples', 'gcd', 'gcd.v'))
    chip.load_project("freepdk45_demo")

    # run an import just to collect files
    chip.set('steplist', 'import')
    chip.run()

    env = {
        'SC_VALID_PATHS': os.path.join(scroot, 'third_party', 'pdks'),
        'SCPATH': os.environ['SCPATH']
    }
    monkeypatch.setattr(os, 'environ', env)

    assert chip.check_manifest() == 0

@pytest.mark.eda
@pytest.mark.quick
def test_check_allowed_filepaths_fail(scroot, monkeypatch):
    chip = siliconcompiler.Chip()
    chip.set('design', 'gcd')

    chip.set('source', os.path.join(scroot, 'examples', 'gcd', 'gcd.v'))
    chip.set('read', 'sdc', 'import', '0', '/random/abs/path/to/file.sdc')
    chip.set('read', 'sdc', 'import', '0', False, field='copy')
    chip.load_project("freepdk45_demo")

    # run an import just to collect files
    chip.set('steplist', 'import')
    chip.run()

    env = {
        'SC_VALID_PATHS': os.path.join(scroot, 'third_party', 'pdks'),
        'SCPATH': os.environ['SCPATH']
    }
    monkeypatch.setattr(os, 'environ', env)

    assert chip.check_manifest() == 1

def test_check_missing_file_param():
    chip = siliconcompiler.Chip()
    chip.set('design', 'gcd')
    chip.load_project("freepdk45_demo")

    chip.set('arg', 'step', 'syn')
    chip.set('arg', 'index', '0')
    setup_tool = chip.find_function('yosys', 'setup', 'tools')
    setup_tool(chip)

    chip.set('eda', 'yosys', 'input', 'syn', '0', [])
    chip.set('eda', 'yosys', 'output', 'syn', '0',[])

    # not real file, will cause error
    libname = 'NangateOpenCellLibrary'
    corner = 'typical'
    chip.add('library', libname, 'nldm', corner, 'lib', '/fake/timing/file.lib')

    assert chip.check_manifest() == 1

#########################
if __name__ == "__main__":
    test_check_manifest()
