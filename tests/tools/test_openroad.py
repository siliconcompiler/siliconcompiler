# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import pytest

from siliconcompiler import ASIC, Flowgraph

from siliconcompiler.flows.asicflow import ASICFlow

from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.openroad import _apr
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad import metrics
from siliconcompiler.utils.paths import workdir
from siliconcompiler.tools.openroad import write_data
from siliconcompiler.tools.openroad import antenna_repair
from siliconcompiler.tools.openroad import fillmetal_insertion
from siliconcompiler.tools.openroad import global_placement
from siliconcompiler.tools.openroad import global_route
from siliconcompiler.tools.openroad import init_floorplan
from siliconcompiler.tools.openroad import macro_placement
from siliconcompiler.tools.openroad import power_grid_analysis
from siliconcompiler.tools.openroad import power_grid
from siliconcompiler.tools.openroad import rcx_bench
from siliconcompiler.tools.openroad import rcx_extract
from siliconcompiler.tools.openroad import rdlroute
from siliconcompiler.tools.openroad import repair_design
from siliconcompiler.tools.openroad import repair_timing
from siliconcompiler.tools.openroad import screenshot


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
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_openroad_images(asic_gcd):
    for task in APRTask.find_task(asic_gcd):
        task.set('var', 'ord_enable_images', True)

    assert asic_gcd.run()

    images_count = {
        'floorplan.init': 2,
        'place.detailed': 6,
        'cts.clock_tree_synthesis': 10,
        'route.detailed': 12,
        'write.views': 28,
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
    task.set_openroad_rszskippinswap(True)
    assert task.get("var", "rsz_skip_pin_swap") is True
    task.set_openroad_rszskippinswap(False, step='rsz', index='1')
    assert task.get("var", "rsz_skip_pin_swap", step='rsz', index='1') is False
    assert task.get("var", "rsz_skip_pin_swap") is True


def test_openroad_apr_parameter_rsz_skip_gate_cloning():
    task = _apr.OpenROADRSZTimingParameter()
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
    task.set_openroad_removebuffers(True)
    assert task.get("var", "remove_synth_buffers") is True
    task.set_openroad_removebuffers(False, step='init_floorplan', index='1')
    assert task.get("var", "remove_synth_buffers", step='init_floorplan', index='1') is False
    assert task.get("var", "remove_synth_buffers") is True


def test_openroad_init_floorplan_parameter_remove_dead_logic():
    task = init_floorplan.InitFloorplanTask()
    task.set_openroad_removedeadlogic(True)
    assert task.get("var", "remove_dead_logic") is True
    task.set_openroad_removedeadlogic(False, step='init_floorplan', index='1')
    assert task.get("var", "remove_dead_logic", step='init_floorplan', index='1') is False
    assert task.get("var", "remove_dead_logic") is True


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
    task = rcx_bench.ORXBenchTask()
    task.set_openroad_benchmaxlayer('m1')
    assert task.get("var", "max_layer") == 'm1'
    task.set_openroad_benchmaxlayer('m2', step='rcx_bench', index='1')
    assert task.get("var", "max_layer", step='rcx_bench', index='1') == 'm2'
    assert task.get("var", "max_layer") == 'm1'


def test_openroad_rcx_bench_parameter_bench_length():
    task = rcx_bench.ORXBenchTask()
    task.set_openroad_benchlength(100.0)
    assert task.get("var", "bench_length") == 100.0
    task.set_openroad_benchlength(200.0, step='rcx_bench', index='1')
    assert task.get("var", "bench_length", step='rcx_bench', index='1') == 200.0
    assert task.get("var", "bench_length") == 100.0


def test_openroad_rcx_extract_parameter_corner():
    task = rcx_extract.ORXExtractTask()
    task.set_openroad_rcxcorner('test_corner')
    assert task.get("var", "corner") == 'test_corner'
    task.set_openroad_rcxcorner('other_corner', step='rcx_extract', index='1')
    assert task.get("var", "corner", step='rcx_extract', index='1') == 'other_corner'
    assert task.get("var", "corner") == 'test_corner'


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
