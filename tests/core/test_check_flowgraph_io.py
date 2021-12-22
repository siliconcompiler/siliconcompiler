import siliconcompiler

def test_check_flowgraph():
    chip = siliconcompiler.Chip()

    chip.set('design', 'foo')
    chip.add('source', 'foo.v')

    chip.node('import', 'surelog')
    chip.node('syn', 'yosys')
    chip.edge('import', 'syn')

    for step in chip.getkeys('flowgraph'):
        for index in chip.getkeys('flowgraph', step):
            # Setting up tool is optional
            tool = chip.get('flowgraph', step, index, 'tool')
            if tool not in chip.builtin:
                chip.set('arg','step', step)
                chip.set('arg','index', index)
                func = chip.find_function(tool, 'tool', 'setup_tool')
                func(chip)
                # Need to clear index, otherwise we will skip
                # setting up other indices. Clear step for good
                # measure.
                chip.set('arg','step', None)
                chip.set('arg','index', None)

    assert chip._check_flowgraph_io()

def test_check_flowgraph_join():
    chip = siliconcompiler.Chip()

    chip.set('design', 'foo')

    chip.node('prejoin1', 'fake_out')
    chip.node('prejoin2', 'fake_out')
    chip.node('dojoin', 'join')
    chip.node('postjoin', 'fake_in')

    chip.edge('prejoin1', 'dojoin')
    chip.edge('prejoin2', 'dojoin')
    chip.edge('dojoin', 'postjoin')

    chip.set('eda', 'fake_out', 'output', 'prejoin1', '0', 'a.v')
    chip.set('eda', 'fake_out', 'output', 'prejoin2', '0', 'b.v')
    chip.set('eda', 'fake_in', 'input', 'postjoin', '0', ['a.v', 'b.v'])

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min():
    chip = siliconcompiler.Chip()

    chip.set('design', 'foo')

    chip.node('premin', 'fake_out', index=0)
    chip.node('premin', 'fake_out', index=1)
    chip.node('domin', 'minimum')
    chip.node('postmin', 'fake_in')

    chip.edge('premin', 'domin', tail_index=0)
    chip.edge('premin', 'domin', tail_index=1)
    chip.edge('domin', 'postmin')

    chip.set('eda', 'fake_out', 'output', 'premin', '0', ['a.v', 'common.v'])
    chip.set('eda', 'fake_out', 'output', 'premin', '1', ['b.v', 'common.v'])
    chip.set('eda', 'fake_in', 'input', 'postmin', '0', 'common.v')

    assert chip._check_flowgraph_io()

def test_check_flowgraph_min_fail():
    chip = siliconcompiler.Chip()

    chip.set('design', 'foo')

    chip.node('premin', 'fake_out', index=0)
    chip.node('premin', 'fake_out', index=1)
    chip.node('domin', 'minimum')
    chip.node('postmin', 'fake_in')

    chip.edge('premin', 'domin', tail_index=0)
    chip.edge('premin', 'domin', tail_index=1)
    chip.edge('domin', 'postmin')

    chip.set('eda', 'fake_out', 'output', 'premin', '0', ['a.v'])
    chip.set('eda', 'fake_out', 'output', 'premin', '1', ['b.v'])
    chip.set('eda', 'fake_in', 'input', 'postmin', '0', 'a.v')

    assert not chip._check_flowgraph_io()
