# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_verilator(oh_dir):
    ydir = os.path.join(oh_dir, 'stdlib', 'hdl')

    design = "oh_fifo_sync"
    topfile = os.path.join(ydir, f'{design}.v')
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')
    chip.set('ydir', ydir)
    chip.set('design', design)
    chip.set('source', topfile)
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('mode', 'sim')
    chip.set('arg','step',step)
    chip.set('flow','test')
    chip.load_tool('verilator', standalone=True)
    chip.run()

    # check that compilation succeeded
    assert chip.find_result('v', step=step) is not None

#########################
if __name__ == "__main__":
    oh_dir = os.path.join('third_party', 'designs', 'oh')
    test_verilator(oh_dir)
