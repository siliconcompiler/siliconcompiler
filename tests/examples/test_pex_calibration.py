import pytest

import os.path


@pytest.mark.eda
@pytest.mark.nocpulimit
@pytest.mark.timeout(1800)
def test_py_calibrate():
    """Daily guard: keep the PEX estimate calibration example working end to end.

    Drives ``examples/pex_calibration/calibrate.py`` on a single small design
    (gcd, rather than the full demo survey, for runtime): the bench_wires
    initial-model phase and the calibration-survey phase, then the reuse
    (no-rerun) path. Checks deck-consistent initial values, sane per-layer
    correction factors, and that the data files are written and reused.
    """
    from siliconcompiler.tools.openroad.utils import pex_calibrate as pc
    from pex_calibration import calibrate

    # One-design survey (gcd) for speed; the demo suite's smallest design.
    model, factors = calibrate.main(designs=[pc.GCD()], outdir="pex")

    # Data files are written.
    assert os.path.isfile("pex/freepdk45.rclayer.csv")
    assert os.path.isfile("pex/freepdk45.rccorr.csv")

    # Initial model: resistance is deck-exact for freepdk45 metal2; capacitance
    # is a real (small, positive SI) value. Guards the segment walk + units.
    assert "typical" in model
    metal2 = model["typical"]["metal2"]
    assert metal2["source"] == "bench"
    assert 3.0 < metal2["res"] < 4.0
    # freepdk45 metal2 is ~1.2e-16 F/um; the band tolerates PDK/tool drift but
    # still catches an fF/pF unit slip in the segment walk (~1000x off).
    assert 5e-17 < metal2["cap"] < 5e-16

    # Correction factors: the heavily-used lower layers must be characterized.
    assert "typical" in factors
    typ = factors["typical"]
    assert "metal2" in typ
    assert "metal3" in typ
    for layer, info in typ.items():
        assert info["nseg"] > 0
        # Loose sanity band: this only has to catch a unit slip or a broken
        # segment walk (which land orders of magnitude out), not pin down a
        # value. Lightly-routed upper layers are genuinely noisy, so the
        # direction of the correction is asserted only on metal2 below.
        assert 0.01 < info["cap_factor"] < 100.0, layer
    # Headline check: on freepdk45 the bench_wires pattern set over-predicts
    # capacitance per unit length relative to real routing, so on the
    # best-sampled layer the survey must *de-rate* it - cap_factor below 1.0.
    # This asserts the direction of the correction, not merely that it is
    # positive. (The direction is a property of this PDK's pattern set, not a
    # universal guarantee; it is asserted here because a flipped sign would mean
    # the estimate and golden sides got swapped.)
    assert typ["metal2"]["cap_factor"] < 0.95
    # Resistance is deck-exact, so the resistance factor on a well-sampled layer
    # sits right at 1.0 (guards the unit handling / segment walk).
    assert 0.9 < typ["metal2"]["res_factor"] < 1.1

    # Reuse path: the data files are present, so a second call returns the same
    # numbers without recomputing.
    model2, factors2 = calibrate.main(designs=[pc.GCD()], outdir="pex")
    assert set(model2["typical"]) == set(model["typical"])
    assert abs(factors2["typical"]["metal2"]["cap_factor"]
               - typ["metal2"]["cap_factor"]) < 1e-6


@pytest.mark.eda
@pytest.mark.nocpulimit
@pytest.mark.timeout(2400)
def test_py_calibrate_score(capsys):
    """Exercise the --score path end to end: derive, then re-route the survey
    uncorrected and calibrated and print the per-net error table.

    Smoke-checks that the scoring path runs and produces a before/after summary
    (not that the win is a specific size - a single tiny design is too noisy to
    pin a number).
    """
    from siliconcompiler.tools.openroad.utils import pex_calibrate as pc
    from pex_calibration import calibrate

    calibrate.main(designs=[pc.GCD()], outdir="pex", score=True)

    captured = capsys.readouterr()
    # The score table (stdout) names the corner and its metrics; the heading
    # goes to stderr.
    assert "PEX estimate error" in captured.err
    assert "typical" in captured.out
    assert "median" in captured.out
