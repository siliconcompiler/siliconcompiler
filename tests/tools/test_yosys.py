import siliconcompiler
import os
import pytest
import json

from siliconcompiler.tools.yosys import lec

from siliconcompiler.tools.builtin import nop
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'lec'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'lec', lec)
    chip.edge(flow, 'import', 'lec')
    chip.set('option', 'flow', flow)

    chip.input(os.path.join(lec_dir, 'foo.v'))
    chip.input(os.path.join(lec_dir, 'foo.vg'))

    assert chip.run()

    errors = chip.get('metric', 'drvs', step='lec', index='0')

    assert errors == 0


@pytest.mark.eda
@pytest.mark.quick
def test_yosys_lec_broken(datadir):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'lec'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'lec', lec)
    chip.edge(flow, 'import', 'lec')
    chip.set('option', 'flow', flow)

    chip.input(os.path.join(lec_dir, 'foo_broken.v'))
    chip.input(os.path.join(lec_dir, 'foo_broken.vg'))

    assert chip.run()

    errors = chip.get('metric', 'drvs', step='lec', index='0')

    assert errors == 2


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize("ext", ('v', 'vg'))
def test_screenshot(datadir, ext):
    lec_dir = os.path.join(datadir, 'lec')

    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    path = chip.show(os.path.join(lec_dir, f'foo_broken.{ext}'), screenshot=True)

    assert path
    assert os.path.exists(path)


@pytest.mark.eda
@pytest.mark.quick
def test_tristate(datadir):
    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)

    chip.set('option', 'to', 'syn')

    chip.input(os.path.join(datadir, 'tristate.v'))

    assert chip.run()

    assert chip.get('metric', 'errors', step='syn', index='0') == 0

    report_file = 'build/test/job0/syn/0/reports/stat.json'
    assert os.path.isfile(report_file)

    with open(report_file, "r") as report_data:
        stats = json.loads(report_data.read())

        assert 'design' in stats
        assert 'num_cells_by_type' in stats['design']

        cells_by_type = stats['design']['num_cells_by_type']
        assert "TBUF_X1" in cells_by_type
        assert cells_by_type["TBUF_X1"] == 1
