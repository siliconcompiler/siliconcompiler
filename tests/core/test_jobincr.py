import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_jobincr_clean_with_from(gcd_chip):

    gcd_chip.set('option', 'jobname', 'job0')
    gcd_chip.set('option', 'to', 'floorplan.init')

    def log_file(step):
        return f"{gcd_chip.getworkdir(step=step, index='0')}/{step}.log"

    gcd_chip.run(raise_exception=True)
    assert gcd_chip.getworkdir().split(os.sep)[-3:] == ['build', 'gcd', 'job0']
    old_import_time = os.path.getmtime(log_file('import.verilog'))
    old_syn_time = os.path.getmtime(log_file('syn'))
    old_fp_time = os.path.getmtime(log_file('floorplan.init'))

    gcd_chip.set('option', 'clean', True)
    gcd_chip.set('option', 'jobincr', True)
    gcd_chip.set('option', 'from', 'floorplan.init')

    gcd_chip.run(raise_exception=True)
    assert gcd_chip.getworkdir().split(os.sep)[-3:] == ['build', 'gcd', 'job1']
    new_import_time = os.path.getmtime(log_file('import.verilog'))
    new_syn_time = os.path.getmtime(log_file('syn'))
    new_fp_time = os.path.getmtime(log_file('floorplan.init'))

    # import and syn should be copies, floorplan should be new
    assert old_import_time == new_import_time
    assert old_syn_time == new_syn_time
    assert old_fp_time != new_fp_time
