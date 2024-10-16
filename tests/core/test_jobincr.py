import os
import pytest

import siliconcompiler

from siliconcompiler.tools.builtin import nop
from siliconcompiler.scheduler import _increment_job_name


def test_jobincr():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.set('option', 'flow', flow)
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
    chip.node(flow, 'import', nop)

    chip.set('option', 'clean', False)
    chip.set('option', 'jobincr', True)

    chip.run()
    assert chip.getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job0']

    chip.run()
    assert chip.getworkdir().split(os.sep)[-3:] == ['build', 'test', 'job0']


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_jobincr_clean_with_from(gcd_chip):

    gcd_chip.set('option', 'jobname', 'job0')
    gcd_chip.set('option', 'to', 'floorplan.init')

    def log_file(step):
        return f"{gcd_chip.getworkdir(step=step, index='0')}/{step}.log"

    gcd_chip.run()
    assert gcd_chip.getworkdir().split(os.sep)[-3:] == ['build', 'gcd', 'job0']
    old_import_time = os.path.getmtime(log_file('import_verilog'))
    old_syn_time = os.path.getmtime(log_file('syn'))
    old_fp_time = os.path.getmtime(log_file('floorplan.init'))

    gcd_chip.set('option', 'clean', True)
    gcd_chip.set('option', 'jobincr', True)
    gcd_chip.set('option', 'from', 'floorplan.init')

    gcd_chip.run()
    assert gcd_chip.getworkdir().split(os.sep)[-3:] == ['build', 'gcd', 'job1']
    new_import_time = os.path.getmtime(log_file('import_verilog'))
    new_syn_time = os.path.getmtime(log_file('syn'))
    new_fp_time = os.path.getmtime(log_file('floorplan.init'))

    # import and syn should be copies, floorplan should be new
    assert old_import_time == new_import_time
    assert old_syn_time == new_syn_time
    assert old_fp_time != new_fp_time
