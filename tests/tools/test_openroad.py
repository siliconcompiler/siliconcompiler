# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import re
import pytest

from siliconcompiler import Design
from siliconcompiler import Flowgraph
from siliconcompiler import TaskSkip

from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.flows.openroad_pex import (
    GenerateOpenRCXFlow,
    GeneratePEXEstimateFlow,
    PEXCalibrateFlow
)

from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.openroad import OpenROADPDK
from siliconcompiler.tools.openroad import OpenROADStdCellLibrary
from siliconcompiler.tools.openroad import _apr
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad import metrics
from siliconcompiler.tools.openroad import open as openroad_open
from siliconcompiler.tools.openroad import show as openroad_show
from siliconcompiler.utils.paths import workdir
from siliconcompiler.tools.openroad import write_data
from siliconcompiler.tools.openroad import antenna_repair
from siliconcompiler.tools.openroad import clock_tree_synthesis
from siliconcompiler.tools.openroad import detailed_placement
from siliconcompiler.tools.openroad import detailed_route
from siliconcompiler.tools.openroad import fillmetal_insertion
from siliconcompiler.tools.openroad import global_placement
from siliconcompiler.tools.openroad import global_route
from siliconcompiler.tools.openroad import init_floorplan
from siliconcompiler.tools.openroad import macro_placement
from siliconcompiler.tools.openroad import power_grid_analysis
from siliconcompiler.tools.openroad import power_grid
from siliconcompiler.tools.openroad import pex
from siliconcompiler.tools.openroad import rdlroute
from siliconcompiler.tools.openroad import repair_design
from siliconcompiler.tools.openroad import repair_timing
from siliconcompiler.tools.openroad import screenshot
from siliconcompiler.tools.openroad import synth_cleanup
from siliconcompiler.tools.openroad.utils import rcx_merge
from siliconcompiler.tools.openroad.utils.rcx_merge import (
    merge_openrcx_rules,
    RCXMergeError,
)
from siliconcompiler.tools.openroad.utils import pex_calibrate as pc


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(asic_gcd):
    flow = Flowgraph("testflow")
    flow.node("version", init_floorplan.InitFloorplanTask())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_openroad_images(asic_gcd):
    for task in APRTask.find_task(asic_gcd):
        task.set('var', 'ord_enable_images', True)

    assert asic_gcd.run()

    images_count = {
        'floorplan.init': 2,
        'place.detailed': 7,
        'cts.clock_tree_synthesis': 11,
        'route.detailed': 13,
        'write.views': 29,
    }

    for step in images_count.keys():
        count = 0
        all_files = set()
        for dirpath, _, files in os.walk(
                os.path.join(workdir(asic_gcd, step=step, index='0'),
                             'reports',
                             'images')):
            count += len(files)
            all_files.update([os.path.relpath(
                os.path.join(dirpath, f),
                workdir(asic_gcd, step=step, index='0')) for f in files])

        assert images_count[step] == count, f'{step} images do not match: ' \
                                            f'{images_count[step]} == {count}: {all_files}'


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_metrics_task(asic_gcd):
    flow = ASICFlow("testflow")
    flow.node("metrics", metrics.MetricsTask())
    flow.edge('floorplan.init', 'metrics')

    asic_gcd.set_flow(flow)
    asic_gcd.set('option', 'to', 'metrics')
    assert asic_gcd.run()

    assert asic_gcd.history("job0").get('metric', 'cellarea', step='metrics', index='0') is not \
        None
    assert asic_gcd.history("job0").get('metric', 'totalarea', step='metrics', index='0') is not \
        None


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_pin_placement(asic_heartbeat):
    clk = asic_heartbeat.constraint.pin.make_pinconstraint("clk")
    clk.set_layer("metal4")
    clk.set_order(1)
    clk.set_side("top")
    nreset = asic_heartbeat.constraint.pin.make_pinconstraint("nreset")
    nreset.set_layer("metal4")
    nreset.set_order(2)
    nreset.set_side("top")
    out = asic_heartbeat.constraint.pin.make_pinconstraint("out")
    out.set_layer("metal2")
    out.set_order(1)
    out.set_side("bottom")

    asic_heartbeat.option.add_to("floorplan.init")

    job = asic_heartbeat.run()
    assert job
    report = job.find_result(step='floorplan.init', directory=".", filename="floorplan.init.log")
    with open(report, 'r') as f:
        log = f.read()
    assert log.count("Pin clk placed at") == 1
    assert log.count("Pin nreset placed at") == 1
    assert log.count("Pin out placed at") == 1


_CAP_UNIT_SCALE = {"": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18}


def _read_layer_rc_caps(path):
    """Parse per-layer capacitance out of OpenROAD's report_layer_rc tables.

    Returns ``{layer: cap_F_per_um}``. The report prints in the design's
    capacitance unit, which is PDK-dependent (fF/um on freepdk45, pF/um on
    gf180), so the unit prefix is read from the header rather than assumed. The
    file holds one routing table per scene plus an unscened default; the
    capacitance for a layer must be identical in all of them, which is asserted
    here rather than silently collapsed. The via table has no capacitance column
    and so never matches the row pattern.
    """
    # Unit row, e.g. "  |  (kohm/um) |  (fF/um)" - only the capacitance column
    # ends in "F/um", so the resistance column cannot be mistaken for it.
    header = re.compile(r'\((\w?)F/um\)')
    row = re.compile(r'^\s*(\w+)\s*\|\s*[\d.eE+-]+\s*\|\s*([\d.eE+-]+)\s*$')
    scale = None
    caps = {}
    with open(path) as fid:
        for line in fid:
            unit = header.search(line)
            if unit:
                scale = _CAP_UNIT_SCALE[unit.group(1).lower()]
                continue
            match = row.match(line)
            if not match or match.group(1) == "Layer":
                continue
            assert scale is not None, f"no capacitance unit header seen before {line!r}"
            layer, cap = match.group(1), float(match.group(2)) * scale
            # Same layer in a later (per-scene) table must report the same value.
            assert caps.setdefault(layer, cap) == cap, \
                f"{layer} capacitance differs between report_layer_rc tables"
    assert caps, f"parsed no routing capacitances from {path}"
    return caps


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_rccorrection_scales_set_layer_rc(asic_heartbeat):
    """The PDK's rccorrection must actually reach set_layer_rc.

    This is the payoff of the whole PEX calibration path (pdk rccorrection ->
    sc_get_corrmap -> sc_setup_pex -> set_layer_rc); everything else only checks
    that the factors are *derived* correctly. Runs one APR node and reads back
    OpenROAD's own report_layer_rc output, which the APR preamble always writes.
    """
    pdk = asic_heartbeat.get_library(str(asic_heartbeat.get("asic", "pdk")))
    model = {layer: cap for corner, layertype, layer, _, cap
             in pdk.get("tool", "openroad", "rclayer")
             if corner == "typical" and layertype == "routing"}
    assert model["metal1"] and model["metal2"], "fixture PDK must model metal1/metal2"

    # Correct metal2 only: metal1 is the control that must come through untouched.
    pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.5)

    asic_heartbeat.option.add_to("floorplan.init")
    job = asic_heartbeat.run()
    assert job

    report = job.find_result(step="floorplan.init", index="0",
                             directory="reports/setup", filename="layer_rc.rpt")
    assert report, "APR preamble did not write reports/setup/layer_rc.rpt"
    caps = _read_layer_rc_caps(report)

    # abs=0 so the (femtofarad-scale) comparison is governed by rel, not by
    # pytest.approx's 1e-12 default absolute tolerance, which would make any
    # assertion on these magnitudes pass vacuously. The report carries 3
    # significant figures, hence rel=0.01.
    assert caps["metal2"] == pytest.approx(0.5 * model["metal2"], rel=0.01, abs=0)
    assert caps["metal1"] == pytest.approx(model["metal1"], rel=0.01, abs=0)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_apply_pex_correction_false_bypasses_rccorrection(asic_heartbeat):
    """apply_pex_correction=False must fall back to the raw rclayer values."""
    pdk = asic_heartbeat.get_library(str(asic_heartbeat.get("asic", "pdk")))
    model = {layer: cap for corner, layertype, layer, _, cap
             in pdk.get("tool", "openroad", "rclayer")
             if corner == "typical" and layertype == "routing"}
    pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.5)

    for task in APRTask.find_task(asic_heartbeat):
        task.set_openroad_applypexcorrection(False)

    asic_heartbeat.option.add_to("floorplan.init")
    job = asic_heartbeat.run()
    assert job

    report = job.find_result(step="floorplan.init", index="0",
                             directory="reports/setup", filename="layer_rc.rpt")
    caps = _read_layer_rc_caps(report)
    # The 0.5 factor is present in the PDK but must not be applied.
    assert caps["metal2"] == pytest.approx(model["metal2"], rel=0.01, abs=0)


def test_openroad_pdk_add_rclayer_routing():
    pdk = OpenROADPDK()
    pdk.add_openroad_rclayer('typical', 'routing', 'm1', 0.1, 0.2)
    assert pdk.get('tool', 'openroad', 'rclayer') == [('typical', 'routing', 'm1', 0.1, 0.2)]


def test_openroad_pdk_add_rclayer_via_ignores_capacitance():
    pdk = OpenROADPDK()
    pdk.add_openroad_rclayer('typical', 'via', 'v1', 0.3, 0.4)
    assert pdk.get('tool', 'openroad', 'rclayer') == [('typical', 'via', 'v1', 0.3, None)]


def test_openroad_pdk_add_rclayer_default_capacitance():
    pdk = OpenROADPDK()
    pdk.add_openroad_rclayer('typical', 'routing', 'm1', 0.1)
    assert pdk.get('tool', 'openroad', 'rclayer') == [('typical', 'routing', 'm1', 0.1, None)]


def test_openroad_pdk_add_rclayer_accumulates():
    pdk = OpenROADPDK()
    pdk.add_openroad_rclayer('typical', 'routing', 'm1', 0.1, 0.2)
    pdk.add_openroad_rclayer('typical', 'via', 'v1', 0.3, 0.4)
    assert sorted(pdk.get('tool', 'openroad', 'rclayer')) == [
        ('typical', 'routing', 'm1', 0.1, 0.2),
        ('typical', 'via', 'v1', 0.3, None),
    ]


def test_openroad_pdk_add_rclayer_clobber():
    pdk = OpenROADPDK()
    pdk.add_openroad_rclayer('typical', 'routing', 'm1', 0.1, 0.2)
    pdk.add_openroad_rclayer('typical', 'routing', 'm2', 0.5, clobber=True)
    assert pdk.get('tool', 'openroad', 'rclayer') == [('typical', 'routing', 'm2', 0.5, None)]


def test_openroad_pdk_add_rclayer_invalid_layertype():
    pdk = OpenROADPDK()
    with pytest.raises(ValueError):
        pdk.add_openroad_rclayer('typical', 'bad', 'm1', 0.1, 0.2)


def test_openroad_pdk_unset_rclayer():
    pdk = OpenROADPDK()
    pdk.add_openroad_rclayer('typical', 'routing', 'm1', 0.1, 0.2)
    pdk.unset_openroad_rclayer()
    assert pdk.get('tool', 'openroad', 'rclayer') == []


def test_openroad_pdk_add_rccorrection_cap_only_records_none():
    # Common case: only cap_factor prescribed. res_factor must be recorded as
    # None (the caller's value, not coerced to 1.0), keeping all four fields.
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection('typical', 'metal2', cap_factor=0.696)
    assert pdk.get('tool', 'openroad', 'rccorrection') == \
        [('typical', 'metal2', None, 0.696)]


def test_openroad_pdk_add_rccorrection_res_only_records_none():
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection('typical', 'metal3', res_factor=1.1)
    assert pdk.get('tool', 'openroad', 'rccorrection') == \
        [('typical', 'metal3', 1.1, None)]


def test_openroad_pdk_add_rccorrection_accumulates():
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection('typical', 'metal2', cap_factor=0.7)
    pdk.add_openroad_rccorrection('typical', 'metal4', res_factor=1.0, cap_factor=0.5)
    assert sorted(pdk.get('tool', 'openroad', 'rccorrection')) == [
        ('typical', 'metal2', None, 0.7),
        ('typical', 'metal4', 1.0, 0.5),
    ]


def test_openroad_pdk_add_rccorrection_clobber():
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection('typical', 'metal2', cap_factor=0.7)
    pdk.add_openroad_rccorrection('typical', 'metal3', cap_factor=0.6, clobber=True)
    assert pdk.get('tool', 'openroad', 'rccorrection') == \
        [('typical', 'metal3', None, 0.6)]


def test_openroad_pdk_rccorrection_tcl_preserves_none_position():
    # An interior None (res omitted) must hold its slot in the Tcl list, or the
    # runtime reads cap_factor as res_factor. gettcl emits {} for the
    # unprescribed field so the tuple stays four elements wide.
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection('typical', 'metal2', cap_factor=0.696)
    param = pdk.get('tool', 'openroad', 'rccorrection', field=None)
    assert param.gettcl() == '[list [list "typical" "metal2" {} 0.696]]'


def test_openroad_pdk_unset_rccorrection():
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection('typical', 'metal2', cap_factor=0.7)
    pdk.unset_openroad_rccorrection()
    assert pdk.get('tool', 'openroad', 'rccorrection') == []


def test_openroad_pdk_add_rccorrection_rejects_negative():
    # A negative multiplier is never meaningful and would silently invert the
    # estimate; the schema range rejects it at the setter.
    pdk = OpenROADPDK()
    with pytest.raises(ValueError,
                       match=r"^error while adding to \[tool,openroad,rccorrection\]: "
                             r"-0\.5 is not in range: 0\.0\.\.$"):
        pdk.add_openroad_rccorrection('typical', 'metal2', cap_factor=-0.5)
    with pytest.raises(ValueError,
                       match=r"^error while adding to \[tool,openroad,rccorrection\]: "
                             r"-1\.0 is not in range: 0\.0\.\.$"):
        pdk.add_openroad_rccorrection('typical', 'metal2', res_factor=-1.0)
    assert pdk.get('tool', 'openroad', 'rccorrection') == []


class _FakeCorrLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        self.warnings.append(msg)


class _FakeCorrPDK:
    def __init__(self, rclayer):
        self._rclayer = rclayer

    def get(self, *keys):
        assert keys == ("tool", "openroad", "rclayer")
        return self._rclayer


class _FakeCorrTask:
    def __init__(self, logger, pdk, pex_corners):
        self.logger = logger
        self.pdk = pdk
        self._corners = pex_corners

    def get(self, *keys):
        assert keys == ("var", "pex_corners")
        return self._corners


def _run_corr_warn(rclayer, pex_corners):
    logger = _FakeCorrLogger()
    task = _FakeCorrTask(logger, _FakeCorrPDK(rclayer), pex_corners)
    pex.CalibratePEXTask._warn_uncovered_pex_corners(task)
    return logger.warnings


_TWO_CORNER_RCLAYER = [
    ("typical", "routing", "metal2", 3.5, 1.2e-16),
    ("slow", "routing", "metal2", 4.0, 1.3e-16),
]


def test_warn_uncovered_pex_corner_partial():
    # 'slow' has an estimate model but this survey only calibrates 'typical'.
    warnings = _run_corr_warn(_TWO_CORNER_RCLAYER, ["typical"])
    assert len(warnings) == 1
    assert "slow" in warnings[0]


def test_warn_uncovered_pex_corner_full_coverage():
    # Every modeled corner is covered by the survey -> silent.
    warnings = _run_corr_warn(_TWO_CORNER_RCLAYER, ["typical", "slow"])
    assert warnings == []


def test_warn_uncovered_pex_corner_single():
    # Only one modeled corner, and it is covered -> silent.
    warnings = _run_corr_warn(
        [("typical", "routing", "metal2", 3.5, 1.2e-16)], ["typical"])
    assert warnings == []


def test_openroad_pdk_set_rclayers():
    pdk = OpenROADPDK()
    pdk.set_openroad_rclayers(signal='m3', clock='m5')
    assert pdk.get('tool', 'openroad', 'rclayer_signal') == 'm3'
    assert pdk.get('tool', 'openroad', 'rclayer_clock') == 'm5'


def test_openroad_pdk_set_rclayers_signal_only():
    pdk = OpenROADPDK()
    pdk.set_openroad_rclayers(signal='m3')
    assert pdk.get('tool', 'openroad', 'rclayer_signal') == 'm3'
    assert pdk.get('tool', 'openroad', 'rclayer_clock') is None


def test_openroad_pdk_set_rclayers_clock_only():
    pdk = OpenROADPDK()
    pdk.set_openroad_rclayers(clock='m5')
    assert pdk.get('tool', 'openroad', 'rclayer_signal') is None
    assert pdk.get('tool', 'openroad', 'rclayer_clock') == 'm5'


def test_openroad_pdk_set_globalroutingderating():
    pdk = OpenROADPDK()
    pdk.set_openroad_globalroutingderating('m1', 0.5)
    pdk.set_openroad_globalroutingderating('m2', 0.6)
    assert sorted(pdk.get('tool', 'openroad', 'globalroutingderating')) == \
        [('m1', 0.5), ('m2', 0.6)]


def test_openroad_pdk_set_globalroutingderating_clobber():
    pdk = OpenROADPDK()
    pdk.set_openroad_globalroutingderating('m1', 0.5)
    pdk.set_openroad_globalroutingderating('m9', 0.9, clobber=True)
    assert pdk.get('tool', 'openroad', 'globalroutingderating') == [('m9', 0.9)]


def test_openroad_pdk_unset_globalroutingderating():
    pdk = OpenROADPDK()
    pdk.set_openroad_globalroutingderating('m1', 0.5)
    pdk.unset_openroad_globalroutingderating()
    assert pdk.get('tool', 'openroad', 'globalroutingderating') == []


def test_openroad_pdk_add_pinlayers():
    pdk = OpenROADPDK()
    pdk.add_openroad_pinlayers(horizontal='m1', vertical=['m2', 'm3'])
    assert pdk.get('tool', 'openroad', 'pin_layer_horizontal') == ['m1']
    assert pdk.get('tool', 'openroad', 'pin_layer_vertical') == ['m2', 'm3']


def test_openroad_pdk_add_pinlayers_accumulates():
    pdk = OpenROADPDK()
    pdk.add_openroad_pinlayers(horizontal='m1')
    pdk.add_openroad_pinlayers(horizontal='m2')
    assert pdk.get('tool', 'openroad', 'pin_layer_horizontal') == ['m1', 'm2']


def test_openroad_pdk_add_pinlayers_clobber():
    pdk = OpenROADPDK()
    pdk.add_openroad_pinlayers(horizontal='m1', vertical='m2')
    pdk.add_openroad_pinlayers(horizontal='m5', vertical='m6', clobber=True)
    assert pdk.get('tool', 'openroad', 'pin_layer_horizontal') == ['m5']
    assert pdk.get('tool', 'openroad', 'pin_layer_vertical') == ['m6']


def test_openroad_pdk_set_rcxmaxlayer():
    pdk = OpenROADPDK()
    pdk.set_openroad_rcxmaxlayer('m8')
    assert pdk.get('tool', 'openroad', 'rcx_maxlayer') == 'm8'


def test_openroad_pdk_set_processnode():
    pdk = OpenROADPDK()
    pdk.set_openroad_processnode('n7')
    assert pdk.get('tool', 'openroad', 'drt_process_node') == 'n7'


def test_openroad_pdk_set_detailedroutedisableviagen():
    pdk = OpenROADPDK()
    pdk.set_openroad_detailedroutedisableviagen(True)
    assert pdk.get('tool', 'openroad', 'drt_disable_via_gen') is True


def test_openroad_pdk_set_detailedrouteviarepair():
    pdk = OpenROADPDK()
    pdk.set_openroad_detailedrouteviarepair('v1')
    assert pdk.get('tool', 'openroad', 'drt_repair_pdn_vias') == 'v1'


def test_openroad_pdk_set_detailedrouteviainpinlayers():
    pdk = OpenROADPDK()
    pdk.set_openroad_detailedrouteviainpinlayers('m1', 'm2')
    assert pdk.get('tool', 'openroad', 'drt_via_in_pin_layers') == ('m1', 'm2')


def test_openroad_stdcell_set_tiehigh_cell():
    lib = OpenROADStdCellLibrary()
    lib.set_openroad_tiehigh_cell('TIEHI', 'Y')
    assert lib.get('tool', 'openroad', 'tiehigh_cell') == ('TIEHI', 'Y')


def test_openroad_stdcell_set_tielow_cell():
    lib = OpenROADStdCellLibrary()
    lib.set_openroad_tielow_cell('TIELO', 'Y')
    assert lib.get('tool', 'openroad', 'tielow_cell') == ('TIELO', 'Y')


def test_openroad_stdcell_set_placement_density():
    lib = OpenROADStdCellLibrary()
    lib.set_openroad_placement_density(0.7)
    assert lib.get('tool', 'openroad', 'place_density') == 0.7


def test_openroad_stdcell_cell_padding_default():
    lib = OpenROADStdCellLibrary()
    assert lib.get('tool', 'openroad', 'global_cell_padding') == 0
    assert lib.get('tool', 'openroad', 'detailed_cell_padding') == 0


def test_openroad_stdcell_set_cell_padding():
    lib = OpenROADStdCellLibrary()
    lib.set_openroad_cell_padding(2, 1)
    assert lib.get('tool', 'openroad', 'global_cell_padding') == 2
    assert lib.get('tool', 'openroad', 'detailed_cell_padding') == 1


def test_openroad_stdcell_set_macro_placement_halo():
    lib = OpenROADStdCellLibrary()
    lib.set_openroad_macro_placement_halo(1.5, 2.5)
    assert lib.get('tool', 'openroad', 'macro_placement_halo') == (1.5, 2.5)


def test_openroad_stdcell_set_tracks_file(tmp_path):
    tracks = tmp_path / "tracks.tcl"
    tracks.write_text("track info")
    lib = OpenROADStdCellLibrary()
    lib.set_name('mylib')
    lib.set_dataroot('root', str(tmp_path))
    with lib.active_dataroot('root'):
        lib.set_openroad_tracks_file('tracks.tcl')
    assert lib.get('tool', 'openroad', 'tracks') == 'tracks.tcl'
    assert lib.find_files('tool', 'openroad', 'tracks') == str(tracks)


def test_openroad_stdcell_set_tracks_file_explicit_dataroot(tmp_path):
    tracks = tmp_path / "tracks.tcl"
    tracks.write_text("track info")
    lib = OpenROADStdCellLibrary()
    lib.set_name('mylib')
    lib.set_dataroot('root', str(tmp_path))
    lib.set_openroad_tracks_file('tracks.tcl', dataroot='root')
    assert lib.get('tool', 'openroad', 'tracks') == 'tracks.tcl'
    assert lib.find_files('tool', 'openroad', 'tracks') == str(tracks)


def test_openroad_stdcell_set_tapcells_file(tmp_path):
    tap = tmp_path / "tap.lef"
    tap.write_text("tap info")
    lib = OpenROADStdCellLibrary()
    lib.set_name('mylib')
    lib.set_dataroot('root', str(tmp_path))
    with lib.active_dataroot('root'):
        lib.set_openroad_tapcells_file('tap.lef')
    assert lib.get('tool', 'openroad', 'tapcells') == 'tap.lef'
    assert lib.find_files('tool', 'openroad', 'tapcells') == str(tap)


def _make_lib_with_fileset(tmp_path, fileset='rtl'):
    src = tmp_path / "gc.tcl"
    src.write_text("connect")
    lib = OpenROADStdCellLibrary()
    lib.set_name('mylib')
    lib.set_dataroot('root', str(tmp_path))
    with lib.active_dataroot('root'):
        with lib.active_fileset(fileset):
            lib.add_file('gc.tcl', filetype='tcl')
    return lib


def test_openroad_stdcell_add_globalconnectfileset(tmp_path):
    lib = _make_lib_with_fileset(tmp_path)
    lib.add_openroad_globalconnectfileset('rtl')
    assert lib.get('tool', 'openroad', 'global_connect_fileset') == ['rtl']


def test_openroad_stdcell_add_globalconnectfileset_clobber(tmp_path):
    lib = _make_lib_with_fileset(tmp_path)
    lib.add_openroad_globalconnectfileset('rtl')
    lib.add_openroad_globalconnectfileset('rtl', clobber=True)
    assert lib.get('tool', 'openroad', 'global_connect_fileset') == ['rtl']


def test_openroad_stdcell_add_globalconnectfileset_missing(tmp_path):
    lib = _make_lib_with_fileset(tmp_path)
    with pytest.raises(LookupError):
        lib.add_openroad_globalconnectfileset('missing')


def test_openroad_stdcell_add_powergridfileset(tmp_path):
    lib = _make_lib_with_fileset(tmp_path)
    lib.add_openroad_powergridfileset('rtl')
    assert lib.get('tool', 'openroad', 'power_grid_fileset') == ['rtl']


def test_openroad_stdcell_add_powergridfileset_clobber(tmp_path):
    lib = _make_lib_with_fileset(tmp_path)
    lib.add_openroad_powergridfileset('rtl')
    lib.add_openroad_powergridfileset('rtl', clobber=True)
    assert lib.get('tool', 'openroad', 'power_grid_fileset') == ['rtl']


def test_openroad_stdcell_add_powergridfileset_missing(tmp_path):
    lib = _make_lib_with_fileset(tmp_path)
    with pytest.raises(LookupError):
        lib.add_openroad_powergridfileset('missing')


def test_openroad_stdcell_add_scan_chain_cells():
    lib = OpenROADStdCellLibrary()
    lib.add_openroad_scan_chain_cells('SC1')
    assert lib.get('tool', 'openroad', 'scan_chain_cells') == ['SC1']
    lib.add_openroad_scan_chain_cells(['SC2', 'SC3'])
    assert sorted(lib.get('tool', 'openroad', 'scan_chain_cells')) == ['SC1', 'SC2', 'SC3']
    lib.add_openroad_scan_chain_cells('SC9', clobber=True)
    assert lib.get('tool', 'openroad', 'scan_chain_cells') == ['SC9']


def test_openroad_stdcell_add_multibit_flipflops():
    lib = OpenROADStdCellLibrary()
    lib.add_openroad_multibit_flipflops('FF1')
    assert lib.get('tool', 'openroad', 'multibit_ff_cells') == ['FF1']
    lib.add_openroad_multibit_flipflops(['FF2', 'FF3'])
    assert sorted(lib.get('tool', 'openroad', 'multibit_ff_cells')) == ['FF1', 'FF2', 'FF3']
    lib.add_openroad_multibit_flipflops('FF9', clobber=True)
    assert lib.get('tool', 'openroad', 'multibit_ff_cells') == ['FF9']


def test_openroad_write_data_parameter_abstractlefbloatlayers():
    task = write_data.WriteViewsTask()
    task.set_openroad_abstractlefbloatlayers(False)
    assert task.get("var", "ord_abstract_lef_bloat_layers") is False
    task.set_openroad_abstractlefbloatlayers(True, step='write_data', index='1')
    assert task.get("var", "ord_abstract_lef_bloat_layers", step='write_data', index='1') is True
    assert task.get("var", "ord_abstract_lef_bloat_layers") is False


def test_openroad_write_data_parameter_abstractlefbloatfactor():
    task = write_data.WriteViewsTask()
    task.set_openroad_abstractlefbloatfactor(5)
    assert task.get("var", "ord_abstract_lef_bloat_factor") == 5
    task.set_openroad_abstractlefbloatfactor(20, step='write_data', index='1')
    assert task.get("var", "ord_abstract_lef_bloat_factor", step='write_data', index='1') == 20
    assert task.get("var", "ord_abstract_lef_bloat_factor") == 5


def test_openroad_write_data_parameter_writecdl():
    task = write_data.WriteViewsTask()
    task.set_openroad_writecdl(True)
    assert task.get("var", "write_cdl") is True
    task.set_openroad_writecdl(False, step='write_data', index='1')
    assert task.get("var", "write_cdl", step='write_data', index='1') is False
    assert task.get("var", "write_cdl") is True


def test_openroad_write_data_parameter_writespef():
    task = write_data.WriteViewsTask()
    task.set_openroad_writespef(False)
    assert task.get("var", "write_spef") is False
    task.set_openroad_writespef(True, step='write_data', index='1')
    assert task.get("var", "write_spef", step='write_data', index='1') is True
    assert task.get("var", "write_spef") is False


def test_openroad_write_data_parameter_writeliberty():
    task = write_data.WriteViewsTask()
    task.set_openroad_writeliberty(False)
    assert task.get("var", "write_liberty") is False
    task.set_openroad_writeliberty(True, step='write_data', index='1')
    assert task.get("var", "write_liberty", step='write_data', index='1') is True
    assert task.get("var", "write_liberty") is False


def test_openroad_write_data_parameter_writesdf():
    task = write_data.WriteViewsTask()
    task.set_openroad_writesdf(False)
    assert task.get("var", "write_sdf") is False
    task.set_openroad_writesdf(True, step='write_data', index='1')
    assert task.get("var", "write_sdf", step='write_data', index='1') is True
    assert task.get("var", "write_sdf") is False


def test_openroad_apr_parameter_opensta_early_timing_derate():
    task = _apr.OpenROADSTAParameter()
    task.set_openroad_earlytimingderate(0.5)
    assert task.get("var", "sta_early_timing_derate") == 0.5
    task.set_openroad_earlytimingderate(0.7, step='sta', index='1')
    assert task.get("var", "sta_early_timing_derate", step='sta', index='1') == 0.7
    assert task.get("var", "sta_early_timing_derate") == 0.5


def test_openroad_apr_parameter_opensta_late_timing_derate():
    task = _apr.OpenROADSTAParameter()
    task.set_openroad_latetimingderate(0.5)
    assert task.get("var", "sta_late_timing_derate") == 0.5
    task.set_openroad_latetimingderate(0.7, step='sta', index='1')
    assert task.get("var", "sta_late_timing_derate", step='sta', index='1') == 0.7
    assert task.get("var", "sta_late_timing_derate") == 0.5


def test_openroad_apr_parameter_opensta_top_n_paths():
    task = _apr.OpenROADSTAParameter()
    task.set_openroad_topnpaths(10)
    assert task.get("var", "sta_top_n_paths") == 10
    task.set_openroad_topnpaths(20, step='sta', index='1')
    assert task.get("var", "sta_top_n_paths", step='sta', index='1') == 20
    assert task.get("var", "sta_top_n_paths") == 10


def test_openroad_apr_parameter_opensta_define_path_groups():
    task = _apr.OpenROADSTAParameter()
    task.set_openroad_definepathgroups(True)
    assert task.get("var", "sta_define_path_groups") is True
    task.set_openroad_definepathgroups(False, step='sta', index='1')
    assert task.get("var", "sta_define_path_groups", step='sta', index='1') is False
    assert task.get("var", "sta_define_path_groups") is True


def test_openroad_apr_parameter_opensta_unique_path_groups_per_clock():
    task = _apr.OpenROADSTAParameter()
    task.set_openroad_uniquepathgroupsperclock(True)
    assert task.get("var", "sta_unique_path_groups_per_clock") is True
    task.set_openroad_uniquepathgroupsperclock(False, step='sta', index='1')
    assert task.get("var", "sta_unique_path_groups_per_clock", step='sta', index='1') is False
    assert task.get("var", "sta_unique_path_groups_per_clock") is True


def test_openroad_apr_parameter_psm_enable():
    task = _apr.OpenROADPSMParameter()
    task.set_openroad_psmenable(True)
    assert task.get("var", "psm_enable") is True
    task.set_openroad_psmenable(False, step='sta', index='1')
    assert task.get("var", "psm_enable", step='sta', index='1') is False
    assert task.get("var", "psm_enable") is True


def test_openroad_apr_parameter_psm_skip_nets():
    task = _apr.OpenROADPSMParameter()
    task.add_openroad_psmskipnets('net1')
    assert task.get("var", "psm_skip_nets") == ['net1']
    task.add_openroad_psmskipnets(['net2', 'net3'], step='sta', index='1')
    assert task.get("var", "psm_skip_nets", step='sta', index='1') == ['net2', 'net3']
    assert task.get("var", "psm_skip_nets") == ['net1']
    task.add_openroad_psmskipnets('net4', clobber=True)
    assert task.get("var", "psm_skip_nets") == ['net4']


def test_openroad_apr_parameter_ppl_layers_horizontal():
    task = _apr.OpenROADPPLLayersParameter()
    task.add_openroad_pinlayerhorizontal('hlayer1')
    assert task.get("var", "pin_layer_horizontal") == ['hlayer1']
    task.add_openroad_pinlayerhorizontal(['hlayer2', 'hlayer3'], step='sta', index='1')
    assert task.get("var", "pin_layer_horizontal", step='sta', index='1') == ['hlayer2', 'hlayer3']
    assert task.get("var", "pin_layer_horizontal") == ['hlayer1']
    task.add_openroad_pinlayerhorizontal('hlayer4', clobber=True)
    assert task.get("var", "pin_layer_horizontal") == ['hlayer4']


def test_openroad_apr_parameter_ppl_layers_vertical():
    task = _apr.OpenROADPPLLayersParameter()
    task.add_openroad_pinlayervertical('vlayer1')
    assert task.get("var", "pin_layer_vertical") == ['vlayer1']
    task.add_openroad_pinlayervertical(['vlayer2', 'vlayer3'], step='sta', index='1')
    assert task.get("var", "pin_layer_vertical", step='sta', index='1') == ['vlayer2', 'vlayer3']
    assert task.get("var", "pin_layer_vertical") == ['vlayer1']
    task.add_openroad_pinlayervertical('vlayer4', clobber=True)
    assert task.get("var", "pin_layer_vertical") == ['vlayer4']


def test_openroad_apr_parameter_ppl_arguments():
    task = _apr.OpenROADPPLParameter()
    task.add_openroad_pplarguments('arg1')
    assert task.get("var", "ppl_arguments") == ['arg1']
    task.add_openroad_pplarguments(['arg2', 'arg3'], step='sta', index='1')
    assert task.get("var", "ppl_arguments", step='sta', index='1') == ['arg2', 'arg3']
    assert task.get("var", "ppl_arguments") == ['arg1']
    task.add_openroad_pplarguments('arg4', clobber=True)
    assert task.get("var", "ppl_arguments") == ['arg4']


def test_openroad_apr_parameter_ppl_constraints():
    task = _apr.OpenROADPPLParameter()
    task.add_openroad_pplconstraints('constraint1')
    assert task.get("var", "ppl_constraints") == ['constraint1']
    task.add_openroad_pplconstraints(['constraint2', 'constraint3'], step='sta', index='1')
    assert task.get("var", "ppl_constraints", step='sta', index='1') == \
        ['constraint2', 'constraint3']
    assert task.get("var", "ppl_constraints") == ['constraint1']
    task.add_openroad_pplconstraints('constraint4', clobber=True)
    assert task.get("var", "ppl_constraints") == ['constraint4']


def test_openroad_apr_parameter_gpl_skip_io():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_gplskipio(True)
    assert task.get("var", "gpl_enable_skip_io") is True
    task.set_openroad_gplskipio(False, step='gpl', index='1')
    assert task.get("var", "gpl_enable_skip_io", step='gpl', index='1') is False
    assert task.get("var", "gpl_enable_skip_io") is True


def test_openroad_apr_parameter_gpl_skip_initial_place():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_gplskipinitialplace(True)
    assert task.get("var", "gpl_enable_skip_initial_place") is True
    task.set_openroad_gplskipinitialplace(False, step='gpl', index='1')
    assert task.get("var", "gpl_enable_skip_initial_place", step='gpl', index='1') is False
    assert task.get("var", "gpl_enable_skip_initial_place") is True


def test_openroad_apr_parameter_gpl_uniform_placement_adjustment():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_gpluniformplacementadjustment(0.5)
    assert task.get("var", "gpl_uniform_placement_adjustment") == 0.5
    task.set_openroad_gpluniformplacementadjustment(0.7, step='gpl', index='1')
    assert task.get("var", "gpl_uniform_placement_adjustment", step='gpl', index='1') == 0.7
    assert task.get("var", "gpl_uniform_placement_adjustment") == 0.5


def test_openroad_apr_parameter_gpl_timing_driven():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_gpltimingdriven(True)
    assert task.get("var", "gpl_timing_driven") is True
    task.set_openroad_gpltimingdriven(False, step='gpl', index='1')
    assert task.get("var", "gpl_timing_driven", step='gpl', index='1') is False
    assert task.get("var", "gpl_timing_driven") is True


def test_openroad_apr_parameter_gpl_routability_driven():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_gplroutabilitydriven(True)
    assert task.get("var", "gpl_routability_driven") is True
    task.set_openroad_gplroutabilitydriven(False, step='gpl', index='1')
    assert task.get("var", "gpl_routability_driven", step='gpl', index='1') is False
    assert task.get("var", "gpl_routability_driven") is True


def test_openroad_apr_parameter_place_density():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_placedensity(0.5)
    assert task.get("var", "place_density") == 0.5
    task.set_openroad_placedensity(0.7, step='gpl', index='1')
    assert task.get("var", "place_density", step='gpl', index='1') == 0.7
    assert task.get("var", "place_density") == 0.5


def test_openroad_apr_parameter_pad_global_place():
    task = _apr.OpenROADGPLParameter()
    task.set_openroad_padglobalplace(10)
    assert task.get("var", "pad_global_place") == 10
    task.set_openroad_padglobalplace(20, step='gpl', index='1')
    assert task.get("var", "pad_global_place", step='gpl', index='1') == 20
    assert task.get("var", "pad_global_place") == 10


def test_openroad_apr_parameter_rsz_cap_margin():
    task = _apr.OpenROADRSZDRVParameter()
    task.set_openroad_rszcapmargin(0.5)
    assert task.get("var", "rsz_cap_margin") == 0.5
    task.set_openroad_rszcapmargin(0.7, step='rsz', index='1')
    assert task.get("var", "rsz_cap_margin", step='rsz', index='1') == 0.7
    assert task.get("var", "rsz_cap_margin") == 0.5


def test_openroad_apr_parameter_rsz_slew_margin():
    task = _apr.OpenROADRSZDRVParameter()
    task.set_openroad_rszslewmargin(0.5)
    assert task.get("var", "rsz_slew_margin") == 0.5
    task.set_openroad_rszslewmargin(0.7, step='rsz', index='1')
    assert task.get("var", "rsz_slew_margin", step='rsz', index='1') == 0.7
    assert task.get("var", "rsz_slew_margin") == 0.5


def test_openroad_apr_parameter_rsz_setup_slack_margin():
    task = _apr.OpenROADRSZTimingParameter()
    task.set_openroad_rszsetupslackmargin(0.1)
    assert task.get("var", "rsz_setup_slack_margin") == 0.1
    task.set_openroad_rszsetupslackmargin(0.2, step='rsz', index='1')
    assert task.get("var", "rsz_setup_slack_margin", step='rsz', index='1') == 0.2
    assert task.get("var", "rsz_setup_slack_margin") == 0.1


def test_openroad_apr_parameter_rsz_hold_slack_margin():
    task = _apr.OpenROADRSZTimingParameter()
    task.set_openroad_rszholdslackmargin(0.1)
    assert task.get("var", "rsz_hold_slack_margin") == 0.1
    task.set_openroad_rszholdslackmargin(0.2, step='rsz', index='1')
    assert task.get("var", "rsz_hold_slack_margin", step='rsz', index='1') == 0.2
    assert task.get("var", "rsz_hold_slack_margin") == 0.1


def test_openroad_apr_parameter_rsz_skip_pin_swap():
    task = _apr.OpenROADRSZTimingParameter()
    # Both transforms are on in ORFS and LibreLane; they were skipped in SC only
    # because of LEC issues that have since been fixed upstream.
    assert task.get("var", "rsz_skip_pin_swap") is False
    task.set_openroad_rszskippinswap(True)
    assert task.get("var", "rsz_skip_pin_swap") is True
    task.set_openroad_rszskippinswap(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_pin_swap", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_pin_swap") is True


def test_openroad_apr_parameter_rsz_skip_gate_cloning():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_gate_cloning") is False
    task.set_openroad_rszskipgatecloning(True)
    assert task.get("var", "rsz_skip_gate_cloning") is True
    task.set_openroad_rszskipgatecloning(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_gate_cloning", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_gate_cloning") is True


def test_openroad_apr_parameter_rsz_repair_tns():
    task = _apr.OpenROADRSZTimingParameter()
    task.set_openroad_rszrepairtns(50)
    assert task.get("var", "rsz_repair_tns") == 50
    task.set_openroad_rszrepairtns(75, step='rsz', index='1')
    assert task.get("var", "rsz_repair_tns", step='rsz', index='1') == 75
    assert task.get("var", "rsz_repair_tns") == 50


def test_openroad_apr_parameter_rsz_recover_power():
    task = _apr.OpenROADRSZTimingParameter()
    task.set_openroad_rszrecoverpower(50)
    assert task.get("var", "rsz_recover_power") == 50
    task.set_openroad_rszrecoverpower(75, step='rsz', index='1')
    assert task.get("var", "rsz_recover_power", step='rsz', index='1') == 75
    assert task.get("var", "rsz_recover_power") == 50


def test_openroad_apr_parameter_rsz_skip_buffer_removal():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_buffer_removal") is False
    task.set_openroad_rszskipbufferremoval(True)
    assert task.get("var", "rsz_skip_buffer_removal") is True
    task.set_openroad_rszskipbufferremoval(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_buffer_removal", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_buffer_removal") is True


def test_openroad_apr_parameter_rsz_skip_buffering():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_buffering") is False
    task.set_openroad_rszskipbuffering(True)
    assert task.get("var", "rsz_skip_buffering") is True
    task.set_openroad_rszskipbuffering(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_buffering", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_buffering") is True


def test_openroad_apr_parameter_rsz_skip_final_sizing():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_final_sizing") is False
    task.set_openroad_rszskipfinalsizing(True)
    assert task.get("var", "rsz_skip_final_sizing") is True
    task.set_openroad_rszskipfinalsizing(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_final_sizing", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_final_sizing") is True


def test_openroad_apr_parameter_rsz_skip_vt_swap():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_vt_swap") is False
    task.set_openroad_rszskipvtswap(True)
    assert task.get("var", "rsz_skip_vt_swap") is True
    task.set_openroad_rszskipvtswap(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_vt_swap", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_vt_swap") is True


def test_openroad_apr_parameter_rsz_skip_crit_vt_swap():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_crit_vt_swap") is False
    task.set_openroad_rszskipcritvtswap(True)
    assert task.get("var", "rsz_skip_crit_vt_swap") is True
    task.set_openroad_rszskipcritvtswap(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_crit_vt_swap", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_crit_vt_swap") is True


def test_openroad_apr_parameter_rsz_sequence():
    task = _apr.OpenROADRSZTimingParameter()
    # Empty by default so OpenROAD picks its own move ordering.
    assert task.get("var", "rsz_sequence") == []
    task.add_openroad_rszsequence(["vt_swap", "reroute"])
    assert task.get("var", "rsz_sequence") == ["vt_swap", "reroute"]
    task.add_openroad_rszsequence("sizeup", step='rsz', index='1')
    assert task.get("var", "rsz_sequence", step='rsz', index='1') == ["sizeup"]
    assert task.get("var", "rsz_sequence") == ["vt_swap", "reroute"]


def test_openroad_apr_parameter_rsz_sequence_appends_in_order():
    """The move order is the point of the parameter, so appending has to preserve it."""
    task = _apr.OpenROADRSZTimingParameter()
    task.add_openroad_rszsequence("unbuffer")
    task.add_openroad_rszsequence(["sizeup", "swap"])
    assert task.get("var", "rsz_sequence") == ["unbuffer", "sizeup", "swap"]
    task.add_openroad_rszsequence("vt_swap", clobber=True)
    assert task.get("var", "rsz_sequence") == ["vt_swap"]


def test_openroad_apr_parameter_rsz_phases():
    task = _apr.OpenROADRSZTimingParameter()
    # Empty by default so OpenROAD picks its own phase ordering.
    assert task.get("var", "rsz_phases") == []
    task.add_openroad_rszphases(["LEGACY", "LAST_GASP"])
    assert task.get("var", "rsz_phases") == ["LEGACY", "LAST_GASP"]
    task.add_openroad_rszphases("GLOBAL_SIZING", step='rsz', index='1')
    assert task.get("var", "rsz_phases", step='rsz', index='1') == ["GLOBAL_SIZING"]
    assert task.get("var", "rsz_phases") == ["LEGACY", "LAST_GASP"]
    task.add_openroad_rszphases("WNS", clobber=True)
    assert task.get("var", "rsz_phases") == ["WNS"]


def test_openroad_apr_parameter_rsz_phases_rejects_unknown():
    """The phase names are matched exactly by OpenROAD, so reject a typo at set time.

    "legacy" is the wrong case and "LEGACY_MT" is real upstream but undocumented, so
    deliberately not offered. The member list comes from RSZ_PHASES rather than being
    written out, so adding a phase updates the expectation with it.
    """
    task = _apr.OpenROADRSZTimingParameter()
    members = ", ".join(sorted(_apr.RSZ_PHASES))
    for bad in ("legacy", "LEGACY_MT"):
        message = (f"error while adding to [var,rsz_phases]: "
                   f"{bad} is not a member of: {members}")
        with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
            task.add_openroad_rszphases([bad])


def test_openroad_apr_parameter_rsz_skip_size_down():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_skip_size_down") is False
    task.set_openroad_rszskipsizedown(True)
    assert task.get("var", "rsz_skip_size_down") is True
    task.set_openroad_rszskipsizedown(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_size_down", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_size_down") is True


def test_openroad_apr_parameter_rsz_max_passes():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_max_passes") is None
    task.set_openroad_rszmaxpasses(50)
    assert task.get("var", "rsz_max_passes") == 50
    task.set_openroad_rszmaxpasses(10, step='rsz', index='1')
    assert task.get("var", "rsz_max_passes", step='rsz', index='1') == 10
    assert task.get("var", "rsz_max_passes") == 50


def test_openroad_apr_parameter_rsz_max_iterations():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_max_iterations") is None
    task.set_openroad_rszmaxiterations(5)
    assert task.get("var", "rsz_max_iterations") == 5
    task.set_openroad_rszmaxiterations(2, step='rsz', index='1')
    assert task.get("var", "rsz_max_iterations", step='rsz', index='1') == 2
    assert task.get("var", "rsz_max_iterations") == 5


def test_openroad_apr_parameter_rsz_max_repairs_per_pass():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_max_repairs_per_pass") is None
    task.set_openroad_rszmaxrepairsperpass(4)
    assert task.get("var", "rsz_max_repairs_per_pass") == 4
    task.set_openroad_rszmaxrepairsperpass(1, step='rsz', index='1')
    assert task.get("var", "rsz_max_repairs_per_pass", step='rsz', index='1') == 1
    assert task.get("var", "rsz_max_repairs_per_pass") == 4


def test_openroad_apr_parameter_rsz_effort_caps_reject_zero():
    """0 passes/iterations/repairs is not a way to disable a phase; the skips are."""
    task = _apr.OpenROADRSZTimingParameter()
    for setter, var in ((task.set_openroad_rszmaxpasses, "rsz_max_passes"),
                        (task.set_openroad_rszmaxiterations, "rsz_max_iterations"),
                        (task.set_openroad_rszmaxrepairsperpass, "rsz_max_repairs_per_pass")):
        message = f"error while setting [var,{var}]: 0 is not in range: 1.."
        with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
            setter(0)


def test_openroad_apr_parameter_rsz_max_wire_length():
    task = _apr.OpenROADRSZDRVParameter()
    assert task.get("var", "rsz_max_wire_length") is None
    task.set_openroad_rszmaxwirelength(500.0)
    assert task.get("var", "rsz_max_wire_length") == 500.0
    task.set_openroad_rszmaxwirelength(100.0, step='rsz', index='1')
    assert task.get("var", "rsz_max_wire_length", step='rsz', index='1') == 100.0
    assert task.get("var", "rsz_max_wire_length") == 500.0


def test_openroad_apr_parameter_rsz_allow_setup_violations():
    task = _apr.OpenROADRSZTimingParameter()
    assert task.get("var", "rsz_allow_setup_violations") is False
    task.set_openroad_rszallowsetupviolations(True)
    assert task.get("var", "rsz_allow_setup_violations") is True
    task.set_openroad_rszallowsetupviolations(False, step='rsz', index='1')
    assert task.get("var", "rsz_allow_setup_violations", step='rsz', index='1') is False
    assert task.get("var", "rsz_allow_setup_violations") is True


def test_openroad_apr_parameter_rsz_max_buffer_percent():
    task = _apr.OpenROADRSZTimingParameter()
    # Unset, not 0: 0 is a meaningful value, so it cannot be the sentinel.
    assert task.get("var", "rsz_max_buffer_percent") is None
    task.set_openroad_rszmaxbufferpercent(20)
    assert task.get("var", "rsz_max_buffer_percent") == 20
    task.set_openroad_rszmaxbufferpercent(50, step='rsz', index='1')
    assert task.get("var", "rsz_max_buffer_percent", step='rsz', index='1') == 50
    assert task.get("var", "rsz_max_buffer_percent") == 20


def test_openroad_apr_parameter_rsz_match_cell_footprint():
    task = _apr.OpenROADRSZDRVParameter()
    assert task.get("var", "rsz_match_cell_footprint") is False
    task.set_openroad_rszmatchcellfootprint(True)
    assert task.get("var", "rsz_match_cell_footprint") is True
    task.set_openroad_rszmatchcellfootprint(False, step='rsz', index='1')
    assert task.get("var", "rsz_match_cell_footprint", step='rsz', index='1') is False
    assert task.get("var", "rsz_match_cell_footprint") is True


def test_openroad_apr_parameter_rsz_max_utilization():
    task = _apr.OpenROADRSZDRVParameter()
    assert task.get("var", "rsz_max_utilization") is None
    task.set_openroad_rszmaxutilization(80)
    assert task.get("var", "rsz_max_utilization") == 80
    task.set_openroad_rszmaxutilization(90, step='rsz', index='1')
    assert task.get("var", "rsz_max_utilization", step='rsz', index='1') == 90
    assert task.get("var", "rsz_max_utilization") == 80


def test_openroad_repair_design_has_footprint_and_utilization():
    """repair_design needs -match_cell_footprint/-max_utilization too, so they live
    on the DRV mixin rather than the timing-only one."""
    task = repair_design.RepairDesignTask()
    assert task.get("var", "rsz_match_cell_footprint") is False
    assert task.get("var", "rsz_max_utilization") is None


def test_openroad_apr_parameter_pad_detail_place():
    task = _apr.OpenROADDPLParameter()
    task.set_openroad_paddetailplace(1)
    assert task.get("var", "pad_detail_place") == 1
    task.set_openroad_paddetailplace(2, step='dpl', index='1')
    assert task.get("var", "pad_detail_place", step='dpl', index='1') == 2
    assert task.get("var", "pad_detail_place") == 1


def test_openroad_apr_parameter_dpl_max_displacement():
    task = _apr.OpenROADDPLParameter()
    task.set_openroad_dplmaxdisplacement(10.0, 10.0)
    assert task.get("var", "dpl_max_displacement") == (10.0, 10.0)
    task.set_openroad_dplmaxdisplacement(20.0, 20.0, step='dpl', index='1')
    assert task.get("var", "dpl_max_displacement", step='dpl', index='1') == (20.0, 20.0)
    assert task.get("var", "dpl_max_displacement") == (10.0, 10.0)


def test_openroad_apr_parameter_dpl_use_diamond_legalizer():
    task = _apr.OpenROADDPLParameter()
    assert task.get("var", "dpl_use_diamond_legalizer") is False
    task.set_openroad_dplusediamondlegalizer(True)
    assert task.get("var", "dpl_use_diamond_legalizer") is True
    task.set_openroad_dplusediamondlegalizer(False, step='dpl', index='1')
    assert task.get("var", "dpl_use_diamond_legalizer", step='dpl', index='1') is False
    assert task.get("var", "dpl_use_diamond_legalizer") is True


def test_openroad_apr_parameter_dpl_use_decap_fillers():
    task = _apr.OpenROADFillCellsParameter()
    task.set_openroad_dplusedecapfillers(True)
    assert task.get("var", "dpl_use_decap_fillers") is True
    task.set_openroad_dplusedecapfillers(False, step='dpl', index='1')
    assert task.get("var", "dpl_use_decap_fillers", step='dpl', index='1') is False
    assert task.get("var", "dpl_use_decap_fillers") is True


def test_openroad_apr_parameter_dpo_enable():
    task = _apr.OpenROADDPOParameter()
    task.set_openroad_dpoenable(True)
    assert task.get("var", "dpo_enable") is True
    task.set_openroad_dpoenable(False, step='dpo', index='1')
    assert task.get("var", "dpo_enable", step='dpo', index='1') is False
    assert task.get("var", "dpo_enable") is True


def test_openroad_apr_parameter_dpo_max_displacement():
    task = _apr.OpenROADDPOParameter()
    task.set_openroad_dpomaxdisplacement(5.0, 5.0)
    assert task.get("var", "dpo_max_displacement") == (5.0, 5.0)
    task.set_openroad_dpomaxdisplacement(10.0, 10.0, step='dpo', index='1')
    assert task.get("var", "dpo_max_displacement", step='dpo', index='1') == (10.0, 10.0)
    assert task.get("var", "dpo_max_displacement") == (5.0, 5.0)


def test_openroad_apr_parameter_cts_distance_between_buffers():
    task = _apr.OpenROADCTSParameter()
    task.set_openroad_ctsdistancebetweenbuffers(100.0)
    assert task.get("var", "cts_distance_between_buffers") == 100.0
    task.set_openroad_ctsdistancebetweenbuffers(200.0, step='cts', index='1')
    assert task.get("var", "cts_distance_between_buffers", step='cts', index='1') == 200.0
    assert task.get("var", "cts_distance_between_buffers") == 100.0


def test_openroad_apr_parameter_cts_cluster_diameter():
    task = _apr.OpenROADCTSParameter()
    task.set_openroad_ctsclusterdiameter(100.0)
    assert task.get("var", "cts_cluster_diameter") == 100.0
    task.set_openroad_ctsclusterdiameter(200.0, step='cts', index='1')
    assert task.get("var", "cts_cluster_diameter", step='cts', index='1') == 200.0
    assert task.get("var", "cts_cluster_diameter") == 100.0


def test_openroad_apr_parameter_cts_cluster_size():
    task = _apr.OpenROADCTSParameter()
    task.set_openroad_ctsclustersize(30)
    assert task.get("var", "cts_cluster_size") == 30
    task.set_openroad_ctsclustersize(60, step='cts', index='1')
    assert task.get("var", "cts_cluster_size", step='cts', index='1') == 60
    assert task.get("var", "cts_cluster_size") == 30


def test_openroad_apr_parameter_cts_balance_levels():
    task = _apr.OpenROADCTSParameter()
    task.set_openroad_ctsbalancelevels(True)
    assert task.get("var", "cts_balance_levels") is True
    task.set_openroad_ctsbalancelevels(False, step='cts', index='1')
    assert task.get("var", "cts_balance_levels", step='cts', index='1') is False
    assert task.get("var", "cts_balance_levels") is True


def test_openroad_apr_parameter_cts_obstruction_aware():
    task = _apr.OpenROADCTSParameter()
    task.set_openroad_ctsobstructionaware(True)
    assert task.get("var", "cts_obstruction_aware") is True
    task.set_openroad_ctsobstructionaware(False, step='cts', index='1')
    assert task.get("var", "cts_obstruction_aware", step='cts', index='1') is False
    assert task.get("var", "cts_obstruction_aware") is True


def test_openroad_apr_parameter_grt_macro_extension():
    task = _apr.OpenROADGRTGeneralParameter()
    task.set_openroad_grtmacroextension(1)
    assert task.get("var", "grt_macro_extension") == 1
    task.set_openroad_grtmacroextension(2, step='grt', index='1')
    assert task.get("var", "grt_macro_extension", step='grt', index='1') == 2
    assert task.get("var", "grt_macro_extension") == 1


def test_openroad_apr_parameter_grt_signal_min_layer():
    task = _apr.OpenROADGRTGeneralParameter()
    task.set_openroad_grtsignalminlayer('m1')
    assert task.get("var", "grt_signal_min_layer") == 'm1'
    task.set_openroad_grtsignalminlayer('m2', step='grt', index='1')
    assert task.get("var", "grt_signal_min_layer", step='grt', index='1') == 'm2'
    assert task.get("var", "grt_signal_min_layer") == 'm1'


def test_openroad_apr_parameter_grt_signal_max_layer():
    task = _apr.OpenROADGRTGeneralParameter()
    task.set_openroad_grtsignalmaxlayer('m10')
    assert task.get("var", "grt_signal_max_layer") == 'm10'
    task.set_openroad_grtsignalmaxlayer('m12', step='grt', index='1')
    assert task.get("var", "grt_signal_max_layer", step='grt', index='1') == 'm12'
    assert task.get("var", "grt_signal_max_layer") == 'm10'


def test_openroad_apr_parameter_grt_clock_min_layer():
    task = _apr.OpenROADGRTGeneralParameter()
    task.set_openroad_grtclockminlayer('m1')
    assert task.get("var", "grt_clock_min_layer") == 'm1'
    task.set_openroad_grtclockminlayer('m2', step='grt', index='1')
    assert task.get("var", "grt_clock_min_layer", step='grt', index='1') == 'm2'
    assert task.get("var", "grt_clock_min_layer") == 'm1'


def test_openroad_apr_parameter_grt_clock_max_layer():
    task = _apr.OpenROADGRTGeneralParameter()
    task.set_openroad_grtclockmaxlayer('m10')
    assert task.get("var", "grt_clock_max_layer") == 'm10'
    task.set_openroad_grtclockmaxlayer('m12', step='grt', index='1')
    assert task.get("var", "grt_clock_max_layer", step='grt', index='1') == 'm12'
    assert task.get("var", "grt_clock_max_layer") == 'm10'


def test_openroad_apr_parameter_grt_allow_congestion():
    task = _apr.OpenROADGRTParameter()
    task.set_openroad_grtallowcongestion(True)
    assert task.get("var", "grt_allow_congestion") is True
    task.set_openroad_grtallowcongestion(False, step='grt', index='1')
    assert task.get("var", "grt_allow_congestion", step='grt', index='1') is False
    assert task.get("var", "grt_allow_congestion") is True


def test_openroad_apr_parameter_grt_overflow_iter():
    task = _apr.OpenROADGRTParameter()
    task.set_openroad_grtoverflowiter(100)
    assert task.get("var", "grt_overflow_iter") == 100
    task.set_openroad_grtoverflowiter(200, step='grt', index='1')
    assert task.get("var", "grt_overflow_iter", step='grt', index='1') == 200
    assert task.get("var", "grt_overflow_iter") == 100


def test_openroad_apr_parameter_grt_resistance_aware():
    # On APRTask alongside load_grt_setup, not on the global routing mixins, because
    # it is also passed on the incremental global routes sc_detailed_placement issues
    # and that is reachable from any APR task.
    task = _apr.APRTask()
    assert task.get("var", "grt_resistance_aware") is False
    task.set_openroad_grtresistanceaware(True)
    assert task.get("var", "grt_resistance_aware") is True
    task.set_openroad_grtresistanceaware(False, step='grt', index='1')
    assert task.get("var", "grt_resistance_aware", step='grt', index='1') is False
    assert task.get("var", "grt_resistance_aware") is True


def test_openroad_apr_parameter_grt_seed():
    task = _apr.OpenROADGRTParameter()
    assert task.get("var", "grt_seed") is None
    task.set_openroad_grtseed(42)
    assert task.get("var", "grt_seed") == 42
    task.set_openroad_grtseed(7, step='grt', index='1')
    assert task.get("var", "grt_seed", step='grt', index='1') == 7
    assert task.get("var", "grt_seed") == 42


def test_openroad_global_route_has_grt_knobs():
    """The seed only makes sense where global_route is driven; resistance-aware is on
    every APR task because sc_detailed_placement can reach it."""
    task = global_route.GlobalRouteTask()
    assert task.get("var", "grt_seed") is None
    assert task.get("var", "grt_resistance_aware") is False


@pytest.mark.parametrize("task_cls", [
    detailed_placement.DetailedPlacementTask,
    clock_tree_synthesis.CTSTask,
    repair_timing.RepairTimingTask,
    repair_timing.PostRouteRepairTimingTask,
])
def test_openroad_detailed_placement_callers_have_resistance_aware(task_cls):
    """sc_detailed_placement reads grt_resistance_aware unconditionally, so every task
    that calls it must declare the var."""
    assert task_cls().get("var", "grt_resistance_aware") is False


def test_openroad_post_route_repair_timing_has_no_seed():
    """The seed belongs to the task that actually drives global_route."""
    assert not repair_timing.PostRouteRepairTimingTask().valid("var", "grt_seed")


def test_openroad_apr_parameter_ant_check():
    task = _apr.OpenROADANTCheckParameter()
    assert task.get("var", "ant_check") is True
    task.set_openroad_antcheck(False)
    assert task.get("var", "ant_check") is False
    task.set_openroad_antcheck(True, step='ant', index='1')
    assert task.get("var", "ant_check", step='ant', index='1') is True
    assert task.get("var", "ant_check") is False


def test_openroad_apr_parameter_ant_repair():
    task = _apr.OpenROADANTCheckParameter()
    assert task.get("var", "ant_repair") is True
    task.set_openroad_antrepair(False)
    assert task.get("var", "ant_repair") is False
    task.set_openroad_antrepair(True, step='ant', index='1')
    assert task.get("var", "ant_repair", step='ant', index='1') is True
    assert task.get("var", "ant_repair") is False


def test_openroad_apr_parameter_ant_iterations():
    task = _apr.OpenROADANTParameter()
    task.set_openroad_antiterations(3)
    assert task.get("var", "ant_iterations") == 3
    task.set_openroad_antiterations(5, step='ant', index='1')
    assert task.get("var", "ant_iterations", step='ant', index='1') == 5
    assert task.get("var", "ant_iterations") == 3


def test_openroad_apr_parameter_ant_margin():
    task = _apr.OpenROADANTParameter()
    task.set_openroad_antmargin(10.0)
    assert task.get("var", "ant_margin") == 10.0
    task.set_openroad_antmargin(20.0, step='ant', index='1')
    assert task.get("var", "ant_margin", step='ant', index='1') == 20.0
    assert task.get("var", "ant_margin") == 10.0


def test_openroad_apr_parameter_drt_process_node():
    task = _apr._OpenROADDRTCommonParameter()
    task.set_openroad_drtprocessnode('test_node')
    assert task.get("var", "drt_process_node") == 'test_node'
    task.set_openroad_drtprocessnode('other_node', step='drt', index='1')
    assert task.get("var", "drt_process_node", step='drt', index='1') == 'other_node'
    assert task.get("var", "drt_process_node") == 'test_node'


def test_openroad_apr_parameter_detailed_route_default_via():
    task = _apr._OpenROADDRTCommonParameter()
    task.add_openroad_detailedroutedefaultvia('via1')
    assert task.get("var", "detailed_route_default_via") == ['via1']
    task.add_openroad_detailedroutedefaultvia(['via2', 'via3'], step='drt', index='1')
    assert task.get("var", "detailed_route_default_via", step='drt', index='1') == ['via2', 'via3']
    assert task.get("var", "detailed_route_default_via") == ['via1']
    task.add_openroad_detailedroutedefaultvia('via4', clobber=True)
    assert task.get("var", "detailed_route_default_via") == ['via4']


def test_openroad_apr_parameter_detailed_route_unidirectional_layer():
    task = _apr._OpenROADDRTCommonParameter()
    task.add_openroad_detailedrouteunidirectionallayer('layer1')
    assert task.get("var", "detailed_route_unidirectional_layer") == ['layer1']
    task.add_openroad_detailedrouteunidirectionallayer(['layer2', 'layer3'], step='drt', index='1')
    assert task.get("var", "detailed_route_unidirectional_layer", step='drt', index='1') == \
        ['layer2', 'layer3']
    assert task.get("var", "detailed_route_unidirectional_layer") == ['layer1']
    task.add_openroad_detailedrouteunidirectionallayer('layer4', clobber=True)
    assert task.get("var", "detailed_route_unidirectional_layer") == ['layer4']


def test_openroad_apr_parameter_drt_disable_via_gen():
    task = _apr.OpenROADDRTParameter()
    task.set_openroad_drtdisableviagen(True)
    assert task.get("var", "drt_disable_via_gen") is True
    task.set_openroad_drtdisableviagen(False, step='drt', index='1')
    assert task.get("var", "drt_disable_via_gen", step='drt', index='1') is False
    assert task.get("var", "drt_disable_via_gen") is True


def test_openroad_apr_parameter_drt_via_in_pin_bottom_layer():
    task = _apr.OpenROADDRTParameter()
    task.set_openroad_drtviainpinbottomlayer('m1')
    assert task.get("var", "drt_via_in_pin_bottom_layer") == 'm1'
    task.set_openroad_drtviainpinbottomlayer('m2', step='drt', index='1')
    assert task.get("var", "drt_via_in_pin_bottom_layer", step='drt', index='1') == 'm2'
    assert task.get("var", "drt_via_in_pin_bottom_layer") == 'm1'


def test_openroad_apr_parameter_drt_via_in_pin_top_layer():
    task = _apr.OpenROADDRTParameter()
    task.set_openroad_drtviainpintoplayer('m10')
    assert task.get("var", "drt_via_in_pin_top_layer") == 'm10'
    task.set_openroad_drtviainpintoplayer('m12', step='drt', index='1')
    assert task.get("var", "drt_via_in_pin_top_layer", step='drt', index='1') == 'm12'
    assert task.get("var", "drt_via_in_pin_top_layer") == 'm10'


def test_openroad_apr_parameter_drt_repair_pdn_vias():
    task = _apr.OpenROADDRTParameter()
    task.set_openroad_drtrepairpdnvias('m1')
    assert task.get("var", "drt_repair_pdn_vias") == 'm1'
    task.set_openroad_drtrepairpdnvias('m2', step='drt', index='1')
    assert task.get("var", "drt_repair_pdn_vias", step='drt', index='1') == 'm2'
    assert task.get("var", "drt_repair_pdn_vias") == 'm1'


def test_openroad_apr_parameter_drt_report_interval():
    task = _apr.OpenROADDRTParameter()
    task.set_openroad_drtreportinterval(5)
    assert task.get("var", "drt_report_interval") == 5
    task.set_openroad_drtreportinterval(10, step='drt', index='1')
    assert task.get("var", "drt_report_interval", step='drt', index='1') == 10
    assert task.get("var", "drt_report_interval") == 5


def test_openroad_apr_parameter_drt_end_iteration():
    task = _apr.OpenROADDRTParameter()
    task.set_openroad_drtenditeration(10)
    assert task.get("var", "drt_end_iteration") == 10
    task.set_openroad_drtenditeration(20, step='drt', index='1')
    assert task.get("var", "drt_end_iteration", step='drt', index='1') == 20
    assert task.get("var", "drt_end_iteration") == 10


def test_openroad_apr_parameter_skip_report():
    task = _apr.APRTask()
    task.add_openroad_skipreport('clock_placement')
    assert task.get("var", "skip_reports") == ['clock_placement']
    task.add_openroad_skipreport(['clock_skew', 'clock_trees'], step='apr', index='1')
    assert task.get("var", "skip_reports", step='apr', index='1') == ['clock_skew', 'clock_trees']
    assert task.get("var", "skip_reports") == ['clock_placement']
    task.add_openroad_skipreport('fmax', clobber=True)
    assert task.get("var", "skip_reports") == ['fmax']


def test_openroad_apr_parameter_enable_images():
    task = _apr.APRTask()
    task.set_openroad_enableimages(True)
    assert task.get("var", "ord_enable_images") is True
    task.set_openroad_enableimages(False, step='apr', index='1')
    assert task.get("var", "ord_enable_images", step='apr', index='1') is False
    assert task.get("var", "ord_enable_images") is True


def test_openroad_apr_parameter_heatmap_bins():
    task = _apr.APRTask()
    task.set_openroad_heatmapbins(16, 16)
    assert task.get("var", "ord_heatmap_bins") == (16, 16)
    task.set_openroad_heatmapbins(32, 32, step='apr', index='1')
    assert task.get("var", "ord_heatmap_bins", step='apr', index='1') == (32, 32)
    assert task.get("var", "ord_heatmap_bins") == (16, 16)


def test_openroad_apr_parameter_power_corner():
    task = _apr.APRTask()
    task.set_openroad_powercorner('test_corner')
    assert task.get("var", "power_corner") == 'test_corner'
    task.set_openroad_powercorner('other_corner', step='apr', index='1')
    assert task.get("var", "power_corner", step='apr', index='1') == 'other_corner'
    assert task.get("var", "power_corner") == 'test_corner'


def test_openroad_apr_parameter_global_connect_fileset():
    task = _apr.APRTask()
    task.add_openroad_globalconnectfileset('lib1', 'fileset1')
    assert task.get("var", "global_connect_fileset") == [('lib1', 'fileset1')]
    task.add_openroad_globalconnectfileset('lib2', 'fileset2', step='apr', index='1')
    assert task.get("var", "global_connect_fileset", step='apr', index='1') == \
        [('lib2', 'fileset2')]
    assert task.get("var", "global_connect_fileset") == [('lib1', 'fileset1')]
    task.add_openroad_globalconnectfileset('lib3', 'fileset3', clobber=True)
    assert task.get("var", "global_connect_fileset") == [('lib3', 'fileset3')]


def test_openroad_antenna_repair_parameter_ant_check():
    task = antenna_repair.AntennaRepairTask()
    task.set_openroad_antcheck(True)
    assert task.get("var", "ant_check") is True
    task.set_openroad_antcheck(False, step='antenna_repair', index='1')
    assert task.get("var", "ant_check", step='antenna_repair', index='1') is False
    assert task.get("var", "ant_check") is True


def test_openroad_antenna_repair_parameter_ant_repair():
    task = antenna_repair.AntennaRepairTask()
    task.set_openroad_antrepair(True)
    assert task.get("var", "ant_repair") is True
    task.set_openroad_antrepair(False, step='antenna_repair', index='1')
    assert task.get("var", "ant_repair", step='antenna_repair', index='1') is False
    assert task.get("var", "ant_repair") is True


def test_openroad_fillmetal_insertion_parameter_add_fill():
    task = fillmetal_insertion.FillMetalTask()
    task.set_openroad_addfill(True)
    assert task.get("var", "fin_add_fill") is True
    task.set_openroad_addfill(False, step='fillmetal_insertion', index='1')
    assert task.get("var", "fin_add_fill", step='fillmetal_insertion', index='1') is False
    assert task.get("var", "fin_add_fill") is True


def test_openroad_fillmetal_insertion_skips_when_disabled(asic_gcd):
    """fin_add_fill=False must drop the node, not run a process that fills nothing.

    The reason is asserted because the ordering matters: the disabled check has to
    come before the PDK rule lookup, or a disabled task on a PDK with no rules would
    report the wrong cause.
    """
    fillmetal_insertion.FillMetalTask.find_task(asic_gcd).set_openroad_addfill(False)

    node = SchedulerNode(asic_gcd, "dfm.metal_fill", "0")
    with node.runtime():
        with pytest.raises(TaskSkip, match="^metal fill is disabled$"):
            node.task.setup()
        assert node.setup() is False


def test_openroad_fillmetal_insertion_skips_without_pdk_rules(asic_gcd):
    """Fill enabled but no PDK fill file to work from still skips the node."""
    fillmetal_insertion.FillMetalTask.find_task(asic_gcd).set_openroad_addfill(True)

    # Drop any fill rules the PDK ships so the skip is exercised regardless of
    # what freepdk45 provides.
    pdk = asic_gcd.get_library(asic_gcd.get("asic", "pdk"))
    for fileset in pdk.get("pdk", "aprtechfileset", "openroad"):
        pdk.unset("fileset", fileset, "file", "fill")

    node = SchedulerNode(asic_gcd, "dfm.metal_fill", "0")
    with node.runtime():
        assert node.task.get("var", "fin_add_fill") is True
        with pytest.raises(TaskSkip, match="^no metal fill rules are available$"):
            node.task.setup()
        assert node.setup() is False


def test_openroad_fillmetal_insertion_disabled_still_runs_with_a_script(asic_gcd):
    """A pre or post script is a reason to run even with nothing to fill."""
    task = fillmetal_insertion.FillMetalTask.find_task(asic_gcd)
    task.set_openroad_addfill(False)
    task.add_prescript(__file__)

    node = SchedulerNode(asic_gcd, "dfm.metal_fill", "0")
    with node.runtime():
        assert node.setup() is True


def test_openroad_global_placement_parameter_enable_scan_chains():
    task = global_placement.GlobalPlacementTask()
    task.set_openroad_enablescanchains(True)
    assert task.get("var", "enable_scan_chains") is True
    task.set_openroad_enablescanchains(False, step='global_placement', index='1')
    assert task.get("var", "enable_scan_chains", step='global_placement', index='1') is False
    assert task.get("var", "enable_scan_chains") is True


def test_openroad_global_placement_parameter_scan_enable_port_pattern():
    task = global_placement.GlobalPlacementTask()
    task.set_openroad_scanenableportpattern('test_pattern')
    assert task.get("var", "scan_enable_port_pattern") == 'test_pattern'
    task.set_openroad_scanenableportpattern('other_pattern', step='global_placement', index='1')
    assert task.get("var", "scan_enable_port_pattern", step='global_placement', index='1') == \
        'other_pattern'
    assert task.get("var", "scan_enable_port_pattern") == 'test_pattern'


def test_openroad_global_placement_parameter_scan_in_port_pattern():
    task = global_placement.GlobalPlacementTask()
    task.set_openroad_scaninportpattern('test_pattern')
    assert task.get("var", "scan_in_port_pattern") == 'test_pattern'
    task.set_openroad_scaninportpattern('other_pattern', step='global_placement', index='1')
    assert task.get("var", "scan_in_port_pattern", step='global_placement', index='1') == \
        'other_pattern'
    assert task.get("var", "scan_in_port_pattern") == 'test_pattern'


def test_openroad_global_placement_parameter_scan_out_port_pattern():
    task = global_placement.GlobalPlacementTask()
    task.set_openroad_scanoutportpattern('test_pattern')
    assert task.get("var", "scan_out_port_pattern") == 'test_pattern'
    task.set_openroad_scanoutportpattern('other_pattern', step='global_placement', index='1')
    assert task.get("var", "scan_out_port_pattern", step='global_placement', index='1') == \
        'other_pattern'
    assert task.get("var", "scan_out_port_pattern") == 'test_pattern'


def test_openroad_global_placement_parameter_enable_multibit_clustering():
    task = global_placement.GlobalPlacementTask()
    task.set_openroad_enablemultibitclustering(True)
    assert task.get("var", "enable_multibit_clustering") is True
    task.set_openroad_enablemultibitclustering(False, step='global_placement', index='1')
    assert task.get("var", "enable_multibit_clustering", step='global_placement', index='1') \
        is False
    assert task.get("var", "enable_multibit_clustering") is True


def test_openroad_global_route_parameter_use_pin_access():
    task = global_route.GlobalRouteTask()
    task.set_openroad_usepinaccess(True)
    assert task.get("var", "grt_use_pin_access") is True
    task.set_openroad_usepinaccess(False, step='global_route', index='1')
    assert task.get("var", "grt_use_pin_access", step='global_route', index='1') is False
    assert task.get("var", "grt_use_pin_access") is True


def test_openroad_init_floorplan_parameter_snap_strategy():
    task = init_floorplan.InitFloorplanTask()
    task.set_openroad_snapstrategy('site')
    assert task.get("var", "ifp_snap_strategy") == 'site'
    task.set_openroad_snapstrategy('grid', step='init_floorplan', index='1')
    assert task.get("var", "ifp_snap_strategy", step='init_floorplan', index='1') == 'grid'
    assert task.get("var", "ifp_snap_strategy") == 'site'


def test_openroad_init_floorplan_parameter_remove_buffers():
    task = init_floorplan.InitFloorplanTask()
    with pytest.warns(DeprecationWarning,
                      match="set_openroad_removebuffers is deprecated in init_floorplan. "
                            "Use cleanup_synth instead."):
        task.set_openroad_removebuffers(True)


def test_openroad_init_floorplan_parameter_remove_dead_logic():
    task = init_floorplan.InitFloorplanTask()
    with pytest.warns(DeprecationWarning,
                      match="set_openroad_removedeadlogic is deprecated in init_floorplan. "
                            "Use cleanup_synth instead."):
        task.set_openroad_removedeadlogic(True)


def test_openroad_cleanup_synth_parameter_remove_buffers():
    task = synth_cleanup.CleanupSynthTask()
    task.set_openroad_removebuffers(True)
    assert task.get("var", "remove_synth_buffers") is True
    task.set_openroad_removebuffers(False, step='cleanup_synth', index='1')
    assert task.get("var", "remove_synth_buffers", step='cleanup_synth', index='1') is False
    assert task.get("var", "remove_synth_buffers") is True


def test_openroad_cleanup_synth_parameter_remove_dead_logic():
    task = synth_cleanup.CleanupSynthTask()
    task.set_openroad_removedeadlogic(True)
    assert task.get("var", "remove_dead_logic") is True
    task.set_openroad_removedeadlogic(False, step='cleanup_synth', index='1')
    assert task.get("var", "remove_dead_logic", step='cleanup_synth', index='1') is False
    assert task.get("var", "remove_dead_logic") is True


def test_openroad_cleanup_synth_parameter_repair_synth_timing():
    task = synth_cleanup.CleanupSynthTask()
    # Off by default: enabling it moves the quality of results of every design.
    assert task.get("var", "repair_synth_timing") is False
    task.set_openroad_repairsynthtiming(True)
    assert task.get("var", "repair_synth_timing") is True
    task.set_openroad_repairsynthtiming(False, step='cleanup_synth', index='1')
    assert task.get("var", "repair_synth_timing", step='cleanup_synth', index='1') is False
    assert task.get("var", "repair_synth_timing") is True


def test_openroad_cleanup_synth_restricts_the_move_sequence():
    """Only the moves a pre-placement pass can justify, and no final sizing pass.

    Buffer insertion, cloning and load splitting are wire-delay driven and there is no
    wire length yet, so the default sequence is deliberately narrower than the tool's.
    """
    task = synth_cleanup.CleanupSynthTask()
    assert task.get("var", "rsz_sequence") == ["unbuffer", "sizeup"]
    assert task.get("var", "rsz_skip_final_sizing") is True


@pytest.mark.parametrize("remove,repair,legal", [
    (True, False, True),      # the shipped default
    (False, True, True),      # keep the buffers and refine them
    (False, False, True),     # leave the netlist as synthesized
    (True, True, False),      # delete the buffering, then forbid replacing it
])
def test_openroad_cleanup_synth_rejects_remove_plus_repair(asic_gcd, remove, repair, legal):
    """Buffer removal and timing repair are alternatives; one or neither is legal."""
    task = synth_cleanup.CleanupSynthTask.find_task(asic_gcd)
    task.set_openroad_removebuffers(remove)
    task.set_openroad_repairsynthtiming(repair)

    node = SchedulerNode(asic_gcd, "cleanup.clean", "0")
    with node.runtime():
        if legal:
            assert node.setup() is True
        else:
            with pytest.raises(ValueError,
                               match=r"^remove_synth_buffers and repair_synth_timing are "
                                     r"alternatives, not additive: .* Enable one or neither\.$"):
                node.task.setup()


def test_openroad_cleanup_synth_defaults_do_not_leak_to_repair_timing():
    """The narrowed defaults are per-task, so the resizer tasks keep the tool defaults."""
    for task in (repair_timing.RepairTimingTask(), repair_design.RepairDesignTask()):
        if task.valid("var", "rsz_sequence"):
            assert task.get("var", "rsz_sequence") == [], task.task()
        if task.valid("var", "rsz_skip_final_sizing"):
            assert task.get("var", "rsz_skip_final_sizing") is False, task.task()


def test_openroad_init_floorplan_parameter_padring_fileset():
    task = init_floorplan.InitFloorplanTask()
    task.add_openroad_padringfileset('fileset1')
    assert task.get("var", "padringfileset") == ['fileset1']
    task.add_openroad_padringfileset(['fileset2', 'fileset3'], step='init_floorplan', index='1')
    assert task.get("var", "padringfileset", step='init_floorplan', index='1') == \
        ['fileset2', 'fileset3']
    assert task.get("var", "padringfileset") == ['fileset1']
    task.add_openroad_padringfileset('fileset4', clobber=True)
    assert task.get("var", "padringfileset") == ['fileset4']


def test_openroad_init_floorplan_parameter_bumpmap_fileset():
    task = init_floorplan.InitFloorplanTask()
    task.add_openroad_bumpmapfileset('fileset1')
    assert task.get("var", "bumpmapfileset") == ['fileset1']
    task.add_openroad_bumpmapfileset(['fileset2', 'fileset3'], step='init_floorplan', index='1')
    assert task.get("var", "bumpmapfileset", step='init_floorplan', index='1') == \
        ['fileset2', 'fileset3']
    assert task.get("var", "bumpmapfileset") == ['fileset1']
    task.add_openroad_bumpmapfileset('fileset4', clobber=True)
    assert task.get("var", "bumpmapfileset") == ['fileset4']


def test_openroad_macro_placement_parameter_mpl_constraints():
    task = macro_placement.MacroPlacementTask()
    task.add_openroad_mplconstraints('constraint1')
    assert task.get("var", "mpl_constraints") == ['constraint1']
    task.add_openroad_mplconstraints(['constraint2', 'constraint3'],
                                     step='macro_placement', index='1')
    assert task.get("var", "mpl_constraints", step='macro_placement', index='1') == \
        ['constraint2', 'constraint3']
    assert task.get("var", "mpl_constraints") == ['constraint1']
    task.add_openroad_mplconstraints('constraint4', clobber=True)
    assert task.get("var", "mpl_constraints") == ['constraint4']


def test_openroad_macro_placement_parameter_macro_place_halo():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_macroplacehalo(1.0, 1.0)
    assert task.get("var", "macro_place_halo") == (1.0, 1.0)
    task.set_openroad_macroplacehalo(2.0, 2.0, step='macro_placement', index='1')
    assert task.get("var", "macro_place_halo", step='macro_placement', index='1') == (2.0, 2.0)
    assert task.get("var", "macro_place_halo") == (1.0, 1.0)


def test_openroad_macro_placement_parameter_mpl_min_instances():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplmininstances(10)
    assert task.get("var", "mpl_min_instances") == 10
    task.set_openroad_mplmininstances(20, step='macro_placement', index='1')
    assert task.get("var", "mpl_min_instances", step='macro_placement', index='1') == 20
    assert task.get("var", "mpl_min_instances") == 10


def test_openroad_macro_placement_parameter_mpl_max_instances():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplmaxinstances(100)
    assert task.get("var", "mpl_max_instances") == 100
    task.set_openroad_mplmaxinstances(200, step='macro_placement', index='1')
    assert task.get("var", "mpl_max_instances", step='macro_placement', index='1') == 200
    assert task.get("var", "mpl_max_instances") == 100


def test_openroad_macro_placement_parameter_mpl_min_macros():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplminmacros(1)
    assert task.get("var", "mpl_min_macros") == 1
    task.set_openroad_mplminmacros(2, step='macro_placement', index='1')
    assert task.get("var", "mpl_min_macros", step='macro_placement', index='1') == 2
    assert task.get("var", "mpl_min_macros") == 1


def test_openroad_macro_placement_parameter_mpl_max_macros():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplmaxmacros(10)
    assert task.get("var", "mpl_max_macros") == 10
    task.set_openroad_mplmaxmacros(20, step='macro_placement', index='1')
    assert task.get("var", "mpl_max_macros", step='macro_placement', index='1') == 20
    assert task.get("var", "mpl_max_macros") == 10


def test_openroad_macro_placement_parameter_mpl_max_levels():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplmaxlevels(5)
    assert task.get("var", "mpl_max_levels") == 5
    task.set_openroad_mplmaxlevels(10, step='macro_placement', index='1')
    assert task.get("var", "mpl_max_levels", step='macro_placement', index='1') == 10
    assert task.get("var", "mpl_max_levels") == 5


def test_openroad_macro_placement_parameter_mpl_min_aspect_ratio():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplminaspectratio(0.5)
    assert task.get("var", "mpl_min_aspect_ratio") == 0.5
    task.set_openroad_mplminaspectratio(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_min_aspect_ratio", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_min_aspect_ratio") == 0.5


def test_openroad_macro_placement_parameter_mpl_fence():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplfence(0.0, 0.0, 100.0, 100.0)
    assert task.get("var", "mpl_fence") == (0.0, 0.0, 100.0, 100.0)
    task.set_openroad_mplfence(10.0, 10.0, 90.0, 90.0, step='macro_placement', index='1')
    assert task.get("var", "mpl_fence", step='macro_placement', index='1') == \
        (10.0, 10.0, 90.0, 90.0)
    assert task.get("var", "mpl_fence") == (0.0, 0.0, 100.0, 100.0)


def test_openroad_macro_placement_parameter_mpl_bus_planning():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplbusplanning(True)
    assert task.get("var", "mpl_bus_planning") is True
    task.set_openroad_mplbusplanning(False, step='macro_placement', index='1')
    assert task.get("var", "mpl_bus_planning", step='macro_placement', index='1') is False
    assert task.get("var", "mpl_bus_planning") is True


def test_openroad_macro_placement_parameter_mpl_target_dead_space():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mpltargetdeadspace(0.1)
    assert task.get("var", "mpl_target_dead_space") == 0.1
    task.set_openroad_mpltargetdeadspace(0.2, step='macro_placement', index='1')
    assert task.get("var", "mpl_target_dead_space", step='macro_placement', index='1') == 0.2
    assert task.get("var", "mpl_target_dead_space") == 0.1


def test_openroad_macro_placement_parameter_mpl_area_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplareaweight(0.5)
    assert task.get("var", "mpl_area_weight") == 0.5
    task.set_openroad_mplareaweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_area_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_area_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_outline_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mploutlineweight(0.5)
    assert task.get("var", "mpl_outline_weight") == 0.5
    task.set_openroad_mploutlineweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_outline_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_outline_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_wirelength_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplwirelengthweight(0.5)
    assert task.get("var", "mpl_wirelength_weight") == 0.5
    task.set_openroad_mplwirelengthweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_wirelength_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_wirelength_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_guidance_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplguidanceweight(0.5)
    assert task.get("var", "mpl_guidance_weight") == 0.5
    task.set_openroad_mplguidanceweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_guidance_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_guidance_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_fence_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplfenceweight(0.5)
    assert task.get("var", "mpl_fence_weight") == 0.5
    task.set_openroad_mplfenceweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_fence_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_fence_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_boundary_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplboundaryweight(0.5)
    assert task.get("var", "mpl_boundary_weight") == 0.5
    task.set_openroad_mplboundaryweight(.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_boundary_weight", step='macro_placement', index='1') == .7
    assert task.get("var", "mpl_boundary_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_blockage_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplblockageweight(0.5)
    assert task.get("var", "mpl_blockage_weight") == 0.5
    task.set_openroad_mplblockageweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_blockage_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_blockage_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_notch_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplnotchweight(0.5)
    assert task.get("var", "mpl_notch_weight") == 0.5
    task.set_openroad_mplnotchweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_notch_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_notch_weight") == 0.5


def test_openroad_macro_placement_parameter_mpl_macro_blockage_weight():
    task = macro_placement.MacroPlacementTask()
    task.set_openroad_mplmacroblockageweight(0.5)
    assert task.get("var", "mpl_macro_blockage_weight") == 0.5
    task.set_openroad_mplmacroblockageweight(0.7, step='macro_placement', index='1')
    assert task.get("var", "mpl_macro_blockage_weight", step='macro_placement', index='1') == 0.7
    assert task.get("var", "mpl_macro_blockage_weight") == 0.5


def test_openroad_power_grid_analysis_parameter_disconnect_rate():
    task = power_grid_analysis.PowerGridAnalysisTask()
    task.set_openroad_disconnectrate(10.0)
    assert task.get("var", "source_disconnection_rate") == 10.0
    task.set_openroad_disconnectrate(20.0, step='power_grid_analysis', index='1')
    assert task.get("var", "source_disconnection_rate", step='power_grid_analysis', index='1') \
        == 20.0
    assert task.get("var", "source_disconnection_rate") == 10.0


def test_openroad_power_grid_analysis_parameter_disconnect_seed():
    task = power_grid_analysis.PowerGridAnalysisTask()
    task.set_openroad_disconnectseed(123)
    assert task.get("var", "source_disconnection_seed") == 123
    task.set_openroad_disconnectseed(456, step='power_grid_analysis', index='1')
    assert task.get("var", "source_disconnection_seed", step='power_grid_analysis', index='1') \
        == 456
    assert task.get("var", "source_disconnection_seed") == 123


def test_openroad_power_grid_analysis_parameter_heatmap_grid():
    task = power_grid_analysis.PowerGridAnalysisTask()
    task.set_openroad_heatmapgrid(10.0, 10.0)
    assert task.get("var", "heatmap_grid") == (10.0, 10.0)
    task.set_openroad_heatmapgrid(20.0, 20.0, step='power_grid_analysis', index='1')
    assert task.get("var", "heatmap_grid", step='power_grid_analysis', index='1') == (20.0, 20.0)
    assert task.get("var", "heatmap_grid") == (10.0, 10.0)


def test_openroad_power_grid_analysis_parameter_external_resistance():
    task = power_grid_analysis.PowerGridAnalysisTask()
    task.set_openroad_externalresistance(0.1)
    assert task.get("var", "external_resistance") == 0.1
    task.set_openroad_externalresistance(0.2, step='power_grid_analysis', index='1')
    assert task.get("var", "external_resistance", step='power_grid_analysis', index='1') == 0.2
    assert task.get("var", "external_resistance") == 0.1


def test_openroad_power_grid_analysis_parameter_irdrop_net():
    task = power_grid_analysis.PowerGridAnalysisTask()
    task.add_openroad_irdropnet('VDD')
    assert task.get("var", "net") == ['VDD']
    task.add_openroad_irdropnet(['VSS'], step='power_grid_analysis', index='1')
    assert task.get("var", "net", step='power_grid_analysis', index='1') == ['VSS']
    assert task.get("var", "net") == ['VDD']
    task.add_openroad_irdropnet('VDD2', clobber=True)
    assert task.get("var", "net") == ['VDD2']


def test_openroad_power_grid_analysis_parameter_instance_power():
    task = power_grid_analysis.PowerGridAnalysisTask()
    task.add_openroad_instancepower('inst1', 0.1)
    assert task.get("var", "instance_power") == [('inst1', 0.1)]
    task.add_openroad_instancepower('inst2', 0.2, step='power_grid_analysis', index='1')
    assert task.get("var", "instance_power", step='power_grid_analysis', index='1') == \
        [('inst2', 0.2)]
    assert task.get("var", "instance_power") == [('inst1', 0.1)]
    task.add_openroad_instancepower('inst3', 0.3, clobber=True)
    assert task.get("var", "instance_power") == [('inst3', 0.3)]


def test_openroad_power_grid_parameter_powergrid_fileset():
    task = power_grid.PowerGridTask()
    task.add_openroad_powergridfileset('lib1', 'fileset1')
    assert task.get("var", "pdn_fileset") == [('lib1', 'fileset1')]
    task.add_openroad_powergridfileset('lib2', 'fileset2', clobber=True)
    assert task.get("var", "pdn_fileset") == [('lib2', 'fileset2')]


def test_openroad_power_grid_parameter_fixed_pin_keepout():
    task = power_grid.PowerGridTask()
    task.set_openroad_fixedpinkeepout(1.0)
    assert task.get("var", "fixed_pin_keepout") == 1.0
    task.set_openroad_fixedpinkeepout(2.0, step='power_grid', index='1')
    assert task.get("var", "fixed_pin_keepout", step='power_grid', index='1') == 2.0
    assert task.get("var", "fixed_pin_keepout") == 1.0


def test_openroad_power_grid_parameter_missing_terminal_nets():
    task = power_grid.PowerGridTask()
    task.add_openroad_missingterminalnets('net1')
    assert task.get("var", "psm_allow_missing_terminal_nets") == ['net1']
    task.add_openroad_missingterminalnets(['net2', 'net3'], step='power_grid', index='1')
    assert task.get("var", "psm_allow_missing_terminal_nets", step='power_grid', index='1') == \
        ['net2', 'net3']
    assert task.get("var", "psm_allow_missing_terminal_nets") == ['net1']
    task.add_openroad_missingterminalnets('net4', clobber=True)
    assert task.get("var", "psm_allow_missing_terminal_nets") == ['net4']


def test_openroad_power_grid_parameter_pdn_enable():
    task = power_grid.PowerGridTask()
    task.set_openroad_pdnenable(True)
    assert task.get("var", "pdn_enable") is True
    task.set_openroad_pdnenable(False, step='power_grid', index='1')
    assert task.get("var", "pdn_enable", step='power_grid', index='1') is False
    assert task.get("var", "pdn_enable") is True


def test_openroad_rcx_bench_parameter_max_layer():
    task = pex.ORXBenchTask()
    task.set_openroad_benchmaxlayer('m1')
    assert task.get("var", "max_layer") == 'm1'
    task.set_openroad_benchmaxlayer('m2', step='rcx_bench', index='1')
    assert task.get("var", "max_layer", step='rcx_bench', index='1') == 'm2'
    assert task.get("var", "max_layer") == 'm1'


def test_openroad_rcx_bench_parameter_bench_length():
    task = pex.ORXBenchTask()
    task.set_openroad_benchlength(100.0)
    assert task.get("var", "bench_length") == 100.0
    task.set_openroad_benchlength(200.0, step='rcx_bench', index='1')
    assert task.get("var", "bench_length", step='rcx_bench', index='1') == 200.0
    assert task.get("var", "bench_length") == 100.0


def test_openroad_rcx_extract_parameter_corner():
    task = pex.ORXExtractTask()
    task.set_openroad_rcxcorner('test_corner')
    assert task.get("var", "corner") == 'test_corner'
    task.set_openroad_rcxcorner('other_corner', step='rcx_extract', index='1')
    assert task.get("var", "corner", step='rcx_extract', index='1') == 'other_corner'
    assert task.get("var", "corner") == 'test_corner'


##############################################################################
# PEX task setup
##############################################################################
def _rcx_project(design):
    """A project running the OpenRCX deck-generation flow (NOP for the PEX tool)."""
    from siliconcompiler import ASIC
    from siliconcompiler.targets import freepdk45_demo
    from siliconcompiler.tools.builtin.nop import NOPTask

    project = ASIC(design)
    project.add_fileset(["rtl", "sdc"])
    freepdk45_demo(project)
    project.set_flow(GenerateOpenRCXFlow(NOPTask()))
    return project


def _setup_node(project, step):
    """Run a node's setup() and return the configured task."""
    node = SchedulerNode(project, step, "0")
    with node.runtime():
        node.setup()
        return node.task


def test_openroad_init_floorplan_derives_corearea_from_coremargin(asic_gcd):
    # sc_init_floorplan.tcl only honors an explicit die area when a core area
    # goes with it, so a die area on its own used to silently fall back to
    # density driven sizing and discard the requested die.
    # https://github.com/siliconcompiler/siliconcompiler/issues/5217
    area = asic_gcd.constraint.area
    area.set_dieoutline(500, 500)
    assert area.get_coremargin() == 1.0, "freepdk45 must supply a core margin"

    require = _setup_node(asic_gcd, "floorplan.init").get("require")

    assert area.get_diearea(step="floorplan.init", index="0") == [(0.0, 0.0), (500.0, 500.0)]
    assert area.get_corearea(step="floorplan.init", index="0") == [(1.0, 1.0), (499.0, 499.0)]

    assert "constraint,area,diearea" in require
    assert "constraint,area,corearea" in require
    # The core area was computed from the margin, so the margin is part of the node.
    assert "constraint,area,coremargin" in require
    assert "constraint,area,density" not in require


def test_openroad_init_floorplan_derives_diearea_from_coremargin(asic_gcd):
    area = asic_gcd.constraint.area
    area.set_corearea([(10, 10), (410, 260)])

    require = _setup_node(asic_gcd, "floorplan.init").get("require")

    # The die grows around the core, the core keeps the coordinates it was given.
    assert area.get_diearea(step="floorplan.init", index="0") == [(9.0, 9.0), (411.0, 261.0)]
    assert area.get_corearea(step="floorplan.init", index="0") == [(10.0, 10.0), (410.0, 260.0)]

    assert "constraint,area,diearea" in require
    assert "constraint,area,corearea" in require
    assert "constraint,area,coremargin" in require


def test_openroad_init_floorplan_explicit_areas(asic_gcd):
    area = asic_gcd.constraint.area
    area.set_diearea([(0, 0), (500, 500)])
    area.set_corearea([(10, 10), (490, 490)])

    require = _setup_node(asic_gcd, "floorplan.init").get("require")

    assert area.get_diearea(step="floorplan.init", index="0") == [(0.0, 0.0), (500.0, 500.0)]
    assert area.get_corearea(step="floorplan.init", index="0") == [(10.0, 10.0), (490.0, 490.0)]

    assert "constraint,area,diearea" in require
    assert "constraint,area,corearea" in require
    # Nothing was derived, so the margin does not affect this node.
    assert "constraint,area,coremargin" not in require


def test_openroad_init_floorplan_derives_corearea_no_coremargin(asic_gcd):
    area = asic_gcd.constraint.area
    area.set_dieoutline(500, 500)
    area.unset("coremargin")

    require = _setup_node(asic_gcd, "floorplan.init").get("require")

    assert area.get_diearea(step="floorplan.init", index="0") == [(0.0, 0.0), (500.0, 500.0)]
    assert area.get_corearea(step="floorplan.init", index="0") == [(0.0, 0.0), (500.0, 500.0)]

    assert "constraint,area,diearea" in require
    assert "constraint,area,corearea" in require
    assert "constraint,area,coremargin" in require


@pytest.mark.parametrize("area,expect", [
    ("diearea", "die"),
    ("corearea", "core"),
])
def test_openroad_init_floorplan_rejects_polygon(asic_gcd, area, expect):
    # sc_init_floorplan.tcl floorplans the first two points of an outline, so a polygon has
    # to be refused until OpenROAD's polygonal floorplan support is usable.
    getattr(asic_gcd.constraint.area, f"set_{area}")(
        [(0, 0), (0, 200), (200, 200), (200, 100), (300, 100), (300, 0)])

    with pytest.raises(ValueError,
                       match=rf"^openroad does not support a polygonal {expect} area yet, "
                             rf"the {expect} area must be given as two points$"):
        _setup_node(asic_gcd, "floorplan.init")


def test_openroad_init_floorplan_density_sizing(asic_gcd):
    # Without a die or core area the floorplan is still sized from density.
    require = _setup_node(asic_gcd, "floorplan.init").get("require")

    assert asic_gcd.constraint.area.get_diearea(step="floorplan.init", index="0") == []
    assert asic_gcd.constraint.area.get_corearea(step="floorplan.init", index="0") == []

    assert "constraint,area,aspectratio" in require
    assert "constraint,area,density" in require
    assert "constraint,area,coremargin" in require
    assert "constraint,area,diearea" not in require


@pytest.mark.parametrize("task_cls", [
    pex.PEXBenchTask,
    pex.PEXBenchExtractTask,
    pex.ORXBenchTask,
    pex.ORXExtractTask,
    pex.CalibratePEXTask
])
def test_openroad_pex_task_make_docs(task_cls):
    # The Sphinx build calls make_docs() on every task listed in
    # docs/reference_manual/predef_modules/tools.rst, and nothing else in the
    # suite exercises it. A setup() that raises on an unset parameter therefore
    # breaks only the docs build - which no test catches without this.
    task = task_cls.make_docs()
    assert task.task()
    # The docs project is freepdk45, which ships an OpenRCX deck, so the
    # deck-required guards in these setups must be satisfied.
    assert task.get("output", step="<step>", index="<index>")


def test_openroad_rcx_extract_setup(gcd_design):
    project = _rcx_project(gcd_design)
    project.get("tool", "openroad", "task", "rcx_extract",
                field="schema").set_openroad_rcxcorner("cmax")

    task = _setup_node(project, "extract")
    assert [str(s) for s in task.get("script")] == ["pex/sc_rcx_extract.tcl"]
    assert task.get("input") == ["gcd.def.gz", "gcd.cmax.spef"]
    assert task.get("output") == ["gcd.cmax.rcx"]


def test_openroad_rcx_extract_setup_requires_corner(gcd_design):
    # The task names its SPEF input and RCX output after the corner. Unset, it
    # would declare '<top>.None.spef' and fail on a missing input file with no
    # hint at the real cause.
    project = _rcx_project(gcd_design)

    with pytest.raises(ValueError,
                       match=r"^rcx_extract requires the parasitic corner to be set "
                             r"\(see set_openroad_rcxcorner\)\.$"):
        _setup_node(project, "extract")


def test_openroad_pex_bench_extract_setup(asic_gcd):
    asic_gcd.set_flow(GeneratePEXEstimateFlow())
    task = _setup_node(asic_gcd, "extract")

    assert [str(s) for s in task.get("script")] == ["pex/sc_pex_extract.tcl"]
    # set_extraction_rules_file only exists from 26Q3-23; the base tool floor
    # (>=24Q3) would let the task launch and then fail on an unknown command.
    assert task.get("version") == [">=26Q3-23"]
    # Every corner the PDK ships a deck for, not just the scenario corners.
    assert task.get("var", "pex_corners") == ["typical"]
    assert task.get("output") == ["gcd.rclayer.csv"]
    require = task.get("require")
    assert "library,freepdk45,pdk,pexmodelfileset,openroad,typical" in require


def test_openroad_pex_bench_extract_setup_requires_openrcx(asic_gcd):
    asic_gcd.set_flow(GeneratePEXEstimateFlow())
    pdk = asic_gcd.get_library(str(asic_gcd.get("asic", "pdk")))
    for corner in pdk.getkeys("pdk", "pexmodelfileset", "openroad"):
        pdk.unset("pdk", "pexmodelfileset", "openroad", corner)

    with pytest.raises(ValueError,
                       match=r"^pex_bench_extract requires an OpenRCX extraction deck "
                             r"\(pdk 'pexmodelfileset' / 'openrcx' file\) to derive the "
                             r"estimate model\.$"):
        _setup_node(asic_gcd, "extract")


@pytest.mark.timeout(30)
def test_openroad_calibrate_pex_setup(asic_gcd):
    asic_gcd.set_flow(PEXCalibrateFlow())
    task = _setup_node(asic_gcd, "calibrate")

    assert [str(s) for s in task.get("script")] == ["apr/sc_calibrate_pex.tcl"]
    # Needs both the mcmm scene API (26Q1-1133) and set_extraction_rules_file.
    assert task.get("version") == [">=26Q3-23"]
    assert task.get("var", "pex_corners") == ["typical"]
    # Terminal analysis node: the calibration CSVs and no design views.
    assert task.get("output") == ["gcd.perlayer.csv", "gcd.nets.csv"]
    assert not task.get("var", "ord_enable_images")


@pytest.mark.timeout(30)
def test_openroad_calibrate_pex_setup_requires_openrcx(asic_gcd):
    asic_gcd.set_flow(PEXCalibrateFlow())
    pdk = asic_gcd.get_library(str(asic_gcd.get("asic", "pdk")))
    for corner in pdk.getkeys("pdk", "pexmodelfileset", "openroad"):
        pdk.unset("pdk", "pexmodelfileset", "openroad", corner)

    with pytest.raises(ValueError,
                       match=r"^calibrate_pex requires an OpenRCX extraction deck "
                             r"\(pdk 'pexmodelfileset' / 'openrcx' file\) to build the golden "
                             r"reference\.$"):
        _setup_node(asic_gcd, "calibrate")


@pytest.mark.timeout(30)
def test_openroad_calibrate_pex_hashes_rccorrection(asic_gcd):
    # Recalibrating must invalidate cached nodes, so the PDK's rccorrection has
    # to be a required key (part of the node hash) like the rclayer it scales.
    asic_gcd.set_flow(PEXCalibrateFlow())
    pdk = asic_gcd.get_library(str(asic_gcd.get("asic", "pdk")))
    pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.5)

    require = _setup_node(asic_gcd, "calibrate").get("require")
    assert "library,freepdk45,tool,openroad,rccorrection" in require
    assert "library,freepdk45,tool,openroad,rclayer" in require


def _gf180_project(design=None, flow=None):
    """A gf180 ASIC project - a multi-corner, filler-cell PDK.

    Defaults to the calibration utility's fileless bench design; pass a real
    design and/or a flow when the test needs them.
    """
    from siliconcompiler import ASIC
    from siliconcompiler.targets import gf180_demo

    if design is None:
        design = pc._bench_design()
    project = ASIC(design)
    project.add_fileset(["rtl"] + (["sdc"] if design.has_fileset("sdc") else []))
    gf180_demo(project)
    if flow:
        project.set_flow(flow)
    return project


def test_openroad_pex_bench_extract_setup_multicorner(gcd_design):
    # freepdk45 ships exactly one pex corner, so a multi-corner PDK is the only
    # way to check that the bench characterizes *every* corner the deck ships
    # rather than one of them.
    project = _gf180_project(gcd_design, GeneratePEXEstimateFlow())
    pdk = project.get_library(str(project.get("asic", "pdk")))
    deck_corners = set(pdk.getkeys("pdk", "pexmodelfileset", "openroad"))
    assert len(deck_corners) > 1, "gf180 fixture must ship more than one pex corner"

    task = _setup_node(project, "extract")
    assert set(task.get("var", "pex_corners")) == deck_corners


def test_openroad_pex_bench_extract_skips_corner_without_a_deck(gcd_design):
    # The bench characterizes the corners the *PDK* declares, so a declared
    # corner whose filesets carry no OpenRCX deck (a Tcl-only estimate model,
    # say) is skipped rather than demanded. Contrast the corners a user wires to
    # a timing scenario, which are never dropped - see the calibrate and
    # write_data tests below.
    project = _gf180_project(gcd_design, GeneratePEXEstimateFlow())
    pdk = project.get_library(str(project.get("asic", "pdk")))
    pdk.set("pdk", "pexmodelfileset", "openroad", "wst", ["openroad.pex.deckless"])

    task = _setup_node(project, "extract")
    assert set(task.get("var", "pex_corners")) == {"bst", "typ"}


@pytest.mark.timeout(30)
def test_openroad_calibrate_pex_requires_a_deck_for_every_scenario_corner(gcd_design):
    # A timing scenario's pex corner is a deliberate user choice, so a corner
    # with no golden reference is named rather than quietly excluded - excluding
    # it would emit a calibration that silently omits the corner.
    project = _gf180_project(gcd_design, PEXCalibrateFlow())
    pdk = project.get_library(str(project.get("asic", "pdk")))
    pdk.unset("pdk", "pexmodelfileset", "openroad", "wst")

    with pytest.raises(
            ValueError,
            match=r"^calibrate_pex cannot calibrate pex corner\(s\) wst: the PDK ships no "
                  r"OpenRCX extraction deck \(pdk 'pexmodelfileset' / 'openrcx' file\) for "
                  r"them\. Add a deck for these corners or point the timing scenarios at "
                  r"corners that have one\.$"):
        _setup_node(project, "calibrate")


def test_openroad_write_data_extracts_every_scenario_corner(gcd_design):
    # gf180 wires three timing scenarios to three distinct pex corners, each with
    # its own deck. All three must be extracted: dropping one would leave that
    # scenario's STA reading no SPEF at all.
    project = _gf180_project(gcd_design, ASICFlow())
    task = _setup_node(project, "write.views")

    assert task.get("var", "pex_corners") == ["bst", "typ", "wst"]
    assert task.get("var", "write_spef")
    assert [out for out in task.get("output") if out.endswith(".spef")] == \
        ["gcd.bst.spef", "gcd.typ.spef", "gcd.wst.spef"]


def test_openroad_write_data_requires_a_deck_for_every_scenario_corner(gcd_design):
    # Same rule as calibrate_pex: a scenario corner without a deck is named, not
    # silently dropped from the SPEF set.
    project = _gf180_project(gcd_design, ASICFlow())
    pdk = project.get_library(str(project.get("asic", "pdk")))
    pdk.unset("pdk", "pexmodelfileset", "openroad", "wst")

    with pytest.raises(
            ValueError,
            match=r"^write_data cannot extract pex corner 'wst': the PDK ships no OpenRCX "
                  r"extraction deck \(pdk 'pexmodelfileset' / 'openrcx' file\) for it\. Add a "
                  r"deck for this corner, point the timing scenario at a corner that has one, "
                  r"or disable write_spef\.$"):
        _setup_node(project, "write.views")


def test_openroad_write_data_no_deck_at_all_disables_spef(gcd_design):
    # A PDK that ships no deck at all cannot write SPEF; write_spef defaults on,
    # so it is turned off rather than failing every run on such a PDK.
    project = _gf180_project(gcd_design, ASICFlow())
    pdk = project.get_library(str(project.get("asic", "pdk")))
    for corner in list(pdk.getkeys("pdk", "pexmodelfileset", "openroad")):
        pdk.unset("pdk", "pexmodelfileset", "openroad", corner)

    task = _setup_node(project, "write.views")
    assert not task.get("var", "write_spef")
    assert not task.get("var", "use_spef")
    assert not [out for out in task.get("output") if out.endswith(".spef")]


@pytest.mark.timeout(30)
def test_openroad_calibrate_pex_keeps_cell_required_keys(gcd_design):
    # CalibratePEXTask suppresses the standard PNR outputs. The library cell
    # lists the APR preamble reads must survive that override, or a change to a
    # filler/tap list would not invalidate the node. (gf180 rather than freepdk45
    # because it is the fixture PDK that actually declares those cell lists.)
    def cell_keys(flow, step):
        project = _gf180_project(gcd_design, flow)
        return {key for key in _setup_node(project, step).get("require")
                if ",asic,cells," in key}

    calibrate_keys = cell_keys(PEXCalibrateFlow(), "calibrate")
    apr_keys = cell_keys(ASICFlow(), "place.detailed")
    assert apr_keys, "gf180 fixture must declare some asic,cells keys"
    assert calibrate_keys == apr_keys


def test_openroad_rdlroute_parameter_rdlroute():
    task = rdlroute.RDLRouteTask()
    task.add_openroad_rdlroute('route1')
    assert task.get("var", "rdlroute") == ['route1']
    task.add_openroad_rdlroute('route2', step='rdlroute', index='1')
    assert task.get("var", "rdlroute", step='rdlroute', index='1') == ['route2']
    assert task.get("var", "rdlroute") == ['route1']
    task.add_openroad_rdlroute('route3', clobber=True)
    assert task.get("var", "rdlroute") == ['route3']


def test_openroad_rdlroute_parameter_add_fill():
    task = rdlroute.RDLRouteTask()
    task.set_openroad_addfill(True)
    assert task.get("var", "fin_add_fill") is True
    task.set_openroad_addfill(False, step='rdlroute', index='1')
    assert task.get("var", "fin_add_fill", step='rdlroute', index='1') is False
    assert task.get("var", "fin_add_fill") is True


def test_openroad_repair_design_parameter_tie_separation():
    task = repair_design.RepairDesignTask()
    task.set_openroad_tieseparation(10.0)
    assert task.get("var", "ifp_tie_separation") == 10.0
    task.set_openroad_tieseparation(20.0, step='repair_design', index='1')
    assert task.get("var", "ifp_tie_separation", step='repair_design', index='1') == 20.0
    assert task.get("var", "ifp_tie_separation") == 10.0


def test_openroad_repair_design_parameter_buffer_inputs():
    task = repair_design.RepairDesignTask()
    task.set_openroad_bufferinputs(True)
    assert task.get("var", "rsz_buffer_inputs") is True
    task.set_openroad_bufferinputs(False, step='repair_design', index='1')
    assert task.get("var", "rsz_buffer_inputs", step='repair_design', index='1') is False
    assert task.get("var", "rsz_buffer_inputs") is True


def test_openroad_repair_design_parameter_buffer_outputs():
    task = repair_design.RepairDesignTask()
    task.set_openroad_bufferoutputs(True)
    assert task.get("var", "rsz_buffer_outputs") is True
    task.set_openroad_bufferoutputs(False, step='repair_design', index='1')
    assert task.get("var", "rsz_buffer_outputs", step='repair_design', index='1') is False
    assert task.get("var", "rsz_buffer_outputs") is True


def test_openroad_repair_timing_parameter_skip_drv_repair():
    task = repair_timing.RepairTimingTask()
    task.set_openroad_skipdrvrepair(True)
    assert task.get("var", "rsz_skip_drv_repair") is True
    task.set_openroad_skipdrvrepair(False, step='repair_timing', index='1')
    assert task.get("var", "rsz_skip_drv_repair", step='repair_timing', index='1') is False
    assert task.get("var", "rsz_skip_drv_repair") is True


def test_openroad_repair_timing_parameter_skip_setup_repair():
    task = repair_timing.RepairTimingTask()
    task.set_openroad_skipsetuprepair(True)
    assert task.get("var", "rsz_skip_setup_repair") is True
    task.set_openroad_skipsetuprepair(False, step='repair_timing', index='1')
    assert task.get("var", "rsz_skip_setup_repair", step='repair_timing', index='1') is False
    assert task.get("var", "rsz_skip_setup_repair") is True


def test_openroad_repair_timing_parameter_skip_hold_repair():
    task = repair_timing.RepairTimingTask()
    task.set_openroad_skipholdrepair(True)
    assert task.get("var", "rsz_skip_hold_repair") is True
    task.set_openroad_skipholdrepair(False, step='repair_timing', index='1')
    assert task.get("var", "rsz_skip_hold_repair", step='repair_timing', index='1') is False
    assert task.get("var", "rsz_skip_hold_repair") is True


def test_openroad_repair_timing_parameter_skip_recover_power():
    task = repair_timing.RepairTimingTask()
    task.set_openroad_skiprecoverpower(True)
    assert task.get("var", "rsz_skip_recover_power") is True
    task.set_openroad_skiprecoverpower(False, step='repair_timing', index='1')
    assert task.get("var", "rsz_skip_recover_power", step='repair_timing', index='1') is False
    assert task.get("var", "rsz_skip_recover_power") is True


# ----------------------------------------------------------------------
# DetailedRouteAntennaRepairTask
# ----------------------------------------------------------------------


def test_openroad_detailed_route_antenna_repair_identity():
    """Its own node and task, so route.detailed reports pure routing results and the
    diode/reroute cost is attributable on its own."""
    task = detailed_route.DetailedRouteAntennaRepairTask()
    assert task.task() == "detailed_route_antenna_repair"
    assert task.tool() == "openroad"
    assert task.task() != detailed_route.DetailedRouteTask().task()


def test_openroad_detailed_route_antenna_repair_parameters():
    task = detailed_route.DetailedRouteAntennaRepairTask()
    assert task.get("var", "ant_check") is True
    assert task.get("var", "ant_repair") is True
    # ORFS passes no -ratio_margin in either antenna loop.
    assert task.get("var", "ant_margin") == 0
    # ORFS MAX_REPAIR_ANTENNAS_ITER_DRT.
    assert task.get("var", "ant_reroute_iterations") == 5
    # ant_iterations bounds a single repair_antennas call and is a pre-route knob,
    # so it deliberately stays off this task.
    assert not task.valid("var", "ant_iterations")


def test_openroad_detailed_route_antenna_repair_parameter_reroute_iterations():
    task = detailed_route.DetailedRouteAntennaRepairTask()
    task.set_openroad_antrerouteiterations(3)
    assert task.get("var", "ant_reroute_iterations") == 3
    task.set_openroad_antrerouteiterations(1, step='detailed', index='1')
    assert task.get("var", "ant_reroute_iterations", step='detailed', index='1') == 1
    assert task.get("var", "ant_reroute_iterations") == 3
    # ant_repair is the off switch, so 0 is not a value the schema accepts.
    message = "error while setting [var,ant_reroute_iterations]: 0 is not in range: 1.."
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        task.set_openroad_antrerouteiterations(0)


def test_openroad_detailed_route_antenna_repair_reroutes_like_detailed_route():
    """The reroute has to use the same detailed router settings the initial route
    used, which is why the task derives from DetailedRouteTask."""
    task = detailed_route.DetailedRouteAntennaRepairTask()
    assert isinstance(task, detailed_route.DetailedRouteTask)
    for var in ("drt_disable_via_gen", "drt_process_node", "drt_report_interval"):
        assert task.valid("var", var), var
    # The loop brackets itself with remove_fillers/sc_insert_fillers.
    assert task.valid("var", "dpl_use_decap_fillers")


def test_openroad_detailed_route_has_no_antenna_vars():
    """Antenna repair moved out of detailed_route into its own node."""
    task = detailed_route.DetailedRouteTask()
    for var in ("ant_check", "ant_repair", "ant_margin", "ant_reroute_iterations"):
        assert not task.valid("var", var), var


def test_openroad_detailed_route_antenna_repair_skips_when_disabled(asic_gcd):
    detailed_route.DetailedRouteAntennaRepairTask.find_task(asic_gcd).set_openroad_antcheck(False)

    node = SchedulerNode(asic_gcd, "route.detailed_antenna_repair", "0")
    with node.runtime():
        with pytest.raises(TaskSkip, match="^antenna repair is disabled$"):
            node.task.setup()
        assert node.setup() is False


def test_openroad_detailed_route_antenna_repair_runs_by_default(asic_gcd):
    node = SchedulerNode(asic_gcd, "route.detailed_antenna_repair", "0")
    with node.runtime():
        assert node.setup() is True


def test_openroad_detailed_route_antenna_repair_uses_its_own_script(asic_gcd):
    """set_script does not clobber by default, so without an explicit clobber the
    parent's script would win and the node would re-run a full detailed route."""
    repair = _setup_node(asic_gcd, "route.detailed_antenna_repair")
    route = _setup_node(asic_gcd, "route.detailed")

    assert repair.get("script") == ["apr/sc_detailed_route_antenna_repair.tcl"]
    assert route.get("script") == ["apr/sc_detailed_route.tcl"]


def test_openroad_antenna_repair_parameters_unchanged():
    """ant_check/ant_repair moved from AntennaRepairTask up into the shared mixin;
    the task's own schema keys and defaults must be unchanged by that move."""
    task = antenna_repair.AntennaRepairTask()
    assert task.get("var", "ant_check") is True
    assert task.get("var", "ant_repair") is True
    assert task.get("var", "ant_margin") == 0
    assert task.get("var", "ant_iterations") == 3


def test_openroad_repair_timing_parameter_skip_wns_repair():
    task = repair_timing.RepairTimingTask()
    # Skipped by default: the pass only applies once global routing exists.
    assert task.get("var", "rsz_skip_wns_repair") is True
    task.set_openroad_skipwnsrepair(False)
    assert task.get("var", "rsz_skip_wns_repair") is False
    task.set_openroad_skipwnsrepair(True, step='repair_timing', index='1')
    assert task.get("var", "rsz_skip_wns_repair", step='repair_timing', index='1') is True
    assert task.get("var", "rsz_skip_wns_repair") is False


def test_openroad_repair_timing_parameter_wns_sequence():
    task = repair_timing.RepairTimingTask()
    assert task.get("var", "rsz_wns_sequence") == ["vt_swap", "reroute"]
    task.add_openroad_rszwnssequence(["sizeup"], clobber=True)
    assert task.get("var", "rsz_wns_sequence") == ["sizeup"]
    task.add_openroad_rszwnssequence("vt_swap", step='repair_timing', index='1', clobber=True)
    assert task.get("var", "rsz_wns_sequence", step='repair_timing', index='1') == ["vt_swap"]
    assert task.get("var", "rsz_wns_sequence") == ["sizeup"]


def test_openroad_repair_timing_parameter_wns_sequence_appends_to_default():
    """This is the one move list with a non-empty default, so adding extends it.

    Replacing the sequence needs clobber. Pinned because the asymmetry with
    rsz_sequence and rsz_phases -- both empty by default, where add and set coincide
    on a fresh task -- is easy to trip over.
    """
    task = repair_timing.RepairTimingTask()
    task.add_openroad_rszwnssequence("sizeup")
    assert task.get("var", "rsz_wns_sequence") == ["vt_swap", "reroute", "sizeup"]


# ----------------------------------------------------------------------
# PostRouteRepairTimingTask
# ----------------------------------------------------------------------


def test_openroad_post_route_repair_timing_identity():
    """A distinct task() name is required: the schema namespace is keyed on it, so
    sharing "repair_timing" with the cts node would let the two clobber each
    other's setup()-time defaults."""
    task = repair_timing.PostRouteRepairTimingTask()
    assert task.task() == "post_route_repair_timing"
    assert task.tool() == "openroad"
    assert task.task() != repair_timing.RepairTimingTask().task()


def test_openroad_post_route_repair_timing_parameter_enable():
    task = repair_timing.PostRouteRepairTimingTask()
    assert task.get("var", "rsz_enable") is False
    task.set_openroad_rszenable(True)
    assert task.get("var", "rsz_enable") is True
    task.set_openroad_rszenable(False, step='repair_timing', index='1')
    assert task.get("var", "rsz_enable", step='repair_timing', index='1') is False
    assert task.get("var", "rsz_enable") is True


def test_openroad_post_route_repair_timing_has_grt_setup():
    """The node runs incremental global routing through sc_detailed_placement, which
    needs the routing layers applied via load_grt_setup."""
    task = repair_timing.PostRouteRepairTimingTask()
    assert task.valid("var", "grt_signal_min_layer")
    # The plain cts node deliberately does not carry the GRT setup.
    assert not repair_timing.RepairTimingTask().valid("var", "grt_signal_min_layer")


def test_openroad_post_route_repair_timing_stage_defaults():
    """The ORFS-equivalent defaults for this stage are declared via _default_*
    overrides, so they are visible on the class without running setup()."""
    task = repair_timing.PostRouteRepairTimingTask()

    assert task.get("var", "rsz_skip_wns_repair") is False
    assert task.get("var", "rsz_skip_recover_power") is True
    assert task.get("var", "rsz_match_cell_footprint") is True


def test_openroad_post_route_repair_timing_defaults_do_not_leak():
    """The post-route defaults must not move the cts repair_timing node's."""
    cts = repair_timing.RepairTimingTask()

    assert cts.get("var", "rsz_skip_wns_repair") is True
    assert cts.get("var", "rsz_match_cell_footprint") is False
    assert cts.get("var", "rsz_skip_recover_power") is False


def test_openroad_post_route_repair_timing_loads_grt_setup(asic_gcd):
    """Incremental global routing needs the routing layers applied, which
    load_grt_setup gates. That one is still set during setup()."""
    repair_timing.PostRouteRepairTimingTask.find_task(asic_gcd).set_openroad_rszenable(True)

    assert _setup_node(asic_gcd, "route.repair_timing").get("var", "load_grt_setup") is True
    assert _setup_node(asic_gcd, "cts.repair_timing").get("var", "load_grt_setup") is False


def test_openroad_post_route_repair_timing_user_value_wins(asic_gcd):
    """The stage defaults are ordinary defvalues, so an explicit setting overrides
    them. The opt-in design depends on this."""
    task = repair_timing.PostRouteRepairTimingTask.find_task(asic_gcd)
    task.set_openroad_rszenable(True)
    task.set_openroad_skipwnsrepair(True)
    task.set_openroad_skiprecoverpower(False)
    task.set_openroad_rszmatchcellfootprint(False)

    task = _setup_node(asic_gcd, "route.repair_timing")
    assert task.get("var", "rsz_skip_wns_repair") is True
    assert task.get("var", "rsz_skip_recover_power") is False
    assert task.get("var", "rsz_match_cell_footprint") is False


def test_openroad_post_route_repair_timing_skips_when_disabled(asic_gcd):
    """rsz_enable cannot change after setup, so the node is dropped there rather
    than in pre_process, and no work directory is built for it."""
    node = SchedulerNode(asic_gcd, "route.repair_timing", "0")
    with node.runtime():
        assert node.task.get("var", "rsz_enable") is False
        with pytest.raises(TaskSkip, match="^post route timing repair is disabled$"):
            node.task.setup()
        # setup() is what the scheduler catches, so it must not reach pre_process.
        assert node.setup() is False


def test_openroad_post_route_repair_timing_runs_when_enabled(asic_gcd):
    repair_timing.PostRouteRepairTimingTask.find_task(asic_gcd).set_openroad_rszenable(True)

    node = SchedulerNode(asic_gcd, "route.repair_timing", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get("var", "rsz_enable") is True


def test_openroad_screenshot_parameter_vertical_resolution():
    task = screenshot.ScreenshotTask()
    task.set_openroad_verticalresolution(1024)
    assert task.get("var", "show_vertical_resolution") == 1024
    task.set_openroad_verticalresolution(2048, step='screenshot', index='1')
    assert task.get("var", "show_vertical_resolution", step='screenshot', index='1') == 2048
    assert task.get("var", "show_vertical_resolution") == 1024


def test_openroad_screenshot_parameter_include_report_images():
    task = screenshot.ScreenshotTask()
    task.set_openroad_includereportimages(True)
    assert task.get("var", "include_report_images") is True
    task.set_openroad_includereportimages(False, step='screenshot', index='1')
    assert task.get("var", "include_report_images", step='screenshot', index='1') is False
    assert task.get("var", "include_report_images") is True


# ----------------------------------------------------------------------
# OpenTask: identity + file copying
# ----------------------------------------------------------------------


def test_openroad_open_basics():
    task = openroad_open.OpenTask()
    assert task.task() == "open"
    assert task.tool() == "openroad"
    assert task.get_supported_task_extentions() == ["odb", "def", "vg"]
    assert task.has_breakpoint() is True


@pytest.mark.parametrize("task_cls", [
    _apr.APRTask,
    openroad_open.OpenTask,
    openroad_show.ShowTask,
    screenshot.ScreenshotTask,
    init_floorplan.InitFloorplanTask,
    global_placement.GlobalPlacementTask,
    global_route.GlobalRouteTask,
    repair_design.RepairDesignTask,
    repair_timing.RepairTimingTask,
    repair_timing.PostRouteRepairTimingTask,
    macro_placement.MacroPlacementTask,
    metrics.MetricsTask,
    write_data.WriteViewsTask,
])
def test_openroad_enablehier_default_false(task_cls):
    """enablehier defaults to False for APR-derived tasks."""
    assert task_cls().get("var", "enablehier") is False


def test_openroad_web_enablehier_default_true():
    """WebTask flips the enablehier default to True."""
    assert openroad_show.WebTask().get("var", "enablehier") is True


def test_openroad_show_supports_def():
    """ShowTask inherits the open task's def/odb/vg extension support."""
    task = openroad_show.ShowTask()
    assert "def" in task.get_supported_task_extentions()
    assert "odb" in task.get_supported_task_extentions()


def test_openroad_screenshot_supports_def():
    """ScreenshotTask inherits the open task's def/odb/vg extension support."""
    task = screenshot.ScreenshotTask()
    assert "def" in task.get_supported_task_extentions()
    assert "odb" in task.get_supported_task_extentions()


def _set_open_flow(project, task_cls=openroad_open.OpenTask):
    """Replace the project's flow with a single-node flow holding ``task_cls``."""
    flow = Flowgraph("openflow")
    flow.node("open", task_cls())
    project.set_flow(flow)


def _populate_outputs(project, step, index, files):
    """Create a fake ``outputs/`` for (step, index) and write ``files`` into it."""
    outputs = os.path.join(workdir(project, step=step, index=index), "outputs")
    os.makedirs(outputs, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(outputs, name), "w") as fh:
            fh.write(content)
    return outputs


@pytest.fixture
def open_project(asic_gcd, tmp_path, monkeypatch):
    """A project rooted under tmp_path with a single OpenTask node installed."""
    monkeypatch.chdir(tmp_path)
    asic_gcd.option.set_builddir(str(tmp_path / "build"))
    _set_open_flow(asic_gcd)
    return asic_gcd


def _run_copy(project, *,
              show_step, show_index, show_type,
              show_path, show_job="job0",
              load_sdcs=None):
    """Drive ``_copy_show_files`` on a SchedulerNode-bound OpenTask in cwd."""
    node = SchedulerNode(project, "open", "0")
    with node.runtime():
        task = node.task
        task.set("var", "showfilepath", show_path)
        task.set("var", "showfiletype", show_type)
        task.set("var", "shownode", (show_job, show_step, show_index))
        if load_sdcs is not None:
            task.set_openroad_loadsdcs(load_sdcs)

        os.makedirs("inputs", exist_ok=True)
        task._copy_show_files()


def test_openroad_open_copy_no_showfilepath(open_project):
    """No showfilepath => nothing is copied."""
    node = SchedulerNode(open_project, "open", "0")
    with node.runtime():
        os.makedirs("inputs", exist_ok=True)
        node.task._copy_show_files()

    assert os.listdir("inputs") == []


def test_openroad_open_copy_basic_def(open_project):
    """A def supplied via showfilepath is copied to inputs/."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def)

    assert os.path.exists("inputs/gcd.def")
    with open("inputs/gcd.def") as fh:
        assert fh.read() == "def-content"


def test_openroad_open_copy_with_vg_companion(open_project):
    """Opening a def pulls in a sibling vg netlist for -hier linking."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.vg": "verilog-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def)

    assert os.path.exists("inputs/gcd.def")
    assert os.path.exists("inputs/gcd.vg")
    with open("inputs/gcd.vg") as fh:
        assert fh.read() == "verilog-content"


def test_openroad_open_copy_prefers_gz_vg(open_project):
    """vg.gz is preferred over plain vg when both exist alongside the def."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.vg": "plain-vg",
        "gcd.vg.gz": "gz-vg",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def)

    assert os.path.exists("inputs/gcd.vg.gz")
    assert not os.path.exists("inputs/gcd.vg")


def test_openroad_open_copy_skips_vg_for_odb(open_project):
    """Opening an odb does not pull in a vg companion (odb is self-contained)."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.odb": "odb-content",
        "gcd.vg": "vg-content",
    })
    src_odb = os.path.join(src_outputs, "gcd.odb")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="odb", show_path=src_odb)

    assert os.path.exists("inputs/gcd.odb")
    assert not os.path.exists("inputs/gcd.vg")


def test_openroad_open_copy_with_sdc(open_project):
    """A sibling generic <top>.sdc is copied when load_sdcs is enabled (default)."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.sdc": "sdc-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def)

    assert os.path.exists("inputs/gcd.sdc")
    with open("inputs/gcd.sdc") as fh:
        assert fh.read() == "sdc-content"


def test_openroad_open_copy_load_sdcs_disabled(open_project):
    """Disabling load_sdcs suppresses sdc copying."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.sdc": "sdc-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def,
              load_sdcs=False)

    assert os.path.exists("inputs/gcd.def")
    assert not os.path.exists("inputs/gcd.sdc")


def test_openroad_open_copy_cross_job(open_project):
    """A shownode pointing at a different jobname resolves via project history."""
    open_project.option.set_jobname("rtl2gds")
    open_project._record_history()
    open_project.option.set_jobname("job0")
    _set_open_flow(open_project)

    history = open_project.history("rtl2gds")
    src_outputs = _populate_outputs(history, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.vg": "vg-content",
        "gcd.sdc": "sdc-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def,
              show_job="rtl2gds")

    assert os.path.exists("inputs/gcd.def")
    assert os.path.exists("inputs/gcd.vg")
    assert os.path.exists("inputs/gcd.sdc")


def test_openroad_open_copy_unknown_job_falls_back(open_project):
    """If the referenced jobname has no history entry, fall back to the live project."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    _run_copy(open_project,
              show_step="route.detailed", show_index="0",
              show_type="def", show_path=src_def,
              show_job="does-not-exist")

    assert os.path.exists("inputs/gcd.def")


def test_openroad_open_copy_no_shownode(open_project):
    """Without a shownode, only the showfilepath is copied — no companion lookup."""
    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.vg": "vg-content",
        "gcd.sdc": "sdc-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    node = SchedulerNode(open_project, "open", "0")
    with node.runtime():
        task = node.task
        task.set("var", "showfilepath", src_def)
        task.set("var", "showfiletype", "def")
        os.makedirs("inputs", exist_ok=True)
        task._copy_show_files()

    assert os.path.exists("inputs/gcd.def")
    assert not os.path.exists("inputs/gcd.vg")
    assert not os.path.exists("inputs/gcd.sdc")


@pytest.mark.parametrize("task_cls", [
    openroad_show.ShowTask,
    screenshot.ScreenshotTask,
])
def test_openroad_show_screenshot_inherit_copy(open_project, task_cls):
    """ShowTask and ScreenshotTask inherit the OpenTask file-copy behavior."""
    _set_open_flow(open_project, task_cls=task_cls)

    src_outputs = _populate_outputs(open_project, "route.detailed", "0", {
        "gcd.def": "def-content",
        "gcd.vg": "vg-content",
        "gcd.sdc": "sdc-content",
    })
    src_def = os.path.join(src_outputs, "gcd.def")

    node = SchedulerNode(open_project, "open", "0")
    with node.runtime():
        task = node.task
        task.set("var", "showfilepath", src_def)
        task.set("var", "showfiletype", "def")
        task.set("var", "shownode", ("job0", "route.detailed", "0"))
        os.makedirs("inputs", exist_ok=True)
        task._copy_show_files()

    assert os.path.exists("inputs/gcd.def")
    assert os.path.exists("inputs/gcd.vg")
    assert os.path.exists("inputs/gcd.sdc")


# ----------------------------------------------------------------------
# Regression guard: every OpenROAD open/show/screenshot variant must end up
# pointing at sc_open.tcl with the right sc_do_screenshot value. The original
# bug here was that ShowTask/ScreenshotTask called set_script("sc_show.tcl")
# *after* OpenTask.setup() had already set sc_open.tcl, but set_script defaults
# to clobber=False so the override was a silent no-op and the screenshot path
# ran the wrong script.
# ----------------------------------------------------------------------


@pytest.mark.parametrize("task_cls", [
    openroad_open.OpenTask,
    openroad_show.ShowTask,
    openroad_show.WebTask,
    screenshot.ScreenshotTask,
])
def test_openroad_open_script_is_sc_open(asic_gcd, tmp_path, monkeypatch, task_cls):
    """All OpenROAD open variants must end up running sc_open.tcl after full setup.

    Regression guard: previously ShowTask/ScreenshotTask called
    ``set_script("sc_show.tcl")`` after OpenTask.setup() had already set
    ``sc_open.tcl``. Because ``set_script`` defaults to ``clobber=False``, the
    second call was a silent no-op and the screenshot path ran the wrong
    script. This test ensures every variant resolves to ``sc_open.tcl``.
    """
    monkeypatch.chdir(tmp_path)
    asic_gcd.option.set_builddir(str(tmp_path / "build"))

    flow = Flowgraph(f"openflow_{task_cls.__name__.lower()}")
    flow.node("open", task_cls())
    asic_gcd.set_flow(flow)

    node = SchedulerNode(asic_gcd, "open", "0")
    with node.runtime():
        # project.show sets showfilepath before setup runs.
        node.task.set("var", "showfilepath", "/tmp/dummy.def")
        node.task.set("var", "showfiletype", "def")
        node.setup()

        scripts = [str(s) for s in node.task.get("script")]
        assert any(s.endswith("sc_open.tcl") for s in scripts), \
            f"{task_cls.__name__}: expected sc_open.tcl, got {scripts}"
        assert all(not s.endswith("sc_show.tcl") for s in scripts), \
            f"{task_cls.__name__}: sc_show.tcl should no longer be referenced; got {scripts}"


def test_openroad_sc_open_tcl_has_screenshot_block(scroot):
    """sc_open.tcl must source the screenshot block guarded by sc_do_screenshot."""
    script_path = os.path.join(scroot, "siliconcompiler", "tools", "openroad",
                               "scripts", "sc_open.tcl")
    with open(script_path) as fh:
        body = fh.read()
    assert "sc_do_screenshot" in body, \
        "sc_open.tcl must reference sc_do_screenshot to trigger screenshot rendering"
    assert "screenshot.tcl" in body, \
        "sc_open.tcl must source common/screenshot.tcl when sc_do_screenshot is true"


def test_openroad_sc_show_tcl_removed(scroot):
    """sc_show.tcl was consolidated into sc_open.tcl and should no longer exist."""
    script_path = os.path.join(scroot, "siliconcompiler", "tools", "openroad",
                               "scripts", "sc_show.tcl")
    assert not os.path.exists(script_path), \
        f"{script_path} should be removed; sc_open.tcl is now the single entry script"


# ---------------------------------------------------------------------------
# OpenRCX per-corner rules merge utility (utils/rcx_merge.py)
# ---------------------------------------------------------------------------
def _single_corner(layer_count, corner_tag):
    """Build a minimal single-corner OpenRCX rules file body."""
    return (
        "Extraction Rules for OpenRCX\n"
        "\n"
        "DIAGMODEL ON\n"
        "\n"
        f"LayerCount {layer_count}\n"
        "DensityRate 1  0\n"
        "\n"
        "DensityModel 0\n"
        "\n"
        "Metal 1 RESOVER\n"
        f"WIDTH Table 1 entries:  0.17 {corner_tag}\n"
        "END DensityModel 0\n"
    )


def _write_rules(name, contents):
    with open(name, "w") as fid:
        fid.write(contents)
    return name


def test_rcx_merge_three_corners():
    files = [
        _write_rules("min.rules", _single_corner(6, "MIN")),
        _write_rules("typ.rules", _single_corner(6, "TYP")),
        _write_rules("max.rules", _single_corner(6, "MAX")),
    ]

    merged = merge_openrcx_rules(files)

    expected = (
        "Extraction Rules for OpenRCX\n"
        "\n"
        "DIAGMODEL ON\n"
        "\n"
        "LayerCount 6\n"
        "DensityRate 3  0 1 2\n"
        "\n"
        "DensityModel 0\n"
        "\n"
        "Metal 1 RESOVER\n"
        "WIDTH Table 1 entries:  0.17 MIN\n"
        "END DensityModel 0\n"
        "\n"
        "DensityModel 1\n"
        "\n"
        "Metal 1 RESOVER\n"
        "WIDTH Table 1 entries:  0.17 TYP\n"
        "END DensityModel 1\n"
        "\n"
        "DensityModel 2\n"
        "\n"
        "Metal 1 RESOVER\n"
        "WIDTH Table 1 entries:  0.17 MAX\n"
        "END DensityModel 2\n"
    )

    assert merged == expected


def test_rcx_merge_single_corner():
    files = [_write_rules("typ.rules", _single_corner(2, "TYP"))]

    merged = merge_openrcx_rules(files)

    assert "DensityRate 1  0\n" in merged
    assert merged.count("DensityModel 0") == 2  # begin + end marker
    assert "END DensityModel 0\n" in merged


def test_rcx_merge_body_is_copied_verbatim():
    files = [
        _write_rules("min.rules", _single_corner(6, "MIN")),
        _write_rules("typ.rules", _single_corner(6, "TYP")),
    ]

    merged = merge_openrcx_rules(files)

    # Each corner keeps its own distinct payload line.
    assert "WIDTH Table 1 entries:  0.17 MIN" in merged
    assert "WIDTH Table 1 entries:  0.17 TYP" in merged

    # Corner indices are assigned in file order.
    assert merged.index("0.17 MIN") < merged.index("0.17 TYP")


def test_rcx_merge_corner_names_emit_documentation_line():
    files = [
        _write_rules("min.rules", _single_corner(6, "MIN")),
        _write_rules("typ.rules", _single_corner(6, "TYP")),
        _write_rules("max.rules", _single_corner(6, "MAX")),
    ]

    merged = merge_openrcx_rules(files, corner_names=["min", "typ", "max"])

    assert "Corners 3 :  min typ max\n" in merged


def test_rcx_merge_mismatched_layer_count_raises():
    files = [
        _write_rules("a.rules", _single_corner(6, "A")),
        _write_rules("b.rules", _single_corner(5, "B")),
    ]

    with pytest.raises(RCXMergeError, match="LayerCount"):
        merge_openrcx_rules(files)


def test_rcx_merge_mismatched_corner_names_raises():
    files = [_write_rules("a.rules", _single_corner(6, "A"))]

    with pytest.raises(RCXMergeError, match="corner names"):
        merge_openrcx_rules(files, corner_names=["min", "typ"])


def test_rcx_merge_empty_inputs_raises():
    with pytest.raises(RCXMergeError, match="at least one"):
        merge_openrcx_rules([])


def test_rcx_merge_missing_density_model_raises():
    bad = (
        "Extraction Rules for OpenRCX\n"
        "\n"
        "LayerCount 6\n"
        "DensityRate 1  0\n"
    )
    path = _write_rules("bad.rules", bad)

    with pytest.raises(RCXMergeError, match="DensityModel"):
        merge_openrcx_rules([path])


def test_rcx_merge_missing_layer_count_raises():
    bad = (
        "Extraction Rules for OpenRCX\n"
        "\n"
        "DensityModel 0\n"
        "END DensityModel 0\n"
    )
    path = _write_rules("bad.rules", bad)

    with pytest.raises(RCXMergeError, match="LayerCount"):
        merge_openrcx_rules([path])


def test_rcx_merge_multiple_blocks_in_one_file_raises():
    two_block = _single_corner(6, "A") + "\n" + (
        "DensityModel 0\n"
        "END DensityModel 0\n"
    )
    path = _write_rules("two.rules", two_block)

    with pytest.raises(RCXMergeError, match="exactly one"):
        merge_openrcx_rules([path])


def test_rcx_merge_cli(monkeypatch):
    files = [
        _write_rules("min.rules", _single_corner(6, "MIN")),
        _write_rules("typ.rules", _single_corner(6, "TYP")),
        _write_rules("max.rules", _single_corner(6, "MAX")),
    ]

    monkeypatch.setattr(
        "sys.argv", ["sc-rcx-merge", "-o", "merged.rules"] + files)
    assert rcx_merge.main() == 0

    with open("merged.rules") as fid:
        merged = fid.read()

    assert "DensityRate 3  0 1 2\n" in merged
    assert "END DensityModel 2\n" in merged
    assert merged == merge_openrcx_rules(files)


def test_rcx_merge_cli_corner_names(monkeypatch, capsys):
    files = [
        _write_rules("min.rules", _single_corner(6, "MIN")),
        _write_rules("typ.rules", _single_corner(6, "TYP")),
    ]
    monkeypatch.setattr(
        "sys.argv", ["sc-rcx-merge", "-c", "min,typ"] + files)
    assert rcx_merge.main() == 0

    assert "Corners 2 :  min typ" in capsys.readouterr().out


def test_rcx_merge_cli_stdout(monkeypatch, capsys):
    path = _write_rules("typ.rules", _single_corner(2, "TYP"))
    monkeypatch.setattr("sys.argv", ["sc-rcx-merge", path])
    assert rcx_merge.main() == 0

    assert "DensityRate 1  0" in capsys.readouterr().out


# A small, self-contained multi-corner rules file that mirrors the exact
# layout OpenROAD's OpenRCX emits (as in the rcx_v2 ext_pattern.rules.3corners
# reference): the "Extraction Rules for OpenRCX" header, blank-line spacing,
# a "DensityRate 3  0 1 2" line, and one "DensityModel <n>" block per corner
# separated by a single blank line. It is written out here by hand (no shared
# code with the merge implementation) so the round-trip test below acts as an
# independent oracle for the output format.
_REFERENCE_3CORNERS = """\
Extraction Rules for OpenRCX

DIAGMODEL ON

LayerCount 6
DensityRate 3  0 1 2

DensityModel 0

Metal 1 RESOVER
WIDTH Table 1 entries:  0.17

Metal 1 RESOVER 0
DIST count 3 width 0.17
0 0 0 0.0681705
0 0.31 0 0.0681705
1.92 0 1.92 0.0681705
END DIST

Metal 1 OVER
WIDTH Table 1 entries:  0.17

Metal 1 OVER 0
DIST count 2 width 0.17
0.17 8.61372e-05 9.44952e-06 0.0340853
2.04 0 3.91595e-05 0.0340853
END DIST

Metal 1 UNDER
WIDTH Table 0 entries:

Metal 1 DIAGUNDER
WIDTH Table 0 entries:
END DensityModel 0

DensityModel 1

Metal 1 RESOVER
WIDTH Table 1 entries:  0.17

Metal 1 RESOVER 0
DIST count 3 width 0.17
0 0 0 0.0791705
0 0.31 0 0.0791705
1.92 0 1.92 0.0791705
END DIST

Metal 1 OVER
WIDTH Table 1 entries:  0.17

Metal 1 OVER 0
DIST count 2 width 0.17
0.17 9.61372e-05 9.44952e-06 0.0440853
2.04 0 3.91595e-05 0.0440853
END DIST

Metal 1 UNDER
WIDTH Table 0 entries:

Metal 1 DIAGUNDER
WIDTH Table 0 entries:
END DensityModel 1

DensityModel 2

Metal 1 RESOVER
WIDTH Table 1 entries:  0.17

Metal 1 RESOVER 0
DIST count 3 width 0.17
0 0 0 0.0981705
0 0.31 0 0.0981705
1.92 0 1.92 0.0981705
END DIST

Metal 1 OVER
WIDTH Table 1 entries:  0.17

Metal 1 OVER 0
DIST count 2 width 0.17
0.17 1.06137e-04 9.44952e-06 0.0540853
2.04 0 3.91595e-05 0.0540853
END DIST

Metal 1 UNDER
WIDTH Table 0 entries:

Metal 1 DIAGUNDER
WIDTH Table 0 entries:
END DensityModel 2
"""


def _split_multicorner(text):
    """Split a multi-corner rules file into a list of single-corner texts."""
    lines = text.splitlines()

    layer_count = None
    for line in lines:
        m = re.match(r"^\s*LayerCount\s+(\d+)\s*$", line)
        if m:
            layer_count = int(m.group(1))
            break

    header = (
        "Extraction Rules for OpenRCX\n"
        "\n"
        "DIAGMODEL ON\n"
        "\n"
        f"LayerCount {layer_count}\n"
        "DensityRate 1  0\n"
        "\n"
    )

    blocks = []
    current = None
    for line in lines:
        if current is None:
            if re.match(r"^\s*DensityModel\s+\d+\s*$", line):
                current = ["DensityModel 0"]
        else:
            if re.match(r"^\s*END\s+DensityModel\s+\d+\s*$", line):
                current.append("END DensityModel 0")
                blocks.append(current)
                current = None
            else:
                current.append(line)

    return [header + "\n".join(b) + "\n" for b in blocks]


def test_rcx_merge_roundtrip_reference():
    """Splitting a multi-corner rules file and re-merging reproduces it.

    Uses an inline reference that matches the OpenRCX output format, so the
    round-trip confirms the merge emits the exact multi-corner layout without
    depending on any external file.
    """
    original = _REFERENCE_3CORNERS

    per_corner = _split_multicorner(original)
    assert len(per_corner) == 3

    files = [_write_rules(f"corner{i}.rules", text)
             for i, text in enumerate(per_corner)]

    assert merge_openrcx_rules(files) == original


##############################################################################
# pex_calibrate utility
##############################################################################
##############################################################################
# Target resolution
##############################################################################
def test_resolve_target_callable():
    def my_target(project):
        pass
    assert pc.resolve_target(my_target) is my_target


def test_resolve_target_bad_name():
    with pytest.raises(
            pc.PEXCalibrateError,
            match=r"^could not resolve target 'definitely_not_a_real_target_module': "
                  r"No module named 'siliconcompiler\.targets\."
                  r"definitely_not_a_real_target_module'$"):
        pc.resolve_target("definitely_not_a_real_target_module")


def test_resolve_target_wrong_type():
    with pytest.raises(pc.PEXCalibrateError,
                       match=r"^target must be a callable or string, got int$"):
        pc.resolve_target(123)


def test_resolve_target_bare_name():
    assert pc.resolve_target("freepdk45_demo").__name__ == "freepdk45_demo"


def test_resolve_target_module_function():
    fn = pc.resolve_target("siliconcompiler.targets.freepdk45_demo:freepdk45_demo")
    assert fn.__name__ == "freepdk45_demo"


def test_resolve_target_dotted():
    fn = pc.resolve_target("siliconcompiler.targets.freepdk45_demo.freepdk45_demo")
    assert fn.__name__ == "freepdk45_demo"


##############################################################################
# PDK introspection
##############################################################################
def test_derive_pdk_name():
    assert pc.derive_pdk_name("freepdk45_demo") == "freepdk45"


##############################################################################
# Designs
##############################################################################
def test_demo_designs_build():
    # Construction is network-free (git dataroots fetch lazily at run time).
    designs = [design_cls() for design_cls in pc.DEMO_DESIGNS.values()]
    tops = {d.get_topmodule("rtl") for d in designs}
    assert tops == {"gcd", "picorv32", "aes_cipher_top", "jpeg_encoder"}
    for design in designs:
        assert design.has_fileset("rtl")
        # The demo designs ship no SDC - the survey routes them without one.
        assert not design.has_fileset("sdc")


def test_design_from_dir_missing():
    # The message carries the resolved absolute path, which is the test's cwd.
    with pytest.raises(
            pc.PEXCalibrateError,
            match=rf"^design directory not found: "
                  rf"{re.escape(os.path.join(os.getcwd(), 'no_such_design_dir'))}$"):
        pc.design_from_dir("no_such_design_dir")


def test_design_from_dir_builds():
    os.makedirs("foo", exist_ok=True)
    with open("foo/foo.v", "w") as fid:
        fid.write("module foo ();\nendmodule\n")
    with open("foo/foo.sdc", "w") as fid:
        fid.write("\n")
    design = pc.design_from_dir("foo")
    assert isinstance(design, Design)
    assert design.get_topmodule("rtl") == "foo"
    assert design.has_fileset("rtl")
    # A sibling <name>.sdc is auto-detected into an sdc fileset.
    assert design.has_fileset("sdc")


def test_design_from_dir_no_sdc():
    os.makedirs("bar", exist_ok=True)
    with open("bar/bar.v", "w") as fid:
        fid.write("module bar ();\nendmodule\n")
    design = pc.design_from_dir("bar")
    assert design.has_fileset("rtl")
    # No sibling <name>.sdc -> no sdc fileset (the survey routes it untimed).
    assert not design.has_fileset("sdc")


def _routing(res, cap, source="bench"):
    return {"res": res, "cap": cap, "layertype": "routing", "source": source}


def _via(res, source="pdk"):
    return {"res": res, "cap": None, "layertype": "via", "source": source}


##############################################################################
# CSV data files (round-trip)
##############################################################################
def test_rclayer_csv_round_trip():
    model = {
        "typical": {
            "metal2": _routing(3.5714, 1.19382e-16),
            "metal3": _routing(3.5714, 1.55445e-16),
            "MetalTop": _routing(0.03, 2.0e-16, source="pdk"),
            "Via1": _via(5.0),
        },
        "fast": {"metal2": _routing(3.0, 1.0e-16)},
    }
    pc.write_rclayer_csv("m.csv", model)
    assert pc.read_rclayer_csv("m.csv") == model


def test_rccorr_csv_round_trip():
    # The CSV is the calibration, so every field compute_factors emits must
    # survive it: a cache hit and a fresh derivation have to be interchangeable.
    factors = {
        "typical": {
            "metal2": {"cap_factor": 0.696, "res_factor": 1.0, "nseg": 1234},
            "metal3": {"cap_factor": 0.641, "res_factor": 1.0, "nseg": 56},
        },
    }
    pc.write_rccorr_csv("c.csv", factors)
    assert pc.read_rccorr_csv("c.csv") == factors


def test_rccorr_csv_unknown_fields_stay_none():
    # An unknown res_factor/nseg is written empty, not fabricated as 1.0, so a
    # diagnostic that was never measured cannot be read back as authoritative.
    pc.write_rccorr_csv("c3.csv", {"typical": {"metal2": {"cap_factor": 0.5}}})
    got = pc.read_rccorr_csv("c3.csv")["typical"]["metal2"]
    assert got == {"cap_factor": 0.5, "res_factor": None, "nseg": None}


def test_write_rccorr_skips_none_cap_factor():
    factors = {"typical": {
        "metal2": {"cap_factor": None, "res_factor": 1.0},
        "metal3": {"cap_factor": 0.5, "res_factor": 1.0},
    }}
    pc.write_rccorr_csv("c2.csv", factors)
    got = pc.read_rccorr_csv("c2.csv")
    assert "metal2" not in got["typical"]
    assert got["typical"]["metal3"]["cap_factor"] == 0.5


##############################################################################
# Factor math and line rendering
##############################################################################
def test_compute_factors():
    # pooled: sum_len, sum_cap (F), sum_res (ohm), nseg
    pooled = {"metal2": [100.0, 50.0e-15, 357.14, 10]}
    rcmodel = {"metal2": (3.5714, 1.0e-15), "metal9": (0.03, 1.0e-15)}
    factors = pc.compute_factors(pooled, rcmodel)
    # metal9 absent from pooled -> not characterized
    assert set(factors) == {"metal2"}
    # golden_cap = 50e-15 / 100 = 0.5e-15; cap_factor = 0.5e-15 / 1e-15 = 0.5
    assert abs(factors["metal2"]["cap_factor"] - 0.5) < 1e-9
    assert factors["metal2"]["nseg"] == 10


def test_pool_perlayer_sums_across_designs():
    # Per (corner, layer): the four sums accumulate and nseg is integer-summed;
    # a layer present in only one design carries through unchanged.
    d1 = {"typical": {"metal2": [100.0, 10.0e-15, 300.0, 5],
                      "metal3": [50.0, 4.0e-15, 100.0, 2]}}
    d2 = {"typical": {"metal2": [200.0, 20.0e-15, 600.0, 7],
                      "metal4": [30.0, 1.0e-15, 40.0, 1]}}
    pooled = pc._pool_perlayer([d1, d2])
    assert pooled["typical"]["metal2"] == [300.0, 30.0e-15, 900.0, 12]
    assert pooled["typical"]["metal3"] == [50.0, 4.0e-15, 100.0, 2]
    assert pooled["typical"]["metal4"] == [30.0, 1.0e-15, 40.0, 1]


def test_pool_perlayer_empty():
    assert pc._pool_perlayer([]) == {}


def test_pool_then_compute_factors():
    # The survey's core path (pool across designs, then divide by the rclayer
    # model) is otherwise only exercised in the nightly EDA run. Two designs
    # whose pooled cap/len ratio is 0.5e-15 F/um and whose res/len reproduces
    # the model exactly (res_factor ~ 1.0).
    d1 = {"typical": {"metal2": [100.0, 30.0e-15, 357.14, 3]}}
    d2 = {"typical": {"metal2": [100.0, 70.0e-15, 357.14, 7]}}
    pooled = pc._pool_perlayer([d1, d2])
    factors = pc.compute_factors(pooled["typical"], {"metal2": (3.5714, 1.0e-15)})
    # sum_cap=100e-15, sum_len=200 -> golden 0.5e-15/um; /1e-15 -> 0.5
    assert abs(factors["metal2"]["cap_factor"] - 0.5) < 1e-9
    assert factors["metal2"]["nseg"] == 10
    # sum_res=714.28, sum_len=200 -> 3.5714 ohm/um; /3.5714 -> 1.0
    assert abs(factors["metal2"]["res_factor"] - 1.0) < 1e-6


def test_format_rclayer_lines():
    out = pc.format_rclayer_lines({"typical": {"metal2": _routing(3.5714, 1.19382e-16)}})
    assert "corner 'typical'" in out
    assert 'pdk.add_openroad_rclayer("typical", "routing", "metal2"' in out
    # No factors passed -> no coverage claim either way.
    assert "WARNING" not in out


def test_format_rclayer_lines_warns_on_uncalibrated_corner():
    # A modeled corner the survey did not cover gets a raw bench value with no
    # correction, which can be worse than what the PDK already had. Pasting it
    # blind is the one way this tool can make the estimate worse, so say so.
    model = {
        "typical": {"metal2": _routing(3.5714, 1.19382e-16)},
        "slow": {"metal2": _routing(4.0, 1.3e-16)},
    }
    factors = {"typical": {"metal2": {"cap_factor": 0.7, "res_factor": 1.0, "nseg": 9}}}
    lines = pc.format_rclayer_lines(model, factors).splitlines()

    warnings = [ln for ln in lines if "WARNING" in ln]
    assert len(warnings) == 1
    assert "'slow'" in warnings[0]
    # The warning precedes the corner's own entries, not the calibrated corner's.
    assert lines.index(warnings[0]) > lines.index(
        next(ln for ln in lines if 'pdk.add_openroad_rclayer("typical"' in ln))


def test_format_rclayer_lines_preserved_via_and_note():
    model = {"typical": {
        "metal2": _routing(3.5714, 1.19382e-16),
        "MetalTop": _routing(0.03, 2.0e-16, source="pdk"),
        "Via1": _via(5.0),
    }}
    lines = pc.format_rclayer_lines(model).splitlines()
    bench = next(ln for ln in lines if '"metal2"' in ln)
    top = next(ln for ln in lines if '"MetalTop"' in ln)
    via = next(ln for ln in lines if '"Via1"' in ln)
    # Bench line carries no preservation note.
    assert "not characterized by OpenRCX" not in bench
    # Preserved routing + via lines are noted as not from OpenRCX.
    assert "not characterized by OpenRCX" in top
    assert "not characterized by OpenRCX" in via
    # Via is emitted with the via layertype and no capacitance argument.
    assert 'pdk.add_openroad_rclayer("typical", "via", "Via1", 5)' in via


def test_merge_preserved():
    model = {"typ": {"Metal1": _routing(1.0, 1.0e-16)}}

    class _FakePDK:
        def get(self, *keys):
            assert keys == ("tool", "openroad", "rclayer")
            return [
                ("typ", "routing", "Metal1", 9.0, 9.0e-16),   # already benched -> skip
                ("typ", "via", "Via1", 5.0, None),            # preserve
                ("typ", "routing", "MetalTop", 0.03, 2.0e-16),  # preserve (bench missed)
                ("other", "via", "Via1", 1.0, None),          # whole corner not benched
            ]

    pc._merge_preserved(model, _FakePDK())
    # Benched entry untouched.
    assert model["typ"]["Metal1"] == _routing(1.0, 1.0e-16)
    # Via and uncharacterized top metal preserved from the PDK.
    assert model["typ"]["Via1"] == _via(5.0)
    assert model["typ"]["MetalTop"] == _routing(0.03, 2.0e-16, source="pdk")
    # A corner the bench never covered is preserved wholesale, so the emitted
    # model stays a complete picture of the PDK's rclayer and pasting it cannot
    # drop that corner's estimate.
    assert model["other"] == {"Via1": _via(1.0)}


def test_merge_preserved_gf180_vias():
    # Real PDK: the bench walks routing segments only, so gf180's Via1-Via4
    # rclayer must be preserved from the PDK (source="pdk").
    project = _gf180_project()
    pdk = project.get_library(project.get("asic", "pdk"))
    # Pretend the bench characterized the routing layers for corner 'typ'.
    model = {"typ": {f"Metal{i}": _routing(1.0, 1.0e-16) for i in range(1, 6)}}
    pc._merge_preserved(model, pdk)
    for via in ("Via1", "Via2", "Via3", "Via4"):
        assert model["typ"][via]["layertype"] == "via"
        assert model["typ"][via]["source"] == "pdk"
        assert model["typ"][via]["cap"] is None


def test_format_rccorr_lines():
    out = pc.format_rccorr_lines(
        {"typical": {"metal2": {"cap_factor": 0.696, "res_factor": 1.0}}})
    assert 'pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.6960)' in out


##############################################################################
# Orchestration: caching / rerun / print (no EDA - the flows are stubbed)
##############################################################################
# Stand-in survey design: the flows are stubbed out, so only the list length
# matters - but it must be non-empty, since calibrate() rejects an empty survey.
_DUMMY_DESIGN = pc._bench_design()


def _stub_flows(monkeypatch, counter):
    monkeypatch.setattr(pc, "derive_pdk_name", lambda target: "testpdk")

    def fake_bench(target):
        counter["bench"] += 1
        return {"typical": {"metal2": _routing(3.5, 1.2e-16)}}

    def fake_survey(target, designs, initial_rclayer=None):
        counter["survey"] += 1
        return {"typical": {"metal2": [100.0, 12.0e-15, 350.0, 5]}}, object()

    def fake_factors(pooled, pdk):
        return {"typical": {"metal2": {"cap_factor": 0.6, "res_factor": 1.0, "nseg": 5}}}

    monkeypatch.setattr(pc, "run_bench", fake_bench)
    monkeypatch.setattr(pc, "run_survey", fake_survey)
    monkeypatch.setattr(pc, "compute_all_factors", fake_factors)


def test_calibrate_caches_reuses_and_reruns(monkeypatch):
    counter = {"bench": 0, "survey": 0}
    _stub_flows(monkeypatch, counter)

    def target(project):
        pass

    # Fresh: computes both phases and writes both files.
    model, factors = pc.calibrate(target, designs=[_DUMMY_DESIGN], outdir="out")
    assert counter == {"bench": 1, "survey": 1}
    assert os.path.isfile("out/testpdk.rclayer.csv")
    assert os.path.isfile("out/testpdk.rccorr.csv")
    assert model == {"typical": {"metal2": _routing(3.5, 1.2e-16)}}
    assert factors["typical"]["metal2"]["cap_factor"] == 0.6

    # Reuse: both files present, nothing recomputed.
    model2, factors2 = pc.calibrate(target, designs=[_DUMMY_DESIGN], outdir="out")
    assert counter == {"bench": 1, "survey": 1}
    assert model2 == model
    assert factors2["typical"]["metal2"]["cap_factor"] == 0.6
    assert model2["typical"]["metal2"]["source"] == "bench"

    # Partial: drop only the correction file -> reuse the model, rerun the survey.
    os.remove("out/testpdk.rccorr.csv")
    pc.calibrate(target, designs=[_DUMMY_DESIGN], outdir="out")
    assert counter == {"bench": 1, "survey": 2}

    # rerun: recompute both.
    pc.calibrate(target, designs=[_DUMMY_DESIGN], outdir="out", rerun=True)
    assert counter == {"bench": 2, "survey": 3}


def test_calibrate_rejects_empty_designs(monkeypatch):
    # None means "use the demo survey"; an explicitly empty list would otherwise
    # produce an empty calibration and cache it.
    counter = {"bench": 0, "survey": 0}
    _stub_flows(monkeypatch, counter)

    with pytest.raises(pc.PEXCalibrateError,
                       match=r"^designs is empty; pass None for the bundled demo survey or at "
                             r"least one design$"):
        pc.calibrate(lambda project: None, designs=[], outdir="out")
    assert counter == {"bench": 0, "survey": 0}


def test_run_survey_rejects_empty_designs():
    with pytest.raises(pc.PEXCalibrateError,
                       match=r"^the calibration survey needs at least one design$"):
        pc.run_survey(lambda project: None, [])


def test_calibrate_does_not_cache_an_empty_survey(monkeypatch):
    # A phase that yields nothing must fail loudly instead of writing a
    # header-only CSV that every later run silently reuses.
    counter = {"bench": 0, "survey": 0}
    _stub_flows(monkeypatch, counter)
    monkeypatch.setattr(pc, "compute_all_factors", lambda pooled, pdk: {})

    with pytest.raises(pc.PEXCalibrateError,
                       match=r"^the calibration survey produced no correction factors; no "
                             r"surveyed layer matched a corner in the initial rclayer model$"):
        pc.calibrate(lambda project: None, designs=[_DUMMY_DESIGN], outdir="out")

    # The model CSV is written (that phase succeeded); the survey CSV is not.
    assert os.path.isfile("out/testpdk.rclayer.csv")
    assert not os.path.isfile("out/testpdk.rccorr.csv")


def test_derive_pdk_name_requires_a_pdk():
    # A target that never selects a PDK would otherwise name its data files
    # "None.rclayer.csv".
    # The message quotes the target itself, which for a lambda is a repr.
    with pytest.raises(pc.PEXCalibrateError,
                       match=r"^target '.*' selects no PDK \(\[asic,pdk\] is unset\); a PEX "
                             r"calibration needs a PDK with an OpenRCX deck$"):
        pc.derive_pdk_name(lambda project: None)


def test_calibrate_prints(monkeypatch, capsys):
    counter = {"bench": 0, "survey": 0}
    _stub_flows(monkeypatch, counter)

    def target(project):
        pass

    pc.calibrate(target, designs=[_DUMMY_DESIGN], outdir="out")
    out = capsys.readouterr().out
    # A single run emits both paste-able blocks (no separate --print needed).
    assert 'pdk.add_openroad_rclayer("typical", "routing", "metal2"' in out
    assert 'pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.6000)' in out


def test_main_print_only(monkeypatch, capsys):
    monkeypatch.setattr(pc, "derive_pdk_name", lambda target: "testpdk")
    os.makedirs("out", exist_ok=True)
    pc.write_rclayer_csv("out/testpdk.rclayer.csv", {"typical": {"metal2": _routing(3.5, 1.2e-16)}})
    pc.write_rccorr_csv("out/testpdk.rccorr.csv",
                        {"typical": {"metal2": {"cap_factor": 0.6, "res_factor": 1.0}}})

    assert pc.main(["t", "-o", "out", "--print"]) == 0
    out = capsys.readouterr().out
    assert 'pdk.add_openroad_rclayer("typical", "routing", "metal2"' in out
    assert 'pdk.add_openroad_rccorrection("typical", "metal2", cap_factor=0.6000)' in out


def test_main_plumbs_cli_flags(monkeypatch, tmp_path):
    # The CLI is the documented entry point; check every flag reaches calibrate()
    # with the value the help text promises.
    seen = {}

    def fake_calibrate(target, designs=None, outdir=None, rerun=False, score=False):
        seen.update(target=target, designs=designs, outdir=outdir, rerun=rerun, score=score)
        return {}, {}

    monkeypatch.setattr(pc, "calibrate", fake_calibrate)
    design_dir = tmp_path / "widget"
    design_dir.mkdir()
    (design_dir / "widget.v").write_text("module widget ();\nendmodule\n")

    assert pc.main(["my_pkg:my_target", "-o", "outdir", "--rerun", "--score",
                    "--design", str(design_dir)]) == 0
    assert seen["target"] == "my_pkg:my_target"
    assert seen["outdir"] == "outdir"
    assert seen["rerun"] is True
    assert seen["score"] is True
    assert [design.name for design in seen["designs"]] == ["widget"]


def test_main_reports_bad_design_dir(monkeypatch, capsys):
    # A PEXCalibrateError must surface as a CLI usage error, not a traceback.
    monkeypatch.setattr(pc, "calibrate", lambda *args, **kwargs: ({}, {}))
    # argparse exits 2 on a usage error; the reason goes to stderr.
    with pytest.raises(SystemExit, match=r"^2$"):
        pc.main(["t", "--design", "no_such_design_dir"])
    assert "design directory not found" in capsys.readouterr().err


def test_main_print_only_missing_files(monkeypatch, capsys):
    monkeypatch.setattr(pc, "derive_pdk_name", lambda target: "testpdk")
    with pytest.raises(SystemExit, match=r"^2$"):
        pc.main(["t", "-o", "nonexistent_dir", "--print"])
    assert "data files not found in nonexistent_dir; run without --print first" in \
        capsys.readouterr().err


##############################################################################
# Scoring (quantify the win) - EDA-free math + wiring
##############################################################################
def test_apply_factors_cap_only_and_clears_previous():
    pdk = OpenROADPDK()
    pdk.add_openroad_rccorrection("typical", "metal9", cap_factor=0.5)  # cleared
    pc.apply_factors(pdk, {"typical": {
        "metal2": {"cap_factor": 0.7, "res_factor": 1.0},
        "metal3": {"cap_factor": None, "res_factor": 1.0},  # no cap -> skipped
    }})
    assert pdk.get("tool", "openroad", "rccorrection") == [("typical", "metal2", None, 0.7)]


def test_read_nets():
    with open("nets.csv", "w") as fid:
        fid.write("pexcorner,scene,net,sigtype,golden_cap_F,est_cap_F\n")
        fid.write("typical,s,n1,SIGNAL,1.0e-15,1.5e-15\n")
        fid.write("typical,s,n2,CLOCK,2.0e-15,2.0e-15\n")
        # No estimate available for this net: the Tcl writes the field empty.
        fid.write("typical,s,n3,SIGNAL,3.0e-15,\n")
    assert pc._read_nets("nets.csv") == [
        ("typical", "SIGNAL", 1.0e-15, 1.5e-15),
        ("typical", "CLOCK", 2.0e-15, 2.0e-15),
        ("typical", "SIGNAL", 3.0e-15, None),
    ]


def test_score_errors_skips_missing_estimate():
    # A net with no estimate must not be scored as a 100% under-estimate.
    rows = [("typ", "SIGNAL", 1.0, 1.5),
            ("typ", "SIGNAL", 1.0, None)]
    assert pc._score_errors(rows) == {"typ": [0.5]}


def test_score_errors_filters_sigtype_and_zero_golden():
    rows = [("typ", "SIGNAL", 1.0, 1.5),   # 0.5
            ("typ", "CLOCK", 2.0, 1.0),    # 0.5
            ("typ", "POWER", 1.0, 5.0),    # non signal/clock -> skip
            ("typ", "SIGNAL", 0.0, 1.0)]   # golden 0 -> skip
    assert pc._score_errors(rows) == {"typ": [0.5, 0.5]}


def test_percentile_nearest_rank():
    values = [float(v) for v in range(1, 11)]
    # p50 is the 5th of 10 samples and p90 the 9th. Truncating the rank instead
    # of rounding it up would report the 10th - the maximum - as p90, hiding the
    # tail the score is meant to expose.
    assert pc._percentile(values, 0.5) == 5.0
    assert pc._percentile(values, 0.9) == 9.0
    # Ends and degenerate inputs stay in range.
    assert pc._percentile(values, 0.0) == 1.0
    assert pc._percentile(values, 1.0) == 10.0
    assert pc._percentile([7.0], 0.9) == 7.0
    assert pc._percentile([], 0.5) is None


def test_score_summary_stats():
    rows = [("typ", "SIGNAL", 1.0, 1.0),   # 0.0
            ("typ", "SIGNAL", 1.0, 1.5),   # 0.5
            ("typ", "SIGNAL", 1.0, 2.0)]   # 1.0
    summ = pc._score_summary(rows)["typ"]
    assert summ["nnets"] == 3
    assert abs(summ["mean"] - 0.5) < 1e-9
    assert summ["median"] == 0.5
    assert summ["p90"] == 1.0


def test_print_score_table(capsys):
    before = {"typical": {"median": 0.30, "p90": 0.60, "mean": 0.35}}
    after = {"typical": {"median": 0.10, "p90": 0.25, "mean": 0.15}}
    pc.print_score(before, after)
    out = capsys.readouterr().out
    assert "typical" in out and "median" in out and "p90" in out
    assert "30.0%" in out and "10.0%" in out


def test_calibrate_score_path(monkeypatch, capsys):
    counter = {"bench": 0, "survey": 0}
    _stub_flows(monkeypatch, counter)
    calls = []

    def fake_survey_nets(target, designs, model, factors=None):
        calls.append(factors is not None)
        return ({"typical": {"median": 0.5, "p90": 0.8, "mean": 0.55}} if factors is None
                else {"typical": {"median": 0.1, "p90": 0.2, "mean": 0.12}})

    monkeypatch.setattr(pc, "_survey_nets", fake_survey_nets)

    def target(project):
        pass

    pc.calibrate(target, designs=[_DUMMY_DESIGN], outdir="out", score=True)
    # before (uncorrected, factors=None) then after (calibrated, factors set)
    assert calls == [False, True]
    assert "typical" in capsys.readouterr().out
