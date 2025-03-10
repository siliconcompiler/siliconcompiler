import pytest
from siliconcompiler.targets import \
    asap7_demo, asic_demo, freepdk45_demo, \
    gf180_demo, ihp130_demo, interposer_demo, skywater130_demo
from siliconcompiler import Chip


@pytest.mark.parametrize("target", (
        asap7_demo,
        asic_demo,
        freepdk45_demo,
        gf180_demo,
        ihp130_demo,
        interposer_demo,
        skywater130_demo))
def test_target_loading(target):
    chip = Chip('')
    chip.use(target)

    assert chip.get('option', 'pdk') is not None
