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
        chip.run(raise_exception=True)
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
        chip.run(raise_exception=True)
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

    assert chip.run()


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
        chip.run(raise_exception=True)
    assert message in caplog.text


def test_prune_nodenotpresent(capfd):
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'compile', nop)
    chip.node(flow, 'elaborate', nop)
    chip.node(flow, 'sim1', nop, index=0)
    chip.node(flow, 'sim1', nop, index=1)
    chip.node(flow, 'sim3', nop)
    chip.node(flow, 'sim4', nop)
    chip.node(flow, 'merge', nop)
    chip.node(flow, 'report', nop)

    chip.edge(flow, 'compile', 'elaborate')
    chip.edge(flow, 'elaborate', 'sim1', head_index=0)
    chip.edge(flow, 'elaborate', 'sim1', head_index=1)
    chip.edge(flow, 'elaborate', 'sim3')
    chip.edge(flow, 'elaborate', 'sim4')
    chip.edge(flow, 'sim1', 'merge', tail_index=0)
    chip.edge(flow, 'sim1', 'merge', tail_index=1)
    chip.edge(flow, 'sim3', 'merge')
    chip.edge(flow, 'sim4', 'merge')
    chip.edge(flow, 'merge', 'report')
    chip.set('option', 'prune', [('sim1', '3')])

    with pytest.raises(SiliconCompilerError,
                       match="test flowgraph contains errors and cannot be run."):
        chip.run(raise_exception=True)
    assert "sim13 is not defined in the test flowgraph" in capfd.readouterr().out


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

    assert chip.run()


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

    assert chip.run()


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
        chip.run(raise_exception=True)
    assert f"These final steps in {flow} can not be reached: ['place']" in caplog.text
