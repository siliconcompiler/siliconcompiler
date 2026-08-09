#!/usr/bin/env python3
# Copyright 2020-2026 Silicon Compiler Authors. All Rights Reserved.

"""Calibrate OpenROAD's pre-route parasitic estimate for FreePDK45.

This is a thin wrapper around the reusable utility app
:mod:`siliconcompiler.tools.openroad.utils.pex_calibrate`. It runs the two-phase
calibration on the bundled demo survey (gcd, picorv32, aes and jpeg) and prints
the ``add_openroad_rclayer`` / ``add_openroad_rccorrection`` lines to paste into
a PDK setup.

The same thing from the command line::

    python -m siliconcompiler.tools.openroad.utils.pex_calibrate freepdk45_demo

To calibrate your own PDK, point ``TARGET`` at your target and pass your own
designs (see the ``designs`` argument of ``calibrate``). For the full write-up
see the "Calibrating the parasitic estimate (PEX)" tutorial (``pex_calibration``)
in the documentation.

Requires: yosys, openroad; freepdk45 (via lambdapdk)
"""

from siliconcompiler.tools.openroad.utils import pex_calibrate


# Target to calibrate. A string ('freepdk45_demo') or the target function both
# work; the PDK name is derived from it automatically.
TARGET = "freepdk45_demo"


def main(designs=None, outdir="build/pex", rerun=False, score=False):
    """Run the two-phase calibration and print the paste-able PDK setup lines.

    Args:
        designs (list, optional): Survey designs. Defaults to the bundled demo
            survey (gcd, picorv32, aes, jpeg); pass a shorter list to trade
            accuracy for runtime.
        outdir (str, optional): Directory for the ``<pdk>.rclayer.csv`` /
            ``<pdk>.rccorr.csv`` data files.
        rerun (bool, optional): Recompute even when the data files exist.
        score (bool, optional): Also re-route the survey with the calibration
            applied and report the per-net error before vs after.

    Returns:
        tuple: ``(model, factors)`` - the initial per-layer estimate model and
        the per-layer correction factors.
    """
    # Phase 1 derives the initial per-layer model from the OpenRCX deck
    # (bench_wires, no design); phase 2 pools the real-routed per-layer
    # capacitance over the demo survey into correction factors. Results are
    # cached under ``outdir`` (here the gitignored build/ tree) - rerun with
    # rerun=True to recompute. The paste-able PDK lines are printed at the end.
    return pex_calibrate.calibrate(TARGET, designs=designs, outdir=outdir,
                                   rerun=rerun, score=score)


if __name__ == "__main__":
    main()
