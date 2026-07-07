"""End-to-end RTL-to-GDS + signoff tests, one per demo target.

For each target this suite runs the 'gcd' design from RTL all the way to GDS
using the asicflow, then runs the correct physical-verification (signoff) flow
for that target's PDK and confirms the result is clean:

  * skywater130 -> SignoffFlow  (Magic DRC + Netgen LVS): DRC and LVS clean
  * gf180       -> DRCFlow      (KLayout DRC)            : DRC clean
  * ihp130      -> DRCFlow      (KLayout DRC)            : DRC clean
  * freepdk45   -> (no open-source signoff available)   : GDS only
  * asap7       -> (no open-source signoff available)   : GDS only

Each target bundles its correct signoff flow as a dependency (see the
``add_dep`` calls in siliconcompiler/targets/*_demo.py), so this suite selects
the flow the target itself declares rather than hard-coding the tool choice.

The interposer target is verified separately by tests/examples/test_interposer.py
(interposerflow + KLayout DRC), since it is not an RTL/asicflow design.
"""

import os.path

import pytest

from siliconcompiler import ASIC, Design
from siliconcompiler.targets import (
    asap7_demo,
    freepdk45_demo,
    gf180_demo,
    ihp130_demo,
    skywater130_demo,
)
from siliconcompiler.tools.klayout.drc import DRCTask


# Per-target signoff configuration.
#   target     : the target setup function
#   flow       : name of the bundled signoff flow to run after RTL-to-GDS, or
#                None when the PDK has no open-source signoff solution
#   drc_name   : KLayout DRC deck to select (None for the Magic-based SignoffFlow)
#   lvs        : whether the signoff flow also performs LVS
#   expect_drcs: expected DRC violation count for the gcd layout (normally 0)
_SIGNOFF = {
    "freepdk45": dict(target=freepdk45_demo, flow=None, drc_name=None, lvs=False,
                      expect_drcs=0),
    "asap7": dict(target=asap7_demo, flow=None, drc_name=None, lvs=False,
                  expect_drcs=0),
    "skywater130": dict(target=skywater130_demo, flow="signoffflow",
                        drc_name=None, lvs=True, expect_drcs=0),
    # gcd on gf180 currently has 2 known CO.6a violations (Metal1 end-of-line
    # overlap of contact) with the CI tool versions; the count shifts when the
    # tools change. Pin it so the test still exercises DRC and flags any
    # change; drop to 0 once the layout is cleaned up.
    "gf180": dict(target=gf180_demo, flow="drcflow", drc_name="drc", lvs=False,
                  expect_drcs=0),
    "ihp130": dict(target=ihp130_demo, flow="drcflow", drc_name="drc", lvs=False,
                   expect_drcs=0),
}


def _make_gcd(examples_root):
    """Build the gcd design (rtl + sdc filesets)."""
    design = Design("gcd")
    design.set_dataroot("gcd", os.path.join(examples_root, "gcd"))
    with design.active_dataroot("gcd"), design.active_fileset("rtl"):
        design.set_topmodule("gcd")
        design.add_file("gcd.v")
    with design.active_dataroot("gcd"), design.active_fileset("sdc"):
        design.add_file("gcd.sdc")
    return design


@pytest.mark.eda
@pytest.mark.parametrize("name", (
    pytest.param("freepdk45", marks=(pytest.mark.quick, pytest.mark.timeout(300))),
    pytest.param("asap7", marks=pytest.mark.timeout(1200)),
    pytest.param("skywater130", marks=pytest.mark.timeout(600)),
    pytest.param("gf180", marks=pytest.mark.timeout(1200)),
    pytest.param("ihp130", marks=(pytest.mark.quick, pytest.mark.timeout(300))),
))
def test_target_signoff(name, examples_root):
    cfg = _SIGNOFF[name]

    design = _make_gcd(examples_root)

    project = ASIC(design)
    project.add_fileset(["rtl", "sdc"])
    cfg["target"](project)
    project.set("option", "nodisplay", True)
    project.set("option", "quiet", True)
    project.option.set_jobname("rtl2gds")

    # --- Part 1: RTL-to-GDS ---
    assert project.run()

    gds = project.find_result("gds", step="write.gds")
    assert gds and os.path.isfile(gds)

    # Targets without an open-source signoff solution stop after GDS.
    if not cfg["flow"]:
        return

    # --- Part 2: signoff (DRC, and LVS where available) ---
    # Feed the generated layout (and gate-level netlist for LVS) back in as the
    # input to the signoff flow the target declared.
    with design.active_fileset("layout"):
        design.set_topmodule("gcd")
        design.add_file(gds)
        if cfg["lvs"]:
            design.add_file(project.find_result("vg", step="write.views"))
    project.add_fileset("layout", clobber=True)

    project.set_flow(cfg["flow"])
    if cfg["drc_name"]:
        DRCTask.find_task(project).set_klayout_drcname(cfg["drc_name"])
    project.option.set_jobname("signoff")

    assert project.run()

    history = project.history("signoff")

    # DRC clean (expect_drcs is 0 for every clean target; gf180 pins its known
    # CO.6a count until the layout is fixed).
    assert history.get("metric", "drcs", step="drc", index="0") == cfg["expect_drcs"]

    # LVS clean (drcs metric on the lvs step counts device/net mismatches).
    if cfg["lvs"]:
        assert history.get("metric", "drcs", step="lvs", index="0") == 0
