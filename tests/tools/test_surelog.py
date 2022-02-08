import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_surelog(scroot):
    gcd_src = os.path.join(scroot, 'examples', 'gcd', 'gcd.v')
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.set('flow', 'test')
    chip.load_tool('surelog', standalone=True)

    chip.run()

    assert chip.find_result('v', step=step) is not None

@pytest.mark.eda
@pytest.mark.quick
def test_surelog_preproc_regression(datadir):
    src = os.path.join(datadir, 'test_preproc.v')
    design = 'test_preproc'
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')

    chip.add('source', src)
    chip.add('define', 'MEM_ROOT=test')
    chip.set('design', design)
    chip.set('mode', 'asicflow')
    chip.set('arg', 'step', step)
    chip.set('flow', 'test')
    chip.load_tool('surelog', standalone=True)

    chip.run()

    result = chip.find_result('v', step=step)

    assert result is not None

    with open(result, 'r') as vlog:
        assert "`MEM_ROOT" not in vlog.read()

if __name__ == "__main__":
    from tests.fixtures import scroot
    from tests.fixtures import datadir
    test_surelog(scroot())
    test_surelog_preproc_regression(datadir(__file__))
