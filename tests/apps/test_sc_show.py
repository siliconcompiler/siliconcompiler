import os

import pytest

from siliconcompiler.apps import sc_show
from siliconcompiler.flowgraph import _get_flowgraph_exit_nodes


@pytest.mark.parametrize('flags', [
    [],
    ['-design', 'heartbeat'],
    ['-design', 'heartbeat',
     '-arg_step', 'floorplan.init'],
    ['-design', 'heartbeat',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0'],
    ['-design', 'heartbeat',
     '-screenshot'],
])
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(180)
def test_sc_show_design_only(flags, monkeypatch, heartbeat_dir):
    '''Test sc-show app on a few sets of flags.'''

    os.chdir(heartbeat_dir)

    # Mock chip.run() to avoid GUI complications
    # We have separate tests in test/core/test_show.py that handle these
    # complications and test this function itself, so there's no need to
    # run it here.
    def fake_run(chip, raise_exception=False):
        # fake a png output in case this is a screenshot
        step, index = _get_flowgraph_exit_nodes(chip, flow='showflow')[0]
        os.makedirs(f'{chip.getworkdir(step=step, index=index)}/outputs', exist_ok=True)
        with open(f'{chip.getworkdir(step=step, index=index)}/outputs/{chip.top()}.png', 'w') as f:
            f.write('\n')
        return True

    monkeypatch.setattr('siliconcompiler.Chip.run', fake_run)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    assert sc_show.main() == 0


@pytest.mark.parametrize('flags', [
    ['build/heartbeat/job0/route.detailed/0/outputs/heartbeat.def'],
    ['-input', 'layout def build/heartbeat/job0/route.detailed/0/outputs/heartbeat.def'],
    ['-input', 'layout gds build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds'],
    ['-input', 'layout def build/heartbeat/job0/write.gds/0/inputs/heartbeat.def',
     '-cfg', 'build/heartbeat/job0/write.gds/0/outputs/heartbeat.pkg.json']
])
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(180)
def test_sc_show(flags, monkeypatch, heartbeat_dir):
    '''Test sc-show app on a few sets of flags.'''

    os.chdir(heartbeat_dir)

    # Mock chip.run() to avoid GUI complications
    # We have separate tests in test/core/test_show.py that handle these
    # complications and test this function itself, so there's no need to
    # run it here.
    def fake_run(chip, raise_exception=False):
        # fake a png output in case this is a screenshot
        step, index = _get_flowgraph_exit_nodes(chip, flow='showflow')[0]
        os.makedirs(f'{chip.getworkdir(step=step, index=index)}/outputs', exist_ok=True)
        with open(f'{chip.getworkdir(step=step, index=index)}/outputs/{chip.top()}.png', 'w') as f:
            f.write('\n')
        return True

    monkeypatch.setattr('siliconcompiler.Chip.run', fake_run)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    assert sc_show.main() == 0


def test_sc_show_no_manifest(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'test', '-arg_step', 'invalid'])
    assert sc_show.main() == 2
