# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

import os

import pytest

def test_check_manifest():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("asicflow_freepdk45")
    chip.set('source', 'examples/gcd/gcd.v')

    index = "0"
    for step in ('import', 'syn'):
        tool = chip.get('flowgraph', step, index, 'tool')
        chip.set('arg', 'step', step)
        chip.set('arg', 'index', index)
        chip.set('design', 'gcd')

        setup_tool = chip.find_function(tool, 'tool', 'setup_tool')
        assert setup_tool is not None
        setup_tool(chip)

    chip.set('arg', 'step', None)
    chip.set('arg', 'index', None)
    assert chip.check_manifest() == 0

@pytest.mark.eda
@pytest.mark.quick
def test_check_allowed_filepaths_pass(scroot, monkeypatch):
    chip = siliconcompiler.Chip()
    chip.set('design', 'gcd')

    chip.set('source', os.path.join(scroot, 'examples', 'gcd', 'gcd.v'))
    chip.target('asicflow_freepdk45')

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
    chip.target('asicflow_freepdk45')

    # run an import just to collect files
    chip.set('steplist', 'import')
    chip.run()

    env = {
        'SC_VALID_PATHS': os.path.join(scroot, 'third_party', 'pdks'),
        'SCPATH': os.environ['SCPATH']
    }
    monkeypatch.setattr(os, 'environ', env)

    assert chip.check_manifest() == 1

#########################
if __name__ == "__main__":
    test_check_manifest()
