import os

import siliconcompiler

from siliconcompiler.tools.builtin import nop
from siliconcompiler.scheduler import _increment_job_name


def test_jobincr():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.set('option', 'mode', 'asic')
    chip.node(flow, 'import', nop)

    chip.set('option', 'clean', True)
    chip.set('option', 'jobincr', True)

    assert chip.get('option', 'jobname') == 'job0'

    chip.run()
    assert chip.getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job0']

    chip.run()
    assert chip.get('option', 'jobname') == 'job1'
    assert chip.getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job1']


def test_jobincr_nondefault():
    chip = siliconcompiler.Chip('test')

    chip.set('option', 'jobname', 'test0')

    chip.set('option', 'clean', True)
    chip.set('option', 'jobincr', True)

    assert chip.get('option', 'jobname') == 'test0'

    os.makedirs(chip.getworkdir(), exist_ok=True)

    _increment_job_name(chip)

    assert chip.get('option', 'jobname') == 'test1'


def test_jobincr_nonnumbered():
    chip = siliconcompiler.Chip('test')

    chip.set('option', 'jobname', 'test')

    chip.set('option', 'clean', True)
    chip.set('option', 'jobincr', True)

    assert chip.get('option', 'jobname') == 'test'

    os.makedirs(chip.getworkdir(), exist_ok=True)

    _increment_job_name(chip)

    assert chip.get('option', 'jobname') == 'test1'


def test_jobincr_not_clean():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.set('option', 'mode', 'asic')
    chip.node(flow, 'import', nop)

    chip.set('option', 'clean', False)
    chip.set('option', 'jobincr', True)

    chip.run()
    assert chip.getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job0']

    chip.run()
    assert chip.getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job0']
