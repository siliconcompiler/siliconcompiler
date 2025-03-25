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
def test_summarize_cfg_no_cfg(monkeypatch, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc summarizes a cfg.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv', [summarize.__name__])
    assert summarize.main() == 1


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg_cli_error(monkeypatch, run_cli, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    run_cli(['./test_replay.sh', '-error'], retcode=1)


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg_help(monkeypatch, run_cli, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    proc = run_cli(['./test_replay.sh', '-help'])

    assert proc.returncode == 0

    output = proc.stdout
    assert "-dir=DIR" in output
    assert "-venv=DIR" in output
    assert "-print_tools" in output
    assert "-extract_only" in output
    assert "-setup_only" in output
    assert "-help" in output


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg_print_tools(monkeypatch, run_cli, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    proc = run_cli(['./test_replay.sh', '-print_tools'])
    assert proc.returncode == 0

    output = proc.stdout
    assert "openroad:" in output
    assert "yosys   :" in output
    assert "klayout :" in output


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg_setup(monkeypatch, run_cli, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    proc = run_cli(['./test_replay.sh',
                    '-dir=replay_dir',
                    '-venv=env',
                    '-assert_python',
                    '-setup_only'])
    assert proc.returncode == 0

    assert os.path.isdir('replay_dir')
    assert os.path.isdir('replay_dir/env')

    assert os.path.isfile('replay_dir/requirements.txt')
    assert os.path.isfile('replay_dir/sc_manifest.json')
    assert os.path.isfile('replay_dir/replay.py')


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg_no_cfg(monkeypatch, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-file', 'test_replay.sh'])

    assert replay.main() == 1

    assert not os.path.isfile('test_replay.sh')


@pytest.mark.eda
@pytest.mark.quick
def test_replay_cfg_no_file(monkeypatch, gcd_chip_dir, copy_chip_dir):
    '''Tests that sc generates a replay script.'''

    chip = copy_chip_dir(gcd_chip_dir)
    chip.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json'])

    assert not os.path.isfile('replay.sh')

    assert replay.main() == 0

    assert os.path.isfile('replay.sh')
