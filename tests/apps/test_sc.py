import os
from siliconcompiler.apps import sc

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_design_inference(scroot, monkeypatch):
    '''Tests that sc CLI app can infer design name from filename.'''
    source = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    # only run import, makes this quicker

    monkeypatch.setattr('sys.argv', ['sc', source, '-steplist', 'import', '-strict'])
    assert sc.main() == 0

    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')
