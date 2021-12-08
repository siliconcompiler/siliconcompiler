import os
import hashlib
import pytest

import siliconcompiler

@pytest.mark.eda
@pytest.mark.quick
def test_klayout(datadir):
    in_def = os.path.join(datadir, 'heartbeat_wrapper.def')
    library_gds = os.path.join(datadir, 'heartbeat.gds')
    library_lef = os.path.join(datadir, 'heartbeat.lef')

    chip = siliconcompiler.Chip()
    chip.set('design', 'heartbeat_wrapper')
    chip.set('asic', 'def', in_def)

    chip.add('asic', 'macrolib', 'heartbeat')
    chip.set('library', 'heartbeat', 'lef', library_lef)
    chip.set('library', 'heartbeat', 'gds', library_gds)

    chip.set('arg', 'step', 'export')
    chip.set('eda', 'klayout', 'export', '0', 'variable', 'timestamps', 'false')
    chip.target('klayout_freepdk45')

    chip.run()

    result = chip.find_result('gds', 'export')

    with open(result, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == '1fa776a8ce442b1a4072d85d638c4bdd'
