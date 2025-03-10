import os
import siliconcompiler

import pytest
from siliconcompiler.targets import freepdk45_demo


@pytest.fixture
def chip(datadir):
    # Create instance of Chip class
    chip = siliconcompiler.Chip('bad')

    # Inserting value into configuration
    chip.input(os.path.join(datadir, 'bad.v'))
    chip.set('design', 'bad')
    chip.set('constraint', 'outline', [(0, 0), (10, 10)])
    chip.set('constraint', 'corearea', [(1, 1), (9, 9)])
    chip.use(freepdk45_demo)

    chip.add('option', 'to', 'syn')

    return chip


def test_incomplete_flowgraph():
    '''Test that SC exits early when flowgraph is incomplete
    '''

    chip = siliconcompiler.Chip('gcd')
    chip.use(freepdk45_demo)

    flow = chip.get('option', 'flow')

    chip.edge(flow, 'export', 'dummy_step')

    # Expect that command exits early
    try:
        chip.run(raise_exception=True)
    except siliconcompiler.SiliconCompilerError as e:
        assert str(e).startswith(flow)
    else:
        assert False
