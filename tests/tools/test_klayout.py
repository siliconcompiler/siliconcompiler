import os
import hashlib
import pytest

import siliconcompiler

from siliconcompiler.tools.klayout import export

from siliconcompiler.tools.builtin import nop


@pytest.mark.eda
@pytest.mark.quick
def test_klayout(datadir):
    in_def = os.path.join(datadir, 'heartbeat_wrapper.def')
    library_gds = os.path.join(datadir, 'heartbeat.gds')
    library_lef = os.path.join(datadir, 'heartbeat.lef')

    chip = siliconcompiler.Chip('heartbeat_wrapper')
    chip.load_target('freepdk45_demo')

    chip.input(in_def)

    chip.add('asic', 'macrolib', 'heartbeat')

    lib = siliconcompiler.Library(chip, 'heartbeat')
    lib.set('output', '10M', 'lef', library_lef)
    lib.set('output', '10M', 'gds', library_gds)
    chip.use(lib)

    flow = 'export'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'export', export)
    chip.edge(flow, 'import', 'export')
    chip.set('option', 'flow', flow)

    chip.set('tool', 'klayout', 'task', 'export', 'var', 'timestamps', 'false')

    chip.run()

    result = chip.find_result('gds', 'export')

    with open(result, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == '537785c8c2dcbb0dae7ef5fc0b72556b'
