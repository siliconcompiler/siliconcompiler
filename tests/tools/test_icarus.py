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

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')
    chip.set('ydir', ydir)
    chip.set('design', design)
    chip.set('source', topfile)
    chip.set('mode', 'sim')
    chip.set('arg','step','compile')
    chip.set('flow', 'icarus')
    chip.run()

    # check that compilation succeeded
    assert chip.find_result('vvp', step='compile') is not None

#########################
if __name__ == "__main__":
    oh_dir = os.path.join('third_party', 'designs', 'oh')
    test_icarus(oh_dir)
