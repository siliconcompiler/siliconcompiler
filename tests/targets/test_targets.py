import pytest
from siliconcompiler.targets import \
    asap7_demo, freepdk45_demo, \
    gf180_demo, ihp130_demo, interposer_demo, skywater130_demo

from siliconcompiler import ASICProject


@pytest.mark.parametrize("target", (
        asap7_demo,
        freepdk45_demo,
        gf180_demo,
        ihp130_demo,
        interposer_demo,
        skywater130_demo))
def test_target_loading_asic(target):
    proj = ASICProject()
    proj.load_target(target.setup)

    assert len(proj.getkeys('library')) != 0
    assert proj.get("asic", "mainlib") is not None
    assert proj._has_library(proj.get("asic", "mainlib")) is True

    assert proj.get("asic", "asiclib") is not None

    assert proj.get("asic", "pdk") is not None
    assert proj._has_library(proj.get("asic", "pdk")) is True

    assert proj.get("option", "flow") is not None
    assert proj.get("option", "flow") in proj.getkeys("flowgraph")
