import pytest

import os.path

from siliconcompiler import Project


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_gcd():
    from gcd import gcd
    gcd.main()

    manifest = 'build/gcd/job0/gcd.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history("job0")

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds.gz')
    # Verify that final manifest was recorded.
    assert os.path.isfile('build/gcd/job0/gcd.pkg.json')

    assert project.get('tool', 'yosys', 'task', 'syn_asic', 'report', 'cellarea',
                       step='synthesis', index='0') == ['reports/stat.json']

    # Warning counts are pinned for every node in the flow so that a tool update
    # which introduces (or silences) a warning fails here instead of slipping by
    # unnoticed. Each note below records the warnings that make up the count; the
    # raw text lives in <build>/<node>/<index>/<node>.warnings.

    # 6x [-Wsign-compare] comparison of differently signed types ('reg[1:0]' vs
    #    'logic signed[31:0]') at gcd.v:188, 195, 202, 266, 274 and 284
    # 1x [-Wsign-conversion] implicit conversion changes signedness at gcd.v:279
    assert project.get('metric', 'warnings', step='elaborate', index='0') == 7

    # 2x Latch inferred for signal (GcdUnitCtrlRTL do_sub and do_swap)
    # 1x ABC: Detected 2 multi-output cells (for example, "FA_X1")
    # 1x ABC: The network is combinational (run "fraig" or "fraig_sweep")
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 4

    # 1x [STA-0441] gcd.sdc:3 set_input_delay relative to a clock defined on the
    #    same port/pin not allowed
    assert project.get('metric', 'warnings', step='synthesis.timing', index='0') == 1

    # 1x [STA-0441] same set_input_delay constraint, reported again when OpenROAD
    #    reads the SDC
    assert project.get('metric', 'warnings', step='cleanup.clean', index='0') == 1

    # 1x [IFP-0028] Core area lower left (1.000, 1.000) snapped to (1.140, 1.400)
    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    # Skipped ("no macros to place."), so no metrics are recorded for this node.
    assert project.get('metric', 'warnings', step='floorplan.macro_placement',
                       index='0') is None

    assert project.get('metric', 'warnings', step='floorplan.tapcell', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.power_grid', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.pin_placement', index='0') == 0

    assert project.get('metric', 'warnings', step='place.global', index='0') == 0
    assert project.get('metric', 'warnings', step='place.repair_design', index='0') == 0
    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    # 1x [CTS-0132] -balance_levels is obsolete
    # 1x [CTS-0128] -obstruction_aware is obsolete
    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    assert project.get('metric', 'warnings', step='cts.repair_timing', index='0') == 0
    assert project.get('metric', 'warnings', step='cts.fillcell', index='0') == 0

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0
    assert project.get('metric', 'warnings', step='route.antenna_repair', index='0') == 0

    # 1x [EST-0026] Missing route to pin req_rdy$_DFF_P_/Q in net req_rdy
    assert project.get('metric', 'warnings', step='route.detailed', index='0') == 1

    # Skipped ("no metal fill rules are available" from freepdk45), so no metrics
    # are recorded for this node.
    assert project.get('metric', 'warnings', step='dfm.metal_fill', index='0') is None

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_py_gcd_skywater():
    from gcd import gcd_skywater

    gcd_skywater.main()

    assert os.path.isfile('build/gcd/rtl2gds/write.gds/0/outputs/gcd.gds.gz')
    assert os.path.isfile('build/gcd/signoff/gcd.pkg.json')

    project = Project.from_manifest('build/gcd/rtl2gds/gcd.pkg.json').history("rtl2gds")

    # Warning counts for the RTL-to-GDS job, pinned per node. See test_py_gcd()
    # for the same breakdown on freepdk45; the counts differ here because sky130
    # ships different cells and LEF rules.

    # 6x [-Wsign-compare] comparison of differently signed types ('reg[1:0]' vs
    #    'logic signed[31:0]') at gcd.v:188, 195, 202, 266, 274 and 284
    # 1x [-Wsign-conversion] implicit conversion changes signedness at gcd.v:279
    assert project.get('metric', 'warnings', step='elaborate', index='0') == 7

    # 2x Latch inferred for signal (GcdUnitCtrlRTL do_sub and do_swap)
    # 1x ABC: Detected 9 multi-output cells (for example, "sky130_fd_sc_hd__fa_1")
    # 1x ABC: The network is combinational (run "fraig" or "fraig_sweep")
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 4

    # 1x [STA-0441] gcd.sdc:3 set_input_delay relative to a clock defined on the
    #    same port/pin not allowed
    assert project.get('metric', 'warnings', step='synthesis.timing', index='0') == 1

    # 1x [STA-0441] same set_input_delay constraint, reported again when OpenROAD
    #    reads the SDC
    assert project.get('metric', 'warnings', step='cleanup.clean', index='0') == 1

    # 1x [IFP-0028] Core area lower left (1.000, 1.000) snapped to (1.380, 2.720)
    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    # Skipped ("no macros to place."), so no metrics are recorded for this node.
    assert project.get('metric', 'warnings', step='floorplan.macro_placement',
                       index='0') is None

    assert project.get('metric', 'warnings', step='floorplan.tapcell', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.power_grid', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.pin_placement', index='0') == 0

    assert project.get('metric', 'warnings', step='place.global', index='0') == 0
    assert project.get('metric', 'warnings', step='place.repair_design', index='0') == 0
    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    # 1x [CTS-0132] -balance_levels is obsolete
    # 1x [CTS-0128] -obstruction_aware is obsolete
    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    # 1x [RSZ-0062] Unable to repair all setup violations
    assert project.get('metric', 'warnings', step='cts.repair_timing', index='0') == 1

    assert project.get('metric', 'warnings', step='cts.fillcell', index='0') == 0

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0
    assert project.get('metric', 'warnings', step='route.antenna_repair', index='0') == 0

    # 10x [DRT-0349] LEF58_ENCLOSURE with no CUTCLASS is not supported, reported
    #     twice each for the mcon, via, via2, via3 and via4 cut layers
    assert project.get('metric', 'warnings', step='route.detailed', index='0') == 10

    # Skipped ("no metal fill rules are available" from sky130), so no metrics
    # are recorded for this node.
    assert project.get('metric', 'warnings', step='dfm.metal_fill', index='0') is None

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0

    signoff = Project.from_manifest('build/gcd/signoff/gcd.pkg.json').history("signoff")

    # Verify that the build was LVS and DRC clean.
    assert signoff.get('metric', 'drcs', step='drc', index='0') == 0
    assert signoff.get('metric', 'drcs', step='lvs', index='0') == 0

    # Warning counts for the signoff job.

    # 1x CIF file read warning: CIF style sky130(vendor): units rescaled by a
    #    factor of 5 / 1, emitted by magic when it reads the GDS
    assert signoff.get('metric', 'warnings', step='drc', index='0') == 1

    # 1x the same magic CIF rescale warning, this run extracts the SPICE netlist
    assert signoff.get('metric', 'warnings', step='extspice', index='0') == 1

    # 2x netgen command 'format'/'global' use fully-qualified name
    #    '::netgen::format' / '::netgen::global'
    # 1x A case-insensitive file has been read and so the verilog file must be
    #    treated case-insensitive to match
    # These are all netgen start-up noise; the LVS itself reports no top-level
    # pin mismatches, which is what the drcs metric above covers.
    assert signoff.get('metric', 'warnings', step='lvs', index='0') == 3

    # 'signoff' is a builtin join task, so it records no metrics of its own.
    assert signoff.get('metric', 'warnings', step='signoff', index='0') is None


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_py_gcd_gf180():
    from gcd import gcd_gf180
    gcd_gf180.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds.gz')

    project = Project.from_manifest('build/gcd/job0/gcd.pkg.json').history("job0")

    # Warning counts pinned per node. See test_py_gcd() for the same breakdown on
    # freepdk45; the counts differ here because gf180 ships different cells and
    # LEF rules.

    # 6x [-Wsign-compare] comparison of differently signed types ('reg[1:0]' vs
    #    'logic signed[31:0]') at gcd.v:188, 195, 202, 266, 274 and 284
    # 1x [-Wsign-conversion] implicit conversion changes signedness at gcd.v:279
    assert project.get('metric', 'warnings', step='elaborate', index='0') == 7

    # 2x Latch inferred for signal (GcdUnitCtrlRTL do_sub and do_swap)
    # 1x ABC: Detected 4 multi-output cells
    #    (for example, "gf180mcu_fd_sc_mcu9t5v0__addf_2")
    # 1x ABC: The network is combinational (run "fraig" or "fraig_sweep")
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 4

    # 1x [STA-0441] gcd.sdc:3 set_input_delay relative to a clock defined on the
    #    same port/pin not allowed
    assert project.get('metric', 'warnings', step='synthesis.timing', index='0') == 1

    # 1x [STA-0441] same set_input_delay constraint, reported again when OpenROAD
    #    reads the SDC
    assert project.get('metric', 'warnings', step='cleanup.clean', index='0') == 1

    # 1x [IFP-0028] Core area lower left (1.000, 1.000) snapped to (1.120, 5.040)
    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    # Skipped ("no macros to place."), so no metrics are recorded for this node.
    assert project.get('metric', 'warnings', step='floorplan.macro_placement',
                       index='0') is None

    assert project.get('metric', 'warnings', step='floorplan.tapcell', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.power_grid', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.pin_placement', index='0') == 0

    assert project.get('metric', 'warnings', step='place.global', index='0') == 0
    assert project.get('metric', 'warnings', step='place.repair_design', index='0') == 0
    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    # 1x [CTS-0132] -balance_levels is obsolete
    # 1x [CTS-0128] -obstruction_aware is obsolete
    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    # 1x [RSZ-0062] Unable to repair all setup violations
    # 1x [RSZ-0066] Unable to repair all hold violations
    assert project.get('metric', 'warnings', step='cts.repair_timing', index='0') == 2

    assert project.get('metric', 'warnings', step='cts.fillcell', index='0') == 0

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0
    assert project.get('metric', 'warnings', step='route.antenna_repair', index='0') == 0

    # 8x [DRT-0349] LEF58_ENCLOSURE with no CUTCLASS is not supported, reported
    #    twice each for the Via1, Via2, Via3 and Via4 cut layers
    # 9x [EST-0026] Missing route to pin, reported three times each for
    #    _361_/B1, an a_lt_b input flop output and _274_/A2
    assert project.get('metric', 'warnings', step='route.detailed', index='0') == 17

    # Skipped ("no metal fill rules are available" from gf180), so no metrics are
    # recorded for this node.
    assert project.get('metric', 'warnings', step='dfm.metal_fill', index='0') is None

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_py_gcd_ihp130():
    from gcd import gcd_ihp130
    gcd_ihp130.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds.gz')
    assert os.path.isfile('build/gcd/drc/drc/0/outputs/gcd.lyrdb')

    proj = Project.from_manifest('build/gcd/drc/gcd.pkg.json')
    assert proj.get("metric", "drcs", step="drc", index="0") == 0
    # The KLayout DRC run is clean, so it emits no warnings either.
    assert proj.get("metric", "warnings", step="drc", index="0") == 0

    project = Project.from_manifest('build/gcd/job0/gcd.pkg.json').history("job0")

    # Warning counts for the RTL-to-GDS job, pinned per node. See test_py_gcd()
    # for the same breakdown on freepdk45; the counts differ here because ihp130
    # ships different cells and LEF rules.

    # 6x [-Wsign-compare] comparison of differently signed types ('reg[1:0]' vs
    #    'logic signed[31:0]') at gcd.v:188, 195, 202, 266, 274 and 284
    # 1x [-Wsign-conversion] implicit conversion changes signedness at gcd.v:279
    assert project.get('metric', 'warnings', step='elaborate', index='0') == 7

    # 2x Latch inferred for signal (GcdUnitCtrlRTL do_sub and do_swap)
    # 1x ABC: The network is combinational (run "fraig" or "fraig_sweep")
    # Unlike the other PDKs there is no multi-output cell warning here, because
    # ABC does not map any full adders for this library.
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 3

    # 1x [STA-0441] gcd.sdc:3 set_input_delay relative to a clock defined on the
    #    same port/pin not allowed
    assert project.get('metric', 'warnings', step='synthesis.timing', index='0') == 1

    # 1x [STA-0441] same set_input_delay constraint, reported again when OpenROAD
    #    reads the SDC
    assert project.get('metric', 'warnings', step='cleanup.clean', index='0') == 1

    # 1x [IFP-0028] Core area lower left (4.800, 4.800) snapped to (4.800, 7.560)
    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    # Skipped ("no macros to place."), so no metrics are recorded for this node.
    assert project.get('metric', 'warnings', step='floorplan.macro_placement',
                       index='0') is None

    assert project.get('metric', 'warnings', step='floorplan.tapcell', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.power_grid', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.pin_placement', index='0') == 0

    assert project.get('metric', 'warnings', step='place.global', index='0') == 0
    assert project.get('metric', 'warnings', step='place.repair_design', index='0') == 0
    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    # 1x [CTS-0132] -balance_levels is obsolete
    # 1x [CTS-0128] -obstruction_aware is obsolete
    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    # 1x [RSZ-0062] Unable to repair all setup violations
    assert project.get('metric', 'warnings', step='cts.repair_timing', index='0') == 1

    assert project.get('metric', 'warnings', step='cts.fillcell', index='0') == 0

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0
    assert project.get('metric', 'warnings', step='route.antenna_repair', index='0') == 0

    # 10x [DRT-0349] LEF58_ENCLOSURE with no CUTCLASS is not supported, for the
    #     Cont, Via1, Via2, Via3, Via4, TopVia1 and TopVia2 cut layers
    # 18x [EST-0026] Missing route to pin, reported three times each for six
    #     pins, one of which is a clock buffer output
    assert project.get('metric', 'warnings', step='route.detailed', index='0') == 28

    # Skipped ("no metal fill rules are available" from ihp130), so no metrics
    # are recorded for this node.
    assert project.get('metric', 'warnings', step='dfm.metal_fill', index='0') is None

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_py_gcd_hls():
    from gcd import gcd_hls
    gcd_hls.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds.gz')

    project = Project.from_manifest('build/gcd/job0/gcd.pkg.json').history("job0")

    # Warning counts pinned per node. This flow starts from gcd.c, so the design
    # is whatever Bambu generates rather than the hand-written gcd.v used by
    # test_py_gcd(), and the counts differ accordingly.

    # The Bambu convert task defines no warning regex, so it records no metrics.
    assert project.get('metric', 'warnings', step='convert', index='0') is None

    # 4x Replacing memory with list of registers, for genblk1.in1_sign,
    #    genblk1.xdenom_arr, genblk1.temp and genblk1.quot
    # 1x ABC: Detected 2 multi-output cells (for example, "FA_X1")
    # 1x ABC: The network is combinational (run "fraig" or "fraig_sweep")
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 6

    # 1x [STA-0441] gcd_hls.sdc:3 set_input_delay relative to a clock defined on
    #    the same port/pin not allowed
    assert project.get('metric', 'warnings', step='synthesis.timing', index='0') == 1

    # 1x [STA-0441] same set_input_delay constraint, reported again when OpenROAD
    #    reads the SDC
    assert project.get('metric', 'warnings', step='cleanup.clean', index='0') == 1

    # 1x [IFP-0028] Core area lower left (1.000, 1.000) snapped to (1.140, 1.400)
    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    # Skipped ("no macros to place."), so no metrics are recorded for this node.
    assert project.get('metric', 'warnings', step='floorplan.macro_placement',
                       index='0') is None

    assert project.get('metric', 'warnings', step='floorplan.tapcell', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.power_grid', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.pin_placement', index='0') == 0

    assert project.get('metric', 'warnings', step='place.global', index='0') == 0
    assert project.get('metric', 'warnings', step='place.repair_design', index='0') == 0
    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    # 1x [CTS-0132] -balance_levels is obsolete
    # 1x [CTS-0128] -obstruction_aware is obsolete
    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    assert project.get('metric', 'warnings', step='cts.repair_timing', index='0') == 0
    assert project.get('metric', 'warnings', step='cts.fillcell', index='0') == 0

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0
    assert project.get('metric', 'warnings', step='route.antenna_repair', index='0') == 0

    # 14x [EST-0026] Missing route to pin, one per pin, spread across the
    #     Datapath temp array, a clock leaf net and assorted logic cells
    assert project.get('metric', 'warnings', step='route.detailed', index='0') == 14

    # Skipped ("no metal fill rules are available" from freepdk45), so no metrics
    # are recorded for this node.
    assert project.get('metric', 'warnings', step='dfm.metal_fill', index='0') is None

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_py_gcd_chisel():
    from gcd import gcd_chisel
    gcd_chisel.main()

    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/GCD.gds.gz')

    project = Project.from_manifest('build/gcd/job0/gcd.pkg.json').history("job0")

    # Warning counts pinned per node. This flow starts from GCD.scala, so the
    # design is whatever the Chisel compiler emits rather than the hand-written
    # gcd.v used by test_py_gcd(), and the counts differ accordingly. It also
    # uses gcd_chisel.sdc rather than gcd.sdc, because Chisel names the clock
    # port of a Module 'clock' rather than 'clk'.

    # The Chisel convert task defines no warning regex, so it records no metrics.
    assert project.get('metric', 'warnings', step='convert', index='0') is None

    # 1x ABC: Detected 2 multi-output cells (for example, "FA_X1")
    # 1x ABC: The network is combinational (run "fraig" or "fraig_sweep")
    assert project.get('metric', 'warnings', step='synthesis', index='0') == 2

    # 1x [STA-0441] gcd_chisel.sdc:3 set_input_delay relative to a clock defined
    #    on the same port/pin not allowed
    assert project.get('metric', 'warnings', step='synthesis.timing', index='0') == 1

    # 1x [STA-0441] same set_input_delay constraint, reported again when OpenROAD
    #    reads the SDC
    assert project.get('metric', 'warnings', step='cleanup.clean', index='0') == 1

    # 1x [IFP-0028] Core area lower left (1.000, 1.000) snapped to (1.140, 1.400)
    assert project.get('metric', 'warnings', step='floorplan.init', index='0') == 1

    # Skipped ("no macros to place."), so no metrics are recorded for this node.
    assert project.get('metric', 'warnings', step='floorplan.macro_placement',
                       index='0') is None

    assert project.get('metric', 'warnings', step='floorplan.tapcell', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.power_grid', index='0') == 0
    assert project.get('metric', 'warnings', step='floorplan.pin_placement', index='0') == 0

    assert project.get('metric', 'warnings', step='place.global', index='0') == 0
    assert project.get('metric', 'warnings', step='place.repair_design', index='0') == 0
    assert project.get('metric', 'warnings', step='place.detailed', index='0') == 0

    # 1x [CTS-0132] -balance_levels is obsolete
    # 1x [CTS-0128] -obstruction_aware is obsolete
    assert project.get('metric', 'warnings', step='cts.clock_tree_synthesis', index='0') == 2

    assert project.get('metric', 'warnings', step='cts.repair_timing', index='0') == 0
    assert project.get('metric', 'warnings', step='cts.fillcell', index='0') == 0

    assert project.get('metric', 'warnings', step='route.global', index='0') == 0
    assert project.get('metric', 'warnings', step='route.antenna_repair', index='0') == 0

    # 2x [EST-0026] Missing route to pin, for _303_/Z and a y[7] flop output
    assert project.get('metric', 'warnings', step='route.detailed', index='0') == 2

    # Skipped ("no metal fill rules are available" from freepdk45), so no metrics
    # are recorded for this node.
    assert project.get('metric', 'warnings', step='dfm.metal_fill', index='0') is None

    assert project.get('metric', 'warnings', step='write.gds', index='0') == 0
    assert project.get('metric', 'warnings', step='write.views', index='0') == 0
