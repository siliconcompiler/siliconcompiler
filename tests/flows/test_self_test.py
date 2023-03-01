import os
import siliconcompiler
import subprocess

import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    chip = siliconcompiler.Chip('')
    chip.load_target('asic_demo')
    chip.run()
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test_cli():
    ''' Verify self-test functionality w/ command-line call '''
    subprocess.run(['sc', '-target', 'asic_demo'])
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
