import siliconcompiler

def test_list_steps():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', 'join')

    chip.node(flow, 'B', 'join')
    chip.edge(flow, 'A', 'B')

    chip.node(flow, 'C', 'join')
    chip.edge(flow, 'B', 'C')

    chip.node(flow, 'D', 'join')
    chip.edge(flow, 'A', 'D')
    chip.edge(flow, 'C', 'D')

    chip.set('flow', flow)

    chip.write_flowgraph('test_list_steps.png')

    assert chip.list_steps() == ['A', 'B', 'C', 'D']
