import siliconcompiler
import os
import pytest
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_sv(datadir):
    '''Test that we can successfully synthesize a SystemVerilog design using the
    asicflow.
    '''
    design = 'prim_fifo_sync'

    chip = siliconcompiler.Chip(design)

    chip.input(os.path.join(datadir, 'sv', 'prim_util_pkg.sv'))
    chip.input(os.path.join(datadir, 'sv', f'{design}.sv'))
    chip.add('option', 'idir', os.path.join(datadir, 'sv', 'inc/'))
    chip.add('option', 'define', 'SYNTHESIS')

    chip.use(freepdk45_demo)

    chip.add('option', 'to', 'syn')

    assert chip.run()

    assert chip.find_result('vg', step='syn') is not None
