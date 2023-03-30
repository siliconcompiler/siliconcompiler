import os

import pytest

import siliconcompiler

import importlib

def create_fake_surelog():
    with open('surelog', 'w') as f:
        # hardcoded to check that fake license server env is provided, then
        # dump a version
        f.write('#!/bin/sh\n')
        f.write('set -o nounset\n') # quit early if script tries to expand unset var
        f.write(': $ACME_LICENSE\n') # try to expand license server var
        f.write('echo VERSION: 0.0\n')
    # executable
    os.chmod('surelog', 0o755)

@pytest.mark.eda
@pytest.mark.quick
def test_multiple_tools():
    '''Tests that we can tweak tool version, path, and licenseserver settings
    across different nodes.'''
    create_fake_surelog()

    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', 'builtin.import')
    chip.node(flow, 'slog', importlib.import_module('siliconcompiler.tools.surelog.import'), index=0)
    chip.node(flow, 'slog', importlib.import_module('siliconcompiler.tools.surelog.import'), index=1)
    chip.edge(flow, 'import', 'slog', head_index=0)
    chip.edge(flow, 'import', 'slog', head_index=1)

    # Overwrite default path to make sure this would break if step/index weren't
    # implemented
    chip.set('tool', 'surelog', 'path', os.getcwd())

    # Restore path for slog0 specifically
    chip.set('tool', 'surelog', 'path', '', step='slog', index=0)
    # Overwrite version for slog1
    chip.set('tool', 'surelog', 'version', '==0.0', step='slog', index=1)

    # Set fake license server for slog1
    chip.set('tool', 'surelog', 'licenseserver', 'ACME_LICENSE', '1700@server', step='slog', index=1)

    # Don't run tools, just vesion check
    chip.set('option', 'skipall', True)
    chip.run()

    assert chip.get('flowgraph', flow, 'slog', '0', 'status') == siliconcompiler.core.TaskStatus.SUCCESS
    assert chip.get('flowgraph', flow, 'slog', '1', 'status') == siliconcompiler.core.TaskStatus.SUCCESS
