import os

import pytest
import siliconcompiler

from siliconcompiler.apps import sc_show
from siliconcompiler.flowgraph import _get_flowgraph_exit_nodes
from siliconcompiler.targets import freepdk45_demo


# TODO: I think moving back to something like a tarfile would be nice here to
# remove the dependency on EDA tools. Maybe make that tarfile the single source
# of truth rather than gcd.pkg.json.
@pytest.fixture(scope='module')
def heartbeat_dir(tmpdir_factory):
    '''Fixture that creates a heartbeat build directory by running a build.
    '''
    scroot = os.path.join(os.path.dirname(__file__), '..', '..')
    datadir = os.path.join(scroot, 'tests', 'data')

    cwd = str(tmpdir_factory.mktemp("heartbeat"))

    os.chdir(cwd)
    chip = siliconcompiler.Chip('heartbeat')
    chip.set('option', 'loglevel', 'error')
    chip.set('option', 'quiet', True)
    chip.input(os.path.join(datadir, 'heartbeat.v'))
    chip.input(os.path.join(datadir, 'heartbeat.sdc'))
    chip.use(freepdk45_demo)
    chip.run()

    return cwd


@pytest.mark.parametrize('flags', [
    [],
    ['-design', 'heartbeat'],
    ['-design', 'heartbeat',
     '-arg_step', 'floorplan'],
    ['-design', 'heartbeat',
     '-arg_step', 'floorplan',
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
    def fake_run(chip):
        # fake a png output in case this is a screenshot
        step, index = _get_flowgraph_exit_nodes(chip, flow='showflow')[0]
        os.makedirs(f'{chip.getworkdir(step=step, index=index)}/outputs', exist_ok=True)
        with open(f'{chip.getworkdir(step=step, index=index)}/outputs/{chip.top()}.png', 'w') as f:
            f.write('\n')

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
    def fake_run(chip):
        # fake a png output in case this is a screenshot
        step, index = _get_flowgraph_exit_nodes(chip, flow='showflow')[0]
        os.makedirs(f'{chip.getworkdir(step=step, index=index)}/outputs', exist_ok=True)
        with open(f'{chip.getworkdir(step=step, index=index)}/outputs/{chip.top()}.png', 'w') as f:
            f.write('\n')

    monkeypatch.setattr('siliconcompiler.Chip.run', fake_run)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    assert sc_show.main() == 0
