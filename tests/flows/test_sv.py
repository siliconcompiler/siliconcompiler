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

    chip = siliconcompiler.Chip(design)

    chip.add('input', 'rtl', 'verilog', os.path.join(datadir, 'sv', 'prim_util_pkg.sv'))
    chip.add('input', 'rtl', 'verilog', os.path.join(datadir, 'sv', f'{design}.sv'))
    chip.add('option', 'idir', os.path.join(datadir, 'sv', 'inc/'))
    chip.add('option', 'define', 'SYNTHESIS')

    chip.set('option', 'frontend', 'systemverilog')
    chip.load_target('freepdk45_demo')

    chip.add('option', 'steplist', 'import')
    chip.add('option', 'steplist', 'convert')
    chip.add('option', 'steplist', 'syn')

    chip.run()

    assert chip.find_result('vg', step='syn') is not None
