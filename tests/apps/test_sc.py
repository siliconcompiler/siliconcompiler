import os
from siliconcompiler.apps import sc
from siliconcompiler.schema import Schema

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_design_inference(scroot, monkeypatch):
    '''Tests that sc CLI app can infer design name from filename.'''
    source = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    # only run import, makes this quicker

    monkeypatch.setattr('sys.argv', ['sc', source, '-to', 'import_verilog', '-strict'])
    assert sc.main() == 0

    cfg_file = 'build/heartbeat/job0/heartbeat.pkg.json'
    assert os.path.isfile(cfg_file)
    assert Schema(manifest=cfg_file).get('design') == 'heartbeat'
