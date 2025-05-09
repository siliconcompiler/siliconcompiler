import siliconcompiler

from siliconcompiler.tools.builtin import join
from siliconcompiler.tools.builtin import nop

from siliconcompiler.utils.flowgraph import nodes_to_execute


def test_nodes_to_execute():
    '''
    A -- B -- C -- D
    |              |
    ----------------
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', join)

    chip.node(flow, 'B', join)
    chip.edge(flow, 'A', 'B')

    chip.node(flow, 'C', join)
    chip.edge(flow, 'B', 'C')

    chip.node(flow, 'D', join)
    chip.edge(flow, 'A', 'D')
    chip.edge(flow, 'C', 'D')

    chip.set('option', 'flow', flow)

    assert nodes_to_execute(chip) == [('A', '0'), ('B', '0'), ('C', '0'), ('D', '0')]


def test_nodes_to_execute_to():
    '''
    Check to ensure forked graph is handled properly with to
    A -- B -- C -- D
    |    |    |    |
    Aa  [Ba]  Ca   Da
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)
        chip.node(flow, n + 'a', nop)
        chip.edge(flow, n, n + 'a')

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'to', 'Ba')

    assert nodes_to_execute(chip) == [
        ('A', '0'),
        ('B', '0'),
        ('Ba', '0')
    ]


def test_nodes_to_execute_to_multiple():
    '''
    Check to ensure forked graph is handled properly with to and multiple ends
    A -- B -- C -- D
    |    |    |    |
    Aa  [Ba]  Ca  [Da]
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)
        chip.node(flow, n + 'a', nop)
        chip.edge(flow, n, n + 'a')

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'to', ['Ba', 'Da'])

    assert nodes_to_execute(chip) == [
        ('A', '0'),
        ('B', '0'),
        ('Ba', '0'),
        ('C', '0'),
        ('D', '0'),
        ('Da', '0')
    ]


def test_nodes_to_execute_from():
    '''
    Check to ensure forked graph is handled properly with from
    A --{B}-- C -- D
    |    |    |    |
    Aa   Ba   Ca   Da
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)
        chip.node(flow, n + 'a', nop)
        chip.edge(flow, n, n + 'a')

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'from', 'B')

    assert nodes_to_execute(chip) == [
        ('B', '0'),
        ('Ba', '0'),
        ('C', '0'),
        ('Ca', '0'),
        ('D', '0'),
        ('Da', '0')
    ]


def test_nodes_to_execute_from_to():
    '''
    Check to ensure forked graph is handled properly with from/to
    A --{B}-- C -- D
    |    |    |    |
    Aa   Ba  [Ca]  Da
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)
        chip.node(flow, n + 'a', nop)
        chip.edge(flow, n, n + 'a')

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'from', 'B')
    chip.set('option', 'to', 'Ca')

    assert nodes_to_execute(chip) == [
        ('B', '0'),
        ('C', '0'),
        ('Ca', '0')
    ]


def test_nodes_to_execute_disjoint_graph_from():
    '''
    Check to ensure nodes_to_execute properly handles disjoint flowgraphs
    A --{B}-- C -- D

    E -- F -- G -- H
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'from', 'B')
    assert nodes_to_execute(chip) == [
        ('B', '0'),
        ('C', '0'),
        ('D', '0')
    ]


def test_nodes_to_execute_disjoint_graph_to():
    '''
    Check to ensure nodes_to_execute properly handles disjoint flowgraphs
    A -- B --[C]-- D

    E -- F -- G -- H
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'to', 'C')
    assert nodes_to_execute(chip) == [
        ('A', '0'),
        ('B', '0'),
        ('C', '0')
    ]


def test_nodes_to_execute_disjoint_graph_from_to():
    '''
    Check to ensure nodes_to_execute properly handles disjoint flowgraphs
    A --{B}--[C]-- D

    E -- F -- G -- H
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    chip.set('option', 'from', 'B')
    chip.set('option', 'to', 'C')
    assert nodes_to_execute(chip) == [
        ('B', '0'),
        ('C', '0')
    ]


def test_nodes_to_execute_different_flow():
    '''
    Check to ensure nodes_to_execute properly handles multiple flows
    A -- B -- C -- D (flow: test)

    E -- F -- G -- H (flow: test2)
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    flow = 'test2'

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', flow)
    assert nodes_to_execute(chip, flow='test') == [
        ('A', '0'),
        ('B', '0'),
        ('C', '0'),
        ('D', '0')
    ]
    assert nodes_to_execute(chip, flow='test2') == [
        ('E', '0'),
        ('F', '0'),
        ('G', '0'),
        ('H', '0')
    ]


def test_nodes_to_execute_different_flow_from_to():
    '''
    Check to ensure nodes_to_execute only applies from/to/prune
    to the correct flow
    {A}--[B]-- C -- D (flow: test)

     E -- F -- G -- H (flow: test2)
    '''
    chip = siliconcompiler.Chip('test')
    flow = 'test'

    prev = None
    for n in ('A', 'B', 'C', 'D'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    flow = 'test2'

    prev = None
    for n in ('E', 'F', 'G', 'H'):
        chip.node(flow, n, nop)

        if prev:
            chip.edge(flow, prev, n)

        prev = n

    chip.set('option', 'flow', 'test')
    chip.set('option', 'from', 'A')
    chip.set('option', 'to', 'B')
    assert nodes_to_execute(chip, flow='test') == [
        ('A', '0'),
        ('B', '0')
    ]
    assert nodes_to_execute(chip, flow='test2') == [
        ('E', '0'),
        ('F', '0'),
        ('G', '0'),
        ('H', '0')
    ]
