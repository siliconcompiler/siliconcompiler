import siliconcompiler

from siliconcompiler.tools.builtin import nop

from siliconcompiler.utils.flowgraph import nodes_to_execute


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
    assert nodes_to_execute(chip, flow='test') == (
        ('A', '0'),
        ('B', '0'),
        ('C', '0'),
        ('D', '0')
    )
    assert nodes_to_execute(chip, flow='test2') == (
        ('E', '0'),
        ('F', '0'),
        ('G', '0'),
        ('H', '0')
    )
