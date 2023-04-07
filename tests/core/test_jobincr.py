import os

import siliconcompiler

def test_jobincr():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', 'builtin.nop')

    chip.set('option', 'jobincr', True)

    chip.run()
    assert chip._getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job0']

    chip.run()
    assert chip._getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job1']
