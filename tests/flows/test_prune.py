import siliconcompiler

from siliconcompiler.tools.builtin import nop, minimum, maximum
from core.tools.dummy import dummy
from siliconcompiler._common import SiliconCompilerError
from siliconcompiler.targets import freepdk45_demo

import pytest
import logging


def test_prune_end(caplog):
    chip = siliconcompiler.Chip('foo')
    chip.logger = logging.getLogger()
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop)
    chip.edge(flow, 'import', 'syn')
    chip.set('option', 'prune', ('syn', '0'))

    with pytest.raises(SiliconCompilerError,
                       match=f"{flow} flowgraph contains errors and cannot be run."):
        chip.run()
    assert f"These final steps in {flow} can not be reached: ['syn']" in caplog.text


def test_prune_middle(caplog):
    chip = siliconcompiler.Chip('foo')
    chip.logger = logging.getLogger()
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop)
    chip.node(flow, 'place', nop)
    chip.edge(flow, 'import', 'syn')
    chip.edge(flow, 'syn', 'place')
    chip.set('option', 'prune', ('syn', '0'))

    with pytest.raises(SiliconCompilerError,
                       match=f"{flow} flowgraph contains errors and cannot be run."):
        chip.run()
    assert f"These final steps in {flow} can not be reached: ['place']" in caplog.text


def test_prune_split():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', nop, index=0)
    chip.node(flow, 'place', nop, index=1)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', head_index=0, tail_index=0)
    chip.edge(flow, 'syn', 'place', head_index=1, tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    chip.run()


def test_prune_split_join(caplog):
    chip = siliconcompiler.Chip('foo')
    chip.logger = logging.getLogger()
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', dummy)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    message = str("Flowgraph connection from {('syn', '0')} to ('place', '0') is missing. "
                  "Double check your flowgraph and from/to/prune options.")
    with pytest.raises(SiliconCompilerError,
                       match=f'{flow} flowgraph contains errors and cannot be run.'):
        chip.run()
    assert message in caplog.text


def test_prune_min():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', minimum)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    chip.run()


def test_prune_max():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', maximum)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    chip.run()


def test_prune_max_all_inputs_pruned(caplog):
    chip = siliconcompiler.Chip('foo')
    chip.logger = logging.getLogger()
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', maximum)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', [('syn', '0'), ('syn', '1')])

    with pytest.raises(SiliconCompilerError,
                       match=f"{flow} flowgraph contains errors and cannot be run."):
        chip.run()
    assert f"These final steps in {flow} can not be reached: ['place']" in caplog.text
