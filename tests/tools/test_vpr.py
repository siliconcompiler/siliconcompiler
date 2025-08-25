import pytest

import os.path

from siliconcompiler import FPGAProject, FlowgraphSchema
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.vpr.place import PlaceTask
from siliconcompiler.tools.vpr.route import RouteTask
from siliconcompiler.tools.vpr import VPRFPGA


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
def test_version(gcd_design):
    proj = FPGAProject(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("version", PlaceTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_vpr_max_router_iterations(gcd_design):
    proj = FPGAProject(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("route", RouteTask())
    proj.set_flow(flow)

    fpga = VPRFPGA()
    fpga.set_name("faux")
    fpga.set_vpr_devicecode("faux_device")
    fpga.set_vpr_clockmodel("ideal")
    fpga.set_vpr_channelwidth(50)
    fpga.set_vpr_archfile("test.xml")
    fpga.set_vpr_graphfile("test_graph.xml")

    with open('test.xml', 'w') as f:
        f.write('test')
    with open('test_graph.xml', 'w') as f:
        f.write('test')

    proj.set_fpga(fpga)

    proj.get_task(filter=RouteTask).set("var", "max_router_iterations", 300)

    node = SchedulerNode(proj, step='route', index='0')
    with node.runtime():
        node.setup()
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 43
        del arguments[10]  # cpu count
        assert arguments == [
            '--device', 'faux_device',
            '--verify_file_digests', 'off',
            '--write_block_usage', 'reports/block_usage.json',
            '--outfile_prefix', 'outputs/',
            os.path.abspath("test.xml"),
            '--num_workers',
            '--constant_net_method', 'route',
            '--const_gen_inference', 'none',
            '--sweep_dangling_primary_ios', 'off',
            '--sweep_dangling_nets', 'off',
            '--allow_dangling_combinational_nodes', 'on',
            '--sweep_constant_primary_outputs', 'off',
            '--sweep_dangling_blocks', 'off',
            '--clock_modeling', 'ideal',
            '--timing_analysis', 'off',
            '--read_rr_graph', os.path.abspath("test_graph.xml"),
            '--route_chan_width', '50',
            'inputs/gcd.blif',
            '--route', '--net_file', 'inputs/gcd.net', '--place_file', 'inputs/gcd.place',
            '--max_router_iterations', '300',
            '--graphics_commands',
            'set_draw_block_text 1; set_draw_block_outlines 1; '
            'save_graphics reports/gcd_place.png; set_draw_block_text 0; '
            'set_draw_block_outlines 0; set_routing_util 1; '
            'save_graphics reports/gcd_route_utilization_with_placement.png; '
            'set_draw_block_text 0; set_draw_block_outlines 0; set_routing_util 4; '
            'save_graphics reports/gcd_route_utilization.png;']


def test_vpr_gen_post_implementation_netlist(gcd_design):
    proj = FPGAProject(gcd_design)
    proj.add_fileset("rtl")

    flow = FlowgraphSchema("testflow")
    flow.node("route", RouteTask())
    proj.set_flow(flow)

    fpga = VPRFPGA()
    fpga.set_name("faux")
    fpga.set_vpr_devicecode("faux_device")
    fpga.set_vpr_clockmodel("ideal")
    fpga.set_vpr_channelwidth(50)
    fpga.set_vpr_archfile("test.xml")
    fpga.set_vpr_graphfile("test_graph.xml")

    with open('test.xml', 'w') as f:
        f.write('test')
    with open('test_graph.xml', 'w') as f:
        f.write('test')

    proj.set_fpga(fpga)

    proj.get_task(filter=RouteTask).set("var", "gen_post_implementation_netlist", True)
    proj.get_task(filter=RouteTask).set("var", "timing_corner", "slow")

    node = SchedulerNode(proj, step='route', index='0')
    with node.runtime():
        node.setup()
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 51
        del arguments[10]  # cpu count
        assert arguments == [
            '--device', 'faux_device',
            '--verify_file_digests', 'off',
            '--write_block_usage', 'reports/block_usage.json',
            '--outfile_prefix', 'outputs/',
            os.path.abspath("test.xml"),
            '--num_workers',
            '--constant_net_method', 'route',
            '--const_gen_inference', 'none',
            '--sweep_dangling_primary_ios', 'off',
            '--sweep_dangling_nets', 'off',
            '--allow_dangling_combinational_nodes', 'on',
            '--sweep_constant_primary_outputs', 'off',
            '--sweep_dangling_blocks', 'off',
            '--clock_modeling', 'ideal',
            '--timing_analysis', 'off',
            '--read_rr_graph', os.path.abspath("test_graph.xml"),
            '--route_chan_width', '50',
            'inputs/gcd.blif',
            '--route', '--net_file', 'inputs/gcd.net', '--place_file', 'inputs/gcd.place',
            '--max_router_iterations', '50',
            '--graphics_commands',
            'set_draw_block_text 1; set_draw_block_outlines 1; '
            'save_graphics reports/gcd_place.png; set_draw_block_text 0; '
            'set_draw_block_outlines 0; set_routing_util 1; '
            'save_graphics reports/gcd_route_utilization_with_placement.png; '
            'set_draw_block_text 0; set_draw_block_outlines 0; set_routing_util 4; '
            'save_graphics reports/gcd_route_utilization.png;',
            '--gen_post_synthesis_netlist', 'on',
            '--gen_post_implementation_sdc', 'on',
            '--post_synth_netlist_unconn_inputs', 'nets',
            '--post_synth_netlist_module_parameters', 'off']
