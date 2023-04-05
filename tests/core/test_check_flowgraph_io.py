import siliconcompiler

def test_check_flowgraph():
    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', 'surelog', 'import')
    chip.node(flow, 'syn', 'yosys', 'syn_asic')
    chip.edge(flow, 'import', 'syn')

    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            # Setting up tool is optional
            tool = chip.get('flowgraph', flow, step, index, 'tool')
            task = chip.get('flowgraph', flow, step, index, 'task')
            if not chip._is_builtin(tool ,task):
                chip._setup_tool(tool, task, step, index)

    assert chip._check_flowgraph_io()

def test_check_flowgraph_join():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'prejoin1', 'fake_out', 'prejoin1')
    chip.node(flow, 'prejoin2', 'fake_out', 'prejoin2')
    chip.node(flow, 'dojoin', 'builtin', 'join')
    chip.node(flow, 'postjoin', 'fake_in', 'postjoin')

    chip.edge(flow, 'prejoin1', 'dojoin')
    chip.edge(flow, 'prejoin2', 'dojoin')
    chip.edge(flow, 'dojoin', 'postjoin')

    chip.set('tool', 'fake_out', 'task', 'prejoin1', 'output', 'a.v', step='prejoin1', index='0')
    chip.set('tool', 'fake_out', 'task', 'prejoin2', 'output', 'b.v', step='prejoin2', index='0')
    chip.set('tool', 'fake_in', 'task', 'postjoin', 'input', ['a.v', 'b.v'], step='postjoin', index='0')

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=0)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=1)
    chip.node(flow, 'domin', 'builtin', 'minimum')
    chip.node(flow, 'postmin', 'fake_in', 'postmin')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake_out', 'task', 'premin', 'output', ['a.v', 'common.v'], step='premin', index='0')
    chip.set('tool', 'fake_out', 'task', 'premin', 'output', ['b.v', 'common.v'], step='premin', index='1')
    chip.set('tool', 'fake_in', 'task', 'postmin', 'input', 'common.v', step='postmin', index='0')

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min_fail():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=0)
    chip.node(flow, 'premin', 'fake_out', 'premin', index=1)
    chip.node(flow, 'domin', 'builtin', 'minimum')
    chip.node(flow, 'postmin', 'fake_in', 'postmin')

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake_out', 'task', 'premin', 'output', ['a.v'], step='premin', index='0')
    chip.set('tool', 'fake_out', 'task', 'premin', 'output', ['b.v'], step='premin', index='1')
    chip.set('tool', 'fake_in', 'task', 'postmin', 'input', 'a.v', step='postmin', index='0')

    assert not chip._check_flowgraph_io()
