import siliconcompiler
import os

def test_sv():
    '''Test that we can successfully synthesize a SystemVerilog design using the
    asicflow.
    '''
    design = 'prim_fifo_sync'

    localdir = os.path.dirname(os.path.abspath(__file__))
    files = f'{localdir}/../../data/sv'

    chip = siliconcompiler.Chip(design=design)

    chip.add('source', f'{files}/prim_util_pkg.sv')
    chip.add('source', f'{files}/{design}.sv')
    chip.add('idir', f'{files}/inc')
    chip.add('define', 'SYNTHESIS')

    chip.set('flowarg', 'sv', 'true')
    chip.target('asicflow_freepdk45')

    chip.add('steplist', 'import')
    chip.add('steplist', 'convert')
    chip.add('steplist', 'syn')

    chip.run()

    assert chip.find_result('vg', step='syn') is not None
