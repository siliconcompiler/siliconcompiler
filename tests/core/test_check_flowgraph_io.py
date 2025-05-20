import siliconcompiler
from siliconcompiler.scheduler import _setup_node

from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.yosys import syn_asic
from core.tools.fake import fake_out
from core.tools.fake import fake_in

from siliconcompiler.tools.builtin import join
from siliconcompiler.tools.builtin import minimum
from siliconcompiler.utils.flowgraph import _check_flowgraph_io
from siliconcompiler.targets import freepdk45_demo


def test_check_flowgraph_io():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    chip.input('foo.v')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.node(flow, 'syn', syn_asic)
    chip.edge(flow, 'import', 'syn')

    _setup_node(chip, 'import', '0')
    _setup_node(chip, 'syn', '0')

    assert _check_flowgraph_io(chip)


def test_check_flowgraph_io_join():

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

    assert _check_flowgraph_io(chip)


def test_check_flowgraph_io_min():

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

    assert _check_flowgraph_io(chip)


def test_check_flowgraph_io_min_fail():

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

    assert not _check_flowgraph_io(chip)


def test_check_flowgraph_io_disallow_multiple():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'prejoin1', fake_out)
    chip.node(flow, 'prejoin2', fake_out)
    chip.node(flow, 'postjoin', fake_in)

    chip.edge(flow, 'prejoin1', 'postjoin')
    chip.edge(flow, 'prejoin2', 'postjoin')

    chip.set('tool', 'fake', 'task', 'fake_out', 'output', 'a.v', step='prejoin1', index='0')
    chip.set('tool', 'fake', 'task', 'fake_out', 'output', 'a.v', step='prejoin2', index='0')
    chip.set('tool', 'fake', 'task', 'fake_in', 'input', ['a.v'], step='postjoin', index='0')

    assert not _check_flowgraph_io(chip)


def test_check_flowgraph_io_allow_multiple():

    chip = siliconcompiler.Chip('foo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'prejoin1', fake_out)
    chip.node(flow, 'prejoin2', fake_out)
    chip.node(flow, 'postjoin', fake_in)

    chip.edge(flow, 'prejoin1', 'postjoin')
    chip.edge(flow, 'prejoin2', 'postjoin')

    chip.set('tool', 'fake', 'task', 'fake_out', 'output', 'a.v', step='prejoin1', index='0')
    chip.set('tool', 'fake', 'task', 'fake_out', 'output', 'a.v', step='prejoin2', index='0')
    chip.set('tool', 'fake', 'task', 'fake_in', 'input', ['a.prejoin10.v', 'a.prejoin20.v'],
             step='postjoin', index='0')

    assert _check_flowgraph_io(chip)
