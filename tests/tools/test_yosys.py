import siliconcompiler
import os
import pytest

from siliconcompiler.tools.yosys import lec

from siliconcompiler.tools.builtin import nop


@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    flow = 'lec'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'lec', lec)
    chip.edge(flow, 'import', 'lec')
    chip.set('option', 'flow', flow)

    chip.input(os.path.join(lec_dir, 'foo.v'))
    chip.input(os.path.join(lec_dir, 'foo.vg'))

    chip.run()

    errors = chip.get('metric', 'drvs', step='lec', index='0')

    assert errors == 0


@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec_broken(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.load_target('freepdk45_demo')

    flow = 'lec'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'lec', lec)
    chip.edge(flow, 'import', 'lec')
    chip.set('option', 'flow', flow)

    chip.input(os.path.join(lec_dir, 'foo_broken.v'))
    chip.input(os.path.join(lec_dir, 'foo_broken.vg'))

    chip.run()

    errors = chip.get('metric', 'drvs', step='lec', index='0')

    assert errors == 2


if __name__ == "__main__":
    from tests.fixtures import datadir
    test_yosys_lec(datadir(__file__))
