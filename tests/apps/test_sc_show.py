import os

import pytest
import siliconcompiler

from siliconcompiler.apps import sc_show
from siliconcompiler import Chip

# TODO: I think moving back to something like a tarfile would be nice here to
# remove the dependency on EDA tools. Maybe make that tarfile the single source
# of truth rather than gcd.pkg.json.
@pytest.fixture(scope='module')
@pytest.mark.skip(reason='schema_rearchitect')
def heartbeat_dir(tmpdir_factory):
    '''Fixture that creates a heartbeat build directory by running a build.
    '''
    scroot = os.path.join(os.path.dirname(__file__), '..', '..')
    datadir = os.path.join(scroot, 'tests', 'data')

    cwd = str(tmpdir_factory.mktemp("heartbeat"))

    os.chdir(cwd)
    chip = siliconcompiler.Chip('heartbeat')
    chip.set('option', 'loglevel', 'ERROR')
    chip.set('option', 'quiet', True)
    chip.add('source', 'verilog', os.path.join(datadir, 'heartbeat.v'))
    chip.load_target('freepdk45_demo')
    chip.run()

    return cwd

@pytest.mark.parametrize('flags', [
    ['-source', 'def build/heartbeat/job0/dfm/0/outputs/heartbeat.def'],
    ['-read_gds', 'gds build/heartbeat/job0/export/0/outputs/heartbeat.gds'],
    ['-design', 'heartbeat'],
    ['-source', 'def build/heartbeat/job0/export/0/inputs/heartbeat.def',
     '-cfg', 'build/heartbeat/job0/export/0/outputs/heartbeat.pkg.json']
    ])
@pytest.mark.eda
@pytest.mark.quick
def test_sc_show(flags, monkeypatch, heartbeat_dir):
    '''Test sc-show app on a few sets of flags.'''

    # Mock chip.show() to avoid GUI complications
    # We have separate tests in test/core/test_show.py that handle these
    # complications and test this function itself, so there's no need to
    # run it here.
    def fake_show(chip, filename):
        # Test basic conditions required for chip.show() to work, to make sure
        # that the sc-show app set up the chip object correctly.
        assert os.path.exists(filename)

        ext = os.path.splitext(filename)[1][1:]
        assert chip.get('option', 'showtool', ext)

        sc_stackup = chip.get('pdk', 'stackup')[0]
        tech_file = chip.get('pdk', 'layermap', 'klayout', 'def', 'gds', sc_stackup)[0]
        assert tech_file is not None

        chip.logger.info('Showing ' + filename)
        return True

    os.chdir(heartbeat_dir)

    monkeypatch.setattr(Chip, 'show', fake_show)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    assert sc_show.main() == 0
