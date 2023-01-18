# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_icarus(oh_dir):
    ydir = os.path.join(oh_dir, 'stdlib', 'hdl')

    design = "oh_fifo_sync"
    topfile = os.path.join(ydir, f'{design}.v')

    chip = siliconcompiler.Chip(design)
    chip.load_target('freepdk45_demo')
    chip.set('option', 'ydir', ydir)
    chip.set('input', 'rtl', 'verilog', topfile)
    chip.set('option', 'mode', 'sim')

    flow = 'sim'
    chip.node(flow, 'import', 'nop', 'nop')
    chip.node(flow, 'compile', 'icarus', 'compile')
    chip.edge(flow, 'import', 'compile')
    chip.set('option', 'flow', flow)

    chip.run()

    # check that compilation succeeded
    assert chip.find_result('vvp', step='compile') is not None

#########################
if __name__ == "__main__":
    oh_dir = os.path.join('third_party', 'designs', 'oh')
    test_icarus(oh_dir)
