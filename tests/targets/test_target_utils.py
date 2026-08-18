import pytest

from siliconcompiler import ASIC
from siliconcompiler.targets._utils import asic_target


# Every name accepted by asic_target(), the target it must dispatch to, and the
# PDK that target is expected to select.
TARGETS = (
    ("asap7", "asap7"),
    ("freepdk45", "freepdk45"),
    ("gf180", "GF180_5LM_1TM_9K_9t"),
    ("ihp130", "ihp130"),
    ("skywater130", "skywater130"),
    ("sky130", "skywater130"),
    ("icsprout55", "icsprout55"),
    ("ics55", "icsprout55"),
    ("gt2n", "gt2n"),
)


@pytest.mark.parametrize("pdk,expect_pdk", TARGETS)
def test_asic_target_pdk(pdk, expect_pdk):
    # The requested PDK must be the one that ends up loaded, not just any PDK.
    proj = ASIC()
    asic_target(proj, pdk)

    assert proj.get("asic", "pdk") == expect_pdk
    assert proj._has_library(expect_pdk) is True

    # No other PDK leaked into the project.
    other_pdks = {other for _, other in TARGETS if other != expect_pdk}
    assert other_pdks.isdisjoint(proj.getkeys("library"))
