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

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.target('surelog')

    chip.run()

    assert chip.find_result('v', step=step) is not None

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_surelog(scroot())
