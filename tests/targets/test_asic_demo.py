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
    assert chip.get('metric', 'holdslack', step='export', index='1') >= 0.0
    assert chip.get('metric', 'holdslack', step='export', index='1') < 10.0
    assert chip.get('metric', 'setupslack', step='export', index='1') >= 0.0
    assert chip.get('metric', 'setupslack', step='export', index='1') < 10.0

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test_cli():
    ''' Verify self-test functionality w/ command-line call '''
    subprocess.run(['sc', '-target', 'asic_demo'])
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')

    # Check timing
    chip = siliconcompiler.Chip('')
    chip.read_manifest('build/heartbeat/job0/heartbeat.pkg.json')
    assert chip.get('metric', 'holdslack', step='export', index='1') >= 0.0
    assert chip.get('metric', 'holdslack', step='export', index='1') < 10.0
    assert chip.get('metric', 'setupslack', step='export', index='1') >= 0.0
    assert chip.get('metric', 'setupslack', step='export', index='1') < 10.0

@pytest.mark.eda
@pytest.mark.timeout(900)
@pytest.mark.skip(reason="Report popup needs to be suppressed for test")
def test_self_test_cli_remote():
    ''' Verify self-test functionality w/ command-line call with remote '''
    subprocess.run(['sc', '-target', 'asic_demo', '-remote'])
    assert os.path.isfile('build/heartbeat/job0/export/0/outputs/heartbeat.gds')
