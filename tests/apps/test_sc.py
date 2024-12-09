import os
from siliconcompiler.apps import sc
from siliconcompiler import Chip, Schema

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_design_inference(scroot, monkeypatch):
    '''Tests that sc CLI app can infer design name from filename.'''
    source = os.path.join(scroot, 'tests', 'data', 'heartbeat.v')
    # only run import, makes this quicker

    monkeypatch.setattr('sys.argv', ['sc', source, '-to', 'import.verilog', '-strict'])
    assert sc.main() == 0

    cfg_file = 'build/heartbeat/job0/heartbeat.pkg.json'
    assert os.path.isfile(cfg_file)
    assert Schema(manifest=cfg_file).get('design') == 'heartbeat'


def test_design_name_inference_nofile():
    '''Tests that sc CLI app can infer design name from filename.'''

    chip = Chip('')

    assert sc._infer_designname(chip) is None


@pytest.mark.parametrize("filepath,name", [
    ('heartbeat.v', 'heartbeat'),
    ('heartbeat.vg', 'heartbeat'),
    ('heartbeat.gds', 'heartbeat'),
    ('heartbeat.gds.gz', 'heartbeat')
])
def test_design_name_inference(filepath, name):
    '''Tests that sc CLI app can infer design name from filename.'''

    chip = Chip('')
    chip.input(filepath)

    assert sc._infer_designname(chip) == name
