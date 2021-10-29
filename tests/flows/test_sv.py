import siliconcompiler
import os
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_sv(datadir):
    '''Test that we can successfully synthesize a SystemVerilog design using the
    asicflow.
    '''
    design = 'prim_fifo_sync'

    chip = siliconcompiler.Chip(design=design)

    chip.add('source', os.path.join(datadir, 'sv', 'prim_util_pkg.sv'))
    chip.add('source', os.path.join(datadir, 'sv', f'{design}.sv'))
    chip.add('idir', os.path.join(datadir, 'sv', 'inc/'))
    chip.add('define', 'SYNTHESIS')

    chip.set('flowarg', 'sv', 'true')
    chip.target('asicflow_freepdk45')

    chip.add('steplist', 'import')
    chip.add('steplist', 'convert')
    chip.add('steplist', 'syn')

    chip.run()

    assert chip.find_result('vg', step='syn') is not None
