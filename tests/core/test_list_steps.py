import siliconcompiler

def test_list_steps():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', siliconcompiler, 'join')

    chip.node(flow, 'B', siliconcompiler, 'join')
    chip.edge(flow, 'A', 'B')

    chip.node(flow, 'C', siliconcompiler, 'join')
    chip.edge(flow, 'B', 'C')

    chip.node(flow, 'D', siliconcompiler, 'join')
    chip.edge(flow, 'A', 'D')
    chip.edge(flow, 'C', 'D')

    chip.set('option', 'flow', flow)

    chip.write_flowgraph('test_list_steps.png')

    assert chip.list_steps() == ['A', 'B', 'C', 'D']
