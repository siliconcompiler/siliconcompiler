import siliconcompiler

from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic
from tests.core.tools.fake import fake_out
from tests.core.tools.fake import fake_in

from siliconcompiler.tools.builtin import join
from siliconcompiler.tools.builtin import minimum


def test_check_flowgraph():
    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.node(flow, 'syn', syn_asic)
    chip.edge(flow, 'import', 'syn')

    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            # Setting up tool is optional
            tool = chip.get('flowgraph', flow, step, index, 'tool')
            task = chip.get('flowgraph', flow, step, index, 'task')
            if not chip._is_builtin(tool, task):
                chip._setup_node(step, index)

    assert chip._check_flowgraph_io()


def test_check_flowgraph_join():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'prejoin1', fake_out)
    chip.node(flow, 'prejoin2', fake_out)
    chip.node(flow, 'dojoin', join)
    chip.node(flow, 'postjoin', fake_in)

    chip.edge(flow, 'prejoin1', 'dojoin')
    chip.edge(flow, 'prejoin2', 'dojoin')
    chip.edge(flow, 'dojoin', 'postjoin')

    chip.set('tool', 'fake', 'task', 'fake_out', 'output', 'a.v', step='prejoin1', index='0')
    chip.set('tool', 'fake', 'task', 'fake_out', 'output', 'b.v', step='prejoin2', index='0')
    chip.set('tool', 'fake', 'task', 'fake_in', 'input', ['a.v', 'b.v'], step='postjoin', index='0')

    assert chip._check_flowgraph_io()


def test_check_flowgraph_min():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', fake_out, index=0)
    chip.node(flow, 'premin', fake_out, index=1)
    chip.node(flow, 'domin', minimum)
    chip.node(flow, 'postmin', fake_in)

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake', 'task', 'fake_out', 'output', ['a.v', 'common.v'],
             step='premin', index='0')
    chip.set('tool', 'fake', 'task', 'fake_out', 'output', ['b.v', 'common.v'],
             step='premin', index='1')
    chip.set('tool', 'fake', 'task', 'fake_in', 'input', 'common.v',
             step='postmin', index='0')

    assert chip._check_flowgraph_io()


def test_check_flowgraph_min_fail():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'premin', fake_out, index=0)
    chip.node(flow, 'premin', fake_out, index=1)
    chip.node(flow, 'domin', minimum)
    chip.node(flow, 'postmin', fake_in)

    chip.edge(flow, 'premin', 'domin', tail_index=0)
    chip.edge(flow, 'premin', 'domin', tail_index=1)
    chip.edge(flow, 'domin', 'postmin')

    chip.set('tool', 'fake', 'task', 'fake_out', 'output', ['a.v'], step='premin', index='0')
    chip.set('tool', 'fake', 'task', 'fake_out', 'output', ['b.v'], step='premin', index='1')
    chip.set('tool', 'fake', 'task', 'fake_in', 'input', 'a.v', step='postmin', index='0')

    assert not chip._check_flowgraph_io()
