from siliconcompiler import Chip
from siliconcompiler.flowgraph import get_nodes_from
from siliconcompiler.targets import freepdk45_demo


def test_get_nodes_from():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    nodes = get_nodes_from(chip, chip.get('option', 'flow'), [('dfm', '0')])
    assert ('route', '0') not in nodes
    assert ('dfm', '0') in nodes
    assert ('write_gds', '0') in nodes
    assert ('write_data', '0') in nodes


def test_get_nodes_from_with_prune():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    chip.set('option', 'prune', ('write_gds', '0'))

    nodes = get_nodes_from(chip, chip.get('option', 'flow'), [('dfm', '0')])
    assert ('route', '0') not in nodes
    assert ('dfm', '0') in nodes
    assert ('write_gds', '0') not in nodes
    assert ('write_data', '0') in nodes


def test_get_nodes_from_with_to():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    chip.set('option', 'to', 'dfm')

    nodes = get_nodes_from(chip, chip.get('option', 'flow'), [('route', '0')])
    assert ('cts', '0') not in nodes
    assert ('route', '0') in nodes
    assert ('dfm', '0') in nodes
    assert ('write_gds', '0') not in nodes
    assert ('write_data', '0') not in nodes
