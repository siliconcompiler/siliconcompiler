import siliconcompiler

from siliconcompiler.tools.builtin import nop
from siliconcompiler._common import SiliconCompilerError

import pytest
import re
import logging


def test_prune_end(caplog):
    chip = siliconcompiler.Chip('foo')
    chip.logger = logging.getLogger()
    chip.load_target('freepdk45_demo')

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
    chip.load_target('freepdk45_demo')

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
    chip.load_target('freepdk45_demo')

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


def test_prune_split_join():
    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', nop)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    message = re.escape("Flowgraph connection from {('syn', '0')} "
                        "to ('place', '0') are missing. "
                        "Double check your flowgraph and from/to/prune options.")
    with pytest.raises(SiliconCompilerError, match=message):
        chip.run()
