import os
import tarfile

import pytest

from siliconcompiler.apps import sc_show
from siliconcompiler import Chip

@pytest.fixture
def heartbeat_dir(scroot):
    '''Fixture that extracts a tarred copy of the heartbeat build dir into test
    directory.
    '''
    datadir = os.path.join(scroot, 'tests', 'data')
    with tarfile.open(os.path.join(datadir, 'heartbeat.tar.gz')) as tar:
        tar.extractall()

    return os.path.join(os.getcwd(), 'build')

@pytest.mark.parametrize('flags', [
    ['-asic_def', 'build/heartbeat/job0/export/0/inputs/heartbeat.def'],
    ['-asic_gds', 'build/heartbeat/job0/export/0/outputs/heartbeat.gds'],
    ['-design', 'heartbeat'],
    ['-asic_def', 'build/heartbeat/job0/export/0/inputs/heartbeat.def',
        '-cfg', 'build/heartbeat/job0/export/0/inputs/heartbeat.pkg.json']
    ])
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
        assert chip.get('showtool', ext)

        sc_stackup = chip.get('pdk', 'stackup')[0]
        tech_file = chip.get('pdk', 'layermap', sc_stackup, 'def', 'gds')[0]
        assert tech_file is not None

        chip.logger.info('Showing ' + filename)
        return True
    monkeypatch.setattr(Chip, 'show', fake_show)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    assert sc_show.main() == 0
