import os
import subprocess

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_design_inference(scroot):
    '''Tests that sc CLI app can infer design name from filename.'''
    source = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    # only run import, makes this quicker
    subprocess.run(['sc', source, '-steplist', 'import', '-strict'])

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
