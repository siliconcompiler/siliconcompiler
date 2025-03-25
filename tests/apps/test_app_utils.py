import os
from siliconcompiler.apps.utils import summarize, replay

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_summarize_cfg(monkeypatch, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc summarizes a cfg.'''

    chip = copy_chip_dir(gcd_chip_dir)

    chip.write_manifest('test.json')

    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv', [summarize.__name__, '-cfg', 'test.json'])
    assert summarize.main() == 0


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg(monkeypatch, run_cli, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)

    chip.write_manifest('test.json')

    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    run_cli(['./test_replay.sh', '-error'], retcode=1)

    run_cli(['./test_replay.sh', '-help'])
    run_cli(['./test_replay.sh', '-print_tools'])
    run_cli(['./test_replay.sh', '-dir=replay_dir', '-venv=env', '-assert_python', '-setup_only'])

    assert os.path.isdir('replay_dir')
    assert os.path.isdir('replay_dir/env')

    assert os.path.isfile('replay_dir/requirements.txt')
    assert os.path.isfile('replay_dir/sc_manifest.json')
    assert os.path.isfile('replay_dir/replay.py')
