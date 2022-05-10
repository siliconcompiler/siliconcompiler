import siliconcompiler

def test_check_flowgraph():
    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', 'surelog')
    chip.node(flow, 'syn', 'yosys')
    chip.edge(flow, 'import', 'syn')

    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            # Setting up tool is optional
            tool = chip.get('flowgraph', flow, step, index, 'tool')
            if tool not in chip.builtin:
                chip.set('arg','step', step)
                chip.set('arg','index', index)
                func = chip.find_function(tool, 'setup', 'tools')
                func(chip)
                # Need to clear index, otherwise we will skip
                # setting up other indices. Clear step for good
                # measure.
                chip.set('arg','step', None)
                chip.set('arg','index', None)

    assert chip._check_flowgraph_io()

def test_check_flowgraph_join():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'prejoin1', 'fake_out')
    chip.node(flow, 'prejoin2', 'fake_out')
    chip.node(flow, 'dojoin', 'join')
    chip.node(flow, 'postjoin', 'fake_in')

    chip.edge(flow, 'prejoin1', 'dojoin')
    chip.edge(flow, 'prejoin2', 'dojoin')
    chip.edge(flow, 'dojoin', 'postjoin')

    chip.set('tool', 'fake_out', 'output', 'prejoin1', '0', 'a.v')
    chip.set('tool', 'fake_out', 'output', 'prejoin2', '0', 'b.v')
    chip.set('tool', 'fake_in', 'input', 'postjoin', '0', ['a.v', 'b.v'])

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', index=0)
    chip.node(flow, 'premin', 'fake_out', index=1)
    chip.node(flow, 'domin', 'minimum')
    chip.node(flow, 'postmin', 'fake_in')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake_out', 'output', 'premin', '0', ['a.v', 'common.v'])
    chip.set('tool', 'fake_out', 'output', 'premin', '1', ['b.v', 'common.v'])
    chip.set('tool', 'fake_in', 'input', 'postmin', '0', 'common.v')

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min_fail():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', index=0)
    chip.node(flow, 'premin', 'fake_out', index=1)
    chip.node(flow, 'domin', 'minimum')
    chip.node(flow, 'postmin', 'fake_in')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake_out', 'output', 'premin', '0', ['a.v'])
    chip.set('tool', 'fake_out', 'output', 'premin', '1', ['b.v'])
    chip.set('tool', 'fake_in', 'input', 'postmin', '0', 'a.v')

    assert not chip._check_flowgraph_io()
