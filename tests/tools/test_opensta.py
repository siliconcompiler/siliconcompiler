# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

from siliconcompiler import Chip
from siliconcompiler.tools.opensta import timing

from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_opensta(datadir):
    design = 'foo'
    netlist = os.path.join(datadir, 'lec', f'{design}.vg')
    sdc = os.path.join(datadir, 'lec', f'{design}.sdc')

    chip = Chip(design)
    chip.use(freepdk45_demo)

    flow = 'opensta_timing'
    chip.node(flow, 'opensta', timing)
    chip.set('option', 'flow', flow)

    chip.input(netlist)
    chip.input(sdc)

    # Check that OpenSTA ran successfully
    assert chip.run()

    # Check that the setup and hold slacks are the expected values.
    assert chip.get('metric', 'setupslack', step='opensta', index='0') == -0.220
    assert chip.get('metric', 'holdslack', step='opensta', index='0') == 0.050


@pytest.mark.eda
@pytest.mark.quick
def test_opensta_sdf(datadir):
    design = 'foo'
    netlist = os.path.join(datadir, 'lec', f'{design}.vg')
    sdc = os.path.join(datadir, 'lec', f'{design}.sdc')
    sdf = os.path.join(datadir, 'lec', f'{design}.typical.sdf')

    chip = Chip(design)
    chip.use(freepdk45_demo)

    flow = 'opensta_timing'
    chip.node(flow, 'opensta', timing)
    chip.set('option', 'flow', flow)

    chip.input(netlist)
    chip.input(sdc)
    chip.input(sdf)

    # Check that OpenSTA ran successfully
    assert chip.run()

    # Check that the setup and hold slacks are the expected values.
    assert chip.get('metric', 'setupslack', step='opensta', index='0') == -0.890
    assert chip.get('metric', 'holdslack', step='opensta', index='0') == 0.020
