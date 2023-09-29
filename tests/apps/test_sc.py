import os
import shutil
import pathlib
from siliconcompiler.apps import sc
from siliconcompiler.schema import Schema

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_design_inference(scroot, monkeypatch):
    '''Tests that sc CLI app can infer design name from filename.'''
    source = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    # only run import, makes this quicker

    monkeypatch.setattr('sys.argv', ['sc', source, '-steplist', 'import', '-strict'])
    assert sc.main() == 0

    cfg_file = 'build/heartbeat/job0/heartbeat.pkg.json'
    assert os.path.isfile(cfg_file)
    assert Schema(manifest=cfg_file).get('design') == 'heartbeat'


@pytest.mark.eda
@pytest.mark.quick
def test_design_inference_windows(scroot, monkeypatch):
    '''Tests that sc CLI app can infer design name from filename.'''
    source = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    # only run import, makes this quicker

    os.makedirs('testdir', exist_ok=True)
    shutil.copy(source, 'testdir')
    source_win = str(pathlib.PureWindowsPath('testdir', os.path.basename(source)))

    monkeypatch.setattr('sys.argv', ['sc', source_win, '-steplist', 'import', '-strict'])
    assert sc.main() == 0

    cfg_file = 'build/heartbeat/job0/heartbeat.pkg.json'
    assert os.path.isfile(cfg_file)
    assert Schema(manifest=cfg_file).get('design') == 'heartbeat'
