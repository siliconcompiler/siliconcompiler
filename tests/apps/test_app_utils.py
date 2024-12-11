import os
from siliconcompiler.apps.utils import summarize, replay

import pytest


@pytest.mark.eda
def test_summarize_cfg(monkeypatch, gcd_chip):
    '''Tests that sc summarizes a cfg.'''

    gcd_chip.run()
    gcd_chip.write_manifest('test.json')

    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv', [summarize.__name__, '-cfg', 'test.json'])
    assert summarize.main() == 0


@pytest.mark.eda
def test_replay_cfg(monkeypatch, gcd_chip):
    '''Tests that sc generates a replay folder.'''

    gcd_chip.run()
    gcd_chip.write_manifest('test.json')

    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv', [replay.__name__, '-cfg', 'test.json', '-path', 'test_replay'])
    assert replay.main() == 0

    assert os.path.isdir('test_replay')
    assert os.path.isfile('test_replay/requirements.txt')
    assert os.path.isfile('test_replay/setup.sh')
    assert os.path.isfile('test_replay/run.py')
