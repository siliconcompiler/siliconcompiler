# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_verilator(scroot):
    ydir = os.path.join(scroot, 'third_party', 'designs', 'oh', 'stdlib', 'hdl')

    design = "oh_fifo_sync"
    topfile = os.path.join(ydir, f'{design}.v')
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.set('ydir', ydir)
    chip.set('design', design)
    chip.set('source', topfile)
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('mode', 'sim')
    chip.set('arg','step',step)
    chip.target("verilator")
    chip.run()

    # check that compilation succeeded
    assert chip.find_result('v', step=step) is not None

#########################
if __name__ == "__main__":
    from tests.fixtures import scroot
    test_verilator(scroot())
