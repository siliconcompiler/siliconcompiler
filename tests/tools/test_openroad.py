# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest
import sys

@pytest.mark.eda
@pytest.mark.quick
def test_openroad(scroot):
    datadir = os.path.join(scroot, 'tests', 'data')
    netlist = os.path.join(datadir, 'oh_fifo_sync_freepdk45.vg')

    design = "oh_fifo_sync"

    chip = siliconcompiler.Chip(design)

    chip.set('input', 'netlist', netlist)
    chip.set('option', 'quiet', True)
    chip.set('option', 'novercheck', True)
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])

    # load tech
    chip.load_target("freepdk45_demo")

    # set up tool for floorplan
    flow = 'floorplan'
    chip.node(flow, 'import', 'nop')
    chip.node(flow, 'floorplan', 'openroad')
    chip.edge(flow, 'import', 'floorplan')
    chip.set('option', 'flow', flow)

    chip.run()

    # check that compilation succeeded
    assert chip.find_result('def', step='floorplan') is not None

#########################
if __name__ == "__main__":
    from tests.fixtures import scroot
    test_openroad(scroot())
