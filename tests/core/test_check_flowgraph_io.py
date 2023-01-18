import siliconcompiler

def test_check_flowgraph():
    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', 'surelog', 'import')
    chip.node(flow, 'syn', 'yosys', 'syn')
    chip.edge(flow, 'import', 'syn')
    chip.set('asic', 'logiclib', 'dummylib')

    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            # Setting up tool is optional
            tool = chip.get('flowgraph', flow, step, index, 'tool')
            task = chip.get('flowgraph', flow, step, index, 'task')
            if task not in chip.builtin:
                chip._setup_tool(tool, step, index)

    assert chip._check_flowgraph_io()

def test_check_flowgraph_join():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'prejoin1', 'fake_out', 'prejoin1')
    chip.node(flow, 'prejoin2', 'fake_out', 'prejoin2')
    chip.node(flow, 'dojoin', 'join', 'dojoin')
    chip.node(flow, 'postjoin', 'fake_in', 'postjoin')

    chip.edge(flow, 'prejoin1', 'dojoin')
    chip.edge(flow, 'prejoin2', 'dojoin')
    chip.edge(flow, 'dojoin', 'postjoin')

    chip.set('tool', 'fake_out', 'task', 'prejoin1', 'output', 'prejoin1', '0', 'a.v')
    chip.set('tool', 'fake_out', 'task', 'prejoin2', 'output', 'prejoin2', '0', 'b.v')
    chip.set('tool', 'fake_in', 'task', 'postjoin', 'input', 'postjoin', '0', ['a.v', 'b.v'])

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=0)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=1)
    chip.node(flow, 'domin', 'minimum', 'domin')
    chip.node(flow, 'postmin', 'fake_in', 'postmin')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake_out', 'task', 'premin', 'output', 'premin', '0', ['a.v', 'common.v'])
    chip.set('tool', 'fake_out', 'task', 'premin', 'output', 'premin', '1', ['b.v', 'common.v'])
    chip.set('tool', 'fake_in', 'task', 'postmin', 'input', 'postmin', '0', 'common.v')

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min_fail():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=0)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=1)
    chip.node(flow, 'domin', 'minimum', 'domin')
    chip.node(flow, 'postmin', 'fake_in', 'postmin')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake_out', 'task', 'premin', 'output', 'premin', '0', ['a.v'])
    chip.set('tool', 'fake_out', 'task', 'premin', 'output', 'premin', '1', ['b.v'])
    chip.set('tool', 'fake_in', 'task', 'postmin', 'input', 'postmin', '0', 'a.v')

    assert not chip._check_flowgraph_io()
