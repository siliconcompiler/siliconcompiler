from siliconcompiler import Chip, Flow
from siliconcompiler.utils.flowgraph import get_nodes_from
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.tools.builtin import nop


def test_get_nodes_from():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    nodes = get_nodes_from(chip, chip.get('option', 'flow'), [('dfm.metal_fill', '0')])
    assert ('route.detailed', '0') not in nodes
    assert ('dfm.metal_fill', '0') in nodes
    assert ('write.gds', '0') in nodes
    assert ('write.views', '0') in nodes


def test_get_nodes_from_with_prune():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    chip.set('option', 'prune', ('write.gds', '0'))

    nodes = get_nodes_from(chip, chip.get('option', 'flow'), [('dfm.metal_fill', '0')])
    assert ('route.detailed', '0') not in nodes
    assert ('dfm.metal_fill', '0') in nodes
    assert ('write.gds', '0') not in nodes
    assert ('write.views', '0') in nodes


def test_get_nodes_from_with_to():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    chip.set('option', 'to', 'dfm.metal_fill')

    nodes = get_nodes_from(chip, chip.get('option', 'flow'), [('route.detailed', '0')])
    assert ('cts.clock_tree_synthesis', '0') not in nodes
    assert ('route.detailed', '0') in nodes
    assert ('dfm.metal_fill', '0') in nodes
    assert ('write.gds', '0') not in nodes
    assert ('write.views', '0') not in nodes
