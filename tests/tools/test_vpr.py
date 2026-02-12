import pytest

import os.path

import xml.etree.ElementTree as ET

from siliconcompiler import FPGA, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.vpr.place import PlaceTask
from siliconcompiler.tools.vpr.route import RouteTask
from siliconcompiler.tools.vpr import VPRFPGA
from siliconcompiler.tools.genfasm.bitstream import BitstreamTask

from tools.inputimporter import ImporterTask


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", PlaceTask())
    proj.set_flow(flow)

    fpga = VPRFPGA()
    fpga.set_name("testfpga")
    proj.set_fpga(fpga)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_run(datadir):
    design = Design("adder")
    with design.active_fileset("rtl"):
        design.set_topmodule("adder")

    proj = FPGA(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("import", ImporterTask())
    flow.node("place", PlaceTask())
    flow.node("route", RouteTask())
    flow.node("bitstream", BitstreamTask())
    flow.edge("import", "place")
    flow.edge("place", "route")
    flow.edge("route", "bitstream")
    proj.set_flow(flow)

    fpga = VPRFPGA()
    fpga.set_name("testfpga")
    fpga.set_vpr_devicecode("K6_N8_3x3")
    fpga.set_vpr_channelwidth(40)
    fpga.set_vpr_clockmodel("ideal")
    fpga.set_lutsize(6)
    fpga.add_vpr_registertype("dff")
    fpga.set_vpr_archfile(os.path.join(datadir, "fpga", "K6_N8_3x3.xml"))
    fpga.set_vpr_graphfile(os.path.join(datadir, "fpga", "K6_N8_3x3_rr_graph.xml"))
    proj.set_fpga(fpga)

    ImporterTask.find_task(proj).set("var", "input_files",
                                     os.path.join(datadir, "adder.blif"))

    assert proj.run()

    assert os.path.isfile(proj.find_result("place", "place"))
    assert os.path.isfile(proj.find_result("route", "route"))
    assert os.path.isfile(proj.find_result("fasm", "bitstream"))


def test_vpr_max_router_iterations(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
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

    RouteTask.find_task(proj).set("var", "max_router_iterations", 300)

    node = SchedulerNode(proj, step='route', index='0')
    with node.runtime():
        node.setup()
        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 45
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
            '--router_lookahead', 'map',
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


def test_vpr_place_with_constraint(gcd_design, monkeypatch):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("place", PlaceTask())
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

    node = SchedulerNode(proj, step='place', index='0')
    with node.runtime():
        node.setup()
        node.task.setup_work_directory(node.workdir)
        with open(os.path.join(node.workdir, node.task.auto_constraints_file()), "w") as f:
            f.write("test")

        monkeypatch.chdir(node.workdir)
        arguments = node.task.get_runtime_arguments()
        monkeypatch.undo()
        assert len(arguments) == 42
        del arguments[34]  # read_rr_graph path
        del arguments[10]  # cpu count
        del arguments[8]  # arch path
        assert arguments == [
            '--device', 'faux_device',
            '--verify_file_digests', 'off',
            '--write_block_usage', 'reports/block_usage.json',
            '--outfile_prefix', 'outputs/',
            '--num_workers',
            '--constant_net_method', 'route',
            '--const_gen_inference', 'none',
            '--sweep_dangling_primary_ios', 'off',
            '--sweep_dangling_nets', 'off',
            '--allow_dangling_combinational_nodes', 'on',
            '--sweep_constant_primary_outputs', 'off',
            '--sweep_dangling_blocks', 'off',
            '--clock_modeling', 'ideal',
            '--router_lookahead', 'map',
            '--timing_analysis', 'off',
            '--read_vpr_constraints', 'inputs/sc_constraints.xml',
            '--read_rr_graph',
            '--route_chan_width', '50',
            'inputs/gcd.blif',
            '--pack',
            '--place',
            '--graphics_commands',
            'set_draw_block_text 1; set_draw_block_outlines 1; '
            'save_graphics reports/gcd_place.png;']


def test_vpr_gen_post_implementation_netlist(gcd_design):
    with gcd_design.active_fileset("sdc-test"):
        gcd_design.add_file(os.path.abspath("test.sdc"))
    with open('test.sdc', 'w') as f:
        f.write('test')

    proj = FPGA(gcd_design)
    proj.add_fileset(["rtl", "sdc-test"])

    flow = Flowgraph("testflow")
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

    RouteTask.find_task(proj).set("var", "timing_corner", "slow")

    node = SchedulerNode(proj, step='route', index='0')
    with node.runtime():
        node.setup()

        assert node.task.get("var", "enable_timing_analysis") is True
        assert node.task.get("var", "gen_post_implementation_netlist") is True

        arguments = node.task.get_runtime_arguments()
        assert len(arguments) == 57
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
            '--router_lookahead', 'map',
            '--sdc_file', os.path.abspath("test.sdc"),
            '--timing_report_detail', 'aggregated',
            '--timing_report_npaths', '20',
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


def test_vpr_parameter_max_router_iterations():
    task = RouteTask()
    task.set_vpr_maxrouteriterations(100)
    assert task.get("var", "max_router_iterations") == 100
    task.set_vpr_maxrouteriterations(200, step='route', index='1')
    assert task.get("var", "max_router_iterations", step='route', index='1') == 200
    assert task.get("var", "max_router_iterations") == 100


def test_vpr_parameter_gen_post_implementation_netlist():
    task = RouteTask()
    task.set_vpr_genpostimplementationnetlist(True)
    assert task.get("var", "gen_post_implementation_netlist") is True
    task.set_vpr_genpostimplementationnetlist(False, step='route', index='1')
    assert task.get("var", "gen_post_implementation_netlist", step='route', index='1') is False
    assert task.get("var", "gen_post_implementation_netlist") is True


def test_vpr_parameter_timing_corner():
    task = RouteTask()
    task.set_vpr_timingcorner('fast')
    assert task.get("var", "timing_corner") == 'fast'
    task.set_vpr_timingcorner('slow', step='route', index='1')
    assert task.get("var", "timing_corner", step='route', index='1') == 'slow'
    assert task.get("var", "timing_corner") == 'fast'


def test_json_constraints_load_and_map(tmp_path):
    from siliconcompiler.tools.vpr import _json_constraint as jcon

    # create json constraints file
    json_constraints = {
        'pinA': {'pin': 'core_pin', 'direction': 'input'},
        'pinB': {'pin': 'core_out', 'direction': 'output'}
    }
    json_file = tmp_path / 'constraints.json'
    json_file.write_text(__import__('json').dumps(json_constraints))

    loaded = jcon.load_json_constraints(str(json_file))
    assert loaded == json_constraints

    # create constraints map
    cmap = {
        'core_pin': {'x': 1, 'y': 2, 'subtile': 0, 'block_type': 7},
        'core_out': {'x': 3, 'y': 4, 'subtile': 1, 'block_type': 9}
    }
    map_file = tmp_path / 'map.json'
    map_file.write_text(__import__('json').dumps(cmap))

    loaded_map = jcon.load_constraints_map(str(map_file))
    assert loaded_map == cmap

    class DummyLogger:
        def __init__(self):
            self.errors = []

        def error(self, msg):
            self.errors.append(msg)

    logger = DummyLogger()

    design_constraints, errors = jcon.map_constraints(logger, loaded, loaded_map)
    # input pin maps to tuple
    assert design_constraints['pinA'] == (1, 2, 0, 7)
    # output pin gets prefixed
    assert design_constraints['out:pinB'] == (3, 4, 1, 9)
    assert errors == 0

    # missing entry in map should increment errors
    bad_json = {'pinX': {'pin': 'missing_pin', 'direction': 'input'}}
    dc, errs = jcon.map_constraints(logger, bad_json, loaded_map)
    assert errs == 1


def test_xml_constraint_helpers(tmp_path):
    from siliconcompiler.tools.vpr import _xml_constraint as xcon
    # test region parsing
    region = ('5', '6', '2', '11')
    x_low, x_high, y_low, y_high, subtile, block_type = xcon.generate_region_from_pin(region)
    assert (x_low, x_high, y_low, y_high, subtile, block_type) == (5, 5, 6, 6, 2, 11)

    # partition name
    pname = xcon.generate_partition_name('pin[0]')
    assert 'part_pin_0' in pname

    # add atom
    atom = xcon.generate_add_atom_xml('pinA')
    assert atom.tag == 'add_atom'
    assert atom.get('name_pattern') == 'pinA'

    # add block type
    btype = xcon.generate_add_block_type_xml('myblock')
    assert btype.tag == 'add_logical_block'
    assert btype.get('name_pattern') == 'myblock'

    # add region (call directly with expected args)
    region_xml = xcon.generate_add_region_xml(1, 1, 2, 2, 0)
    assert region_xml.tag == 'add_region'
    assert region_xml.get('x_low') == '1'
    assert region_xml.get('y_low') == '2'
    assert region_xml.get('subtile') == '0'

    # write xml to file
    root = ET.Element('vpr_constraints')
    outfile = tmp_path / 'out.xml'
    xcon.write_vpr_constraints_xml_file(root, str(outfile))
    assert outfile.exists()
