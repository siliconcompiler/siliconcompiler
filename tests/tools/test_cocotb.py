import siliconcompiler

import os
import sys

import pytest

from siliconcompiler.tools.cocotb import simulation
from siliconcompiler.tools.surelog import parse


@pytest.mark.eda
@pytest.mark.quick
def test_cocotb(scroot):
    heartbeat_src = os.path.join(scroot, 'examples', 'heartbeat', 'heartbeat.v')
    cocotb_src = os.path.join(scroot, 'tests', 'tools', 'data', 'cocotb_heartbeat_test.py')
    design = "heartbeat"

    chip = siliconcompiler.Chip(design)

    chip.input(heartbeat_src)
    chip.set("input", "cocotb", "python", cocotb_src)

    chip.set('tool', 'cocotb', 'task', 'simulation', 'var', 'simulator', 'icarus')
    chip.set('tool', 'cocotb', 'task', 'simulation', 'var', 'timescale', ["1ns", "1ps"])

    flow = "cocotb_flow"
    chip.node(flow, "import", parse)  # use surelog for import
    chip.node(flow, "cocotb", simulation)  # cocotb for sim
    chip.edge(flow, "import", "cocotb")  # perform syn after import
    chip.set("option", "flow", flow)

    assert chip.run()

    #output = chip.find_result('v', step=step)
    #assert output is not None

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_cocotb(scroot())
