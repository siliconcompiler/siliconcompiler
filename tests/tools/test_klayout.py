import os
import hashlib
import json
import pytest

import siliconcompiler

from siliconcompiler.tools.klayout import export
from siliconcompiler.tools.klayout import operations
from siliconcompiler.tools.klayout import drc
from siliconcompiler.tools.klayout import convert_drc_db

from siliconcompiler.tools.builtin import nop
from siliconcompiler.targets import freepdk45_demo


@pytest.fixture
def setup_pdk_test(monkeypatch, datadir):
    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(datadir)


@pytest.mark.eda
@pytest.mark.quick
def test_klayout(datadir):
    in_def = os.path.join(datadir, 'heartbeat_wrapper.def')
    library_gds = os.path.join(datadir, 'heartbeat.gds')
    library_lef = os.path.join(datadir, 'heartbeat.lef')

    chip = siliconcompiler.Chip('heartbeat_wrapper')
    chip.use(freepdk45_demo)

    chip.input(in_def)

    chip.add('asic', 'macrolib', 'heartbeat')

    lib = siliconcompiler.Library('heartbeat')
    lib.set('output', '10M', 'lef', library_lef)
    lib.set('output', '10M', 'gds', library_gds)
    chip.use(lib)

    flow = 'export'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'export', export)
    chip.edge(flow, 'import', 'export')
    chip.set('option', 'flow', flow)

    chip.set('tool', 'klayout', 'task', 'export', 'var', 'timestamps', 'false')

    assert chip.run()

    result = chip.find_result('gds', 'export')

    with open(result, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == '033839a1f1597c15c6ce7e4de24a15d5'


@pytest.mark.eda
@pytest.mark.quick
def test_klayout_operations(datadir):
    library_gds = os.path.join(datadir, 'heartbeat.gds')

    chip = siliconcompiler.Chip('heartbeat')
    chip.use(freepdk45_demo)

    chip.input(library_gds)

    flow = 'klayout_ops'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'ops1', operations)
    chip.node(flow, 'ops2', operations)
    chip.edge(flow, 'import', 'ops1')
    chip.edge(flow, 'ops1', 'ops2')
    chip.set('option', 'flow', flow)

    chip.set('tool', 'klayout', 'task', 'operations', 'var', 'timestamps', 'false')

    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'rotate', step='ops1')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:rotate.gds', step='ops1')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'rotate', step='ops1')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'outline:tool,klayout,task,operations,var,outline', step='ops1')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:outline.gds', step='ops1')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'rename:tool,klayout,task,operations,var,name', step='ops1')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:rename.gds', step='ops1')

    chip.set('tool', 'klayout', 'task', 'operations', 'var', 'outline', ['255', '0'], step='ops1')
    chip.set('tool', 'klayout', 'task', 'operations', 'var', 'name', 'new_name', step='ops1')
    chip.set('tool', 'klayout', 'task', 'operations', 'var', 'name', 'new_top', step='ops2')

    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'merge:rotate.gds', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:rotate.gds', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'add:outline.gds', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:outline.gds', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'add_top:tool,klayout,task,operations,var,name', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:add_top.gds', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'rename_cell:tool,klayout,task,operations,var,rename_cell', step='ops2')
    chip.add('tool', 'klayout', 'task', 'operations', 'var', 'operations',
             'write:rename_cells.gds', step='ops2')

    chip.set('tool', 'klayout', 'task', 'operations', 'var', 'rename_cell', 'AND4_X1=AND_dummy',
             step='ops2')

    assert chip.run()

    ops1_result = chip.getworkdir(step='ops1')
    for op_file, op_hash in [('rotate.gds', '0048802f8d2fedf038cb6cfdc5ebc989'),
                             ('outline.gds', '4bf006f5f465ec9c42cd1ef80677424e'),
                             ('rename.gds', '4991f2267811517b8f7e73924b92128e')]:
        path = os.path.join(ops1_result, 'outputs', op_file)
        assert os.path.exists(path)
        with open(path, 'rb') as gds_file:
            data = gds_file.read()
            assert hashlib.md5(data).hexdigest() == op_hash

    ops2_result = chip.getworkdir(step='ops2')
    for op_file, op_hash in [('rotate.gds', 'ee2e5b9646ca4f7e941dd1767af47188'),
                             ('outline.gds', '753e1a252baaa6c9dbb3e9528a3eef3c'),
                             ('add_top.gds', '2c6f39ff49088278bafa51adfd761e61'),
                             ('rename_cells.gds', '4253ee90771c0fcaf0c4c95010783cef')]:
        path = os.path.join(ops2_result, 'outputs', op_file)
        assert os.path.exists(path)
        with open(path, 'rb') as gds_file:
            data = gds_file.read()
            assert hashlib.md5(data).hexdigest() == op_hash


def test_pdk(setup_pdk_test):
    import klayout_pdk

    chip = siliconcompiler.Chip('interposer')
    chip.use(klayout_pdk)

    assert chip.check_filepaths()


@pytest.mark.eda
@pytest.mark.quick
def test_drc_pass(setup_pdk_test, datadir):
    import klayout_pdk

    chip = siliconcompiler.Chip('interposer')
    chip.use(klayout_pdk)

    flow = siliconcompiler.Flow('drc_flow')
    flow.node('drc_flow', 'drc', drc)

    chip.use(flow)

    chip.set('option', 'flow', 'drc_flow')

    chip.input(os.path.join(datadir, 'klayout_pdk', 'interposer.gds'))

    chip.set('option', 'pdk', 'faux')
    chip.set('option', 'stackup', 'M5')

    assert chip.run()

    assert chip.get('metric', 'drcs', step='drc', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
def test_drc_fail(setup_pdk_test, datadir):
    import klayout_pdk

    chip = siliconcompiler.Chip('interposer')
    chip.use(klayout_pdk)

    flow = siliconcompiler.Flow('drc_flow')
    flow.node('drc_flow', 'drc', drc)

    chip.use(flow)

    chip.set('option', 'flow', 'drc_flow')

    chip.input(os.path.join(datadir, 'klayout_pdk', 'interposer_drcs.gds'))

    chip.set('option', 'pdk', 'faux')
    chip.set('option', 'stackup', 'M5')

    assert chip.run()

    assert chip.get('metric', 'drcs', step='drc', index='0') == 12


@pytest.mark.eda
@pytest.mark.quick
def test_convert_drc(setup_pdk_test, datadir):
    import klayout_pdk

    chip = siliconcompiler.Chip('interposer')
    chip.use(klayout_pdk)

    flow = siliconcompiler.Flow('drc_flow')
    flow.node('drc_flow', 'drc', drc)
    flow.node('drc_flow', 'convert', convert_drc_db)
    flow.edge('drc_flow', 'drc', 'convert')

    chip.use(flow)

    chip.set('option', 'flow', 'drc_flow')

    chip.input(os.path.join(datadir, 'klayout_pdk', 'interposer_drcs.gds'))

    chip.set('option', 'pdk', 'faux')
    chip.set('option', 'stackup', 'M5')

    assert chip.run()

    assert chip.get('metric', 'drcs', step='drc', index='0') == 12

    lyrdb = chip.find_node_file("inputs/interposer.lyrdb", step="convert")
    assert lyrdb
    odb_json = chip.find_result('json', step='convert')
    assert odb_json
    assert os.path.isfile(odb_json)

    with open(odb_json, 'r') as f:
        data = json.load(f)

    assert "interposer.lyrdb" in data
    assert "source" in data["interposer.lyrdb"]

    assert data["interposer.lyrdb"]["source"] == lyrdb
    data["interposer.lyrdb"]["source"] = "sourcefile"

    assert "category" in data["interposer.lyrdb"]
    assert len(data["interposer.lyrdb"]["category"]) == 3
    for cat in data["interposer.lyrdb"]["category"]:
        assert data["interposer.lyrdb"]["category"][cat]["source"] == lyrdb
        data["interposer.lyrdb"]["category"][cat]["source"] = "sourcefile"

    assert hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest() == \
        '6ee3d048a257ccb7f2c0e86333b2044d0173c5c0'
