from siliconcompiler import Chip, Flow
from siliconcompiler.flowgraph import get_nodes_from, _get_flowgraph_execution_order
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


def test_exec_order():
    flow = Flow('test_flow')
    flow.node('test_flow', 'exec0', nop)
    flow.node('test_flow', 'exec1', nop)
    flow.node('test_flow', 'exec2', nop)
    flow.node('test_flow', 'exec3', nop)
    flow.node('test_flow', 'exec4', nop)

    flow.edge('test_flow', 'exec0', 'exec1')
    flow.edge('test_flow', 'exec0', 'exec2')
    flow.edge('test_flow', 'exec1', 'exec2')
    flow.edge('test_flow', 'exec2', 'exec3')
    flow.edge('test_flow', 'exec4', 'exec3')

    chip = Chip('test')
    chip.use(flow)

    order = _get_flowgraph_execution_order(chip, 'test_flow')
    assert len(order) == 4
    assert order[0] == [('exec0', '0'), ('exec4', '0')]
    assert order[1] == [('exec1', '0')]
    assert order[2] == [('exec2', '0')]
    assert order[3] == [('exec3', '0')]


def test_exec_order_reverse():
    flow = Flow('test_flow')
    flow.node('test_flow', 'exec0', nop)
    flow.node('test_flow', 'exec1', nop)
    flow.node('test_flow', 'exec2', nop)
    flow.node('test_flow', 'exec3', nop)
    flow.node('test_flow', 'exec4', nop)

    flow.edge('test_flow', 'exec0', 'exec1')
    flow.edge('test_flow', 'exec0', 'exec2')
    flow.edge('test_flow', 'exec1', 'exec2')
    flow.edge('test_flow', 'exec2', 'exec3')
    flow.edge('test_flow', 'exec4', 'exec3')

    chip = Chip('test')
    chip.use(flow)

    order = _get_flowgraph_execution_order(chip, 'test_flow', reverse=True)
    assert len(order) == 4
    assert order[0] == [('exec3', '0')]
    assert order[1] == [('exec2', '0'), ('exec4', '0')]
    assert order[2] == [('exec1', '0')]
    assert order[3] == [('exec0', '0')]


def test_exec_order_linear():
    flow = Flow('test_flow')
    flow.node('test_flow', 'exec0', nop)
    flow.node('test_flow', 'exec1', nop)
    flow.node('test_flow', 'exec2', nop)
    flow.node('test_flow', 'exec3', nop)
    flow.node('test_flow', 'exec4', nop)

    flow.edge('test_flow', 'exec0', 'exec1')
    flow.edge('test_flow', 'exec1', 'exec2')
    flow.edge('test_flow', 'exec2', 'exec3')
    flow.edge('test_flow', 'exec3', 'exec4')

    chip = Chip('test')
    chip.use(flow)

    order = _get_flowgraph_execution_order(chip, 'test_flow')
    assert len(order) == 5
    assert order[0] == [('exec0', '0')]
    assert order[1] == [('exec1', '0')]
    assert order[2] == [('exec2', '0')]
    assert order[3] == [('exec3', '0')]
    assert order[4] == [('exec4', '0')]


def test_exec_order_with_index():
    flow = Flow('test_flow')
    flow.node('test_flow', 'exec0', nop)
    flow.node('test_flow', 'exec1', nop, index='0')
    flow.node('test_flow', 'exec1', nop, index='1')
    flow.node('test_flow', 'exec1', nop, index='2')
    flow.node('test_flow', 'exec2', nop)

    flow.edge('test_flow', 'exec0', 'exec1', head_index='0')
    flow.edge('test_flow', 'exec0', 'exec1', head_index='1')
    flow.edge('test_flow', 'exec0', 'exec1', head_index='2')
    flow.edge('test_flow', 'exec1', 'exec2', tail_index='0')
    flow.edge('test_flow', 'exec1', 'exec2', tail_index='1')
    flow.edge('test_flow', 'exec1', 'exec2', tail_index='2')

    chip = Chip('test')
    chip.use(flow)

    order = _get_flowgraph_execution_order(chip, 'test_flow')
    assert len(order) == 3
    assert order[0] == [('exec0', '0')]
    assert order[1] == [('exec1', '0'), ('exec1', '1'), ('exec1', '2')]
    assert order[2] == [('exec2', '0')]
