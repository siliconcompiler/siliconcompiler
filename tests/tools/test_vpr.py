import json
import pytest

import os.path

import xml.etree.ElementTree as ET

from unittest.mock import patch

from siliconcompiler import FPGA, Flowgraph, Design
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.vpr.place import PlaceTask
from siliconcompiler.tools.vpr.route import RouteTask
from siliconcompiler.tools.vpr.show import ShowTask as VPRShowTask
from siliconcompiler.tools.vpr.screenshot import ScreenshotTask as VPRScreenshotTask
from siliconcompiler.tools.vpr import VPRFPGA
from siliconcompiler.tools.vpr import _json_constraint as jcon
from siliconcompiler.tools.vpr import _xml_constraint as xcon
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


# Test that JSON pin constraints can be read, and that when used
# with a constraints map they can produce "mapped constraints",
# that is, output data that can be passed to the XML constraints
# generator
def test_json_constraints_load_and_map(tmp_path):

    # create json constraints file
    json_constraints = {
        'pinA': {'pin': 'core_pin', 'direction': 'input'},
        'pinB': {'pin': 'core_out', 'direction': 'output'}
    }
    json_file = tmp_path / 'constraints.json'
    json_file.write_text(json.dumps(json_constraints))

    loaded = jcon.load_json_constraints(str(json_file))
    assert loaded == json_constraints

    # create constraints map
    cmap = {
        'core_pin': {'x': 1, 'y': 2, 'subtile': 0, 'block_type': "clb"},
        'core_out': {'x': 3, 'y': 4, 'subtile': 1, 'block_type': "iob"}
    }
    map_file = tmp_path / 'map.json'
    map_file.write_text(json.dumps(cmap))

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
    assert design_constraints['pinA'] == (1, 2, 0, "clb")
    # output pin gets prefixed
    assert design_constraints['out:pinB'] == (3, 4, 1, "iob")
    assert errors == 0

    # errors are flagged by map_constraints when input constraints
    # to the mapper contain pin names that are not in the constraints
    # map; validate that errors are in fact generated for that case
    bad_json = {'pinX': {'pin': 'missing_pin', 'direction': 'input'}}
    _, errs = jcon.map_constraints(logger, bad_json, loaded_map)
    assert errs == 1


# Verify that each of the helper functions called by the XML constraints
# generator produces valid output; i.e. passes/formats input data correctly
def test_xml_constraint_helpers(tmp_path):
    # test region parsing
    region = ('5', '6', '2', 'clb')
    x_low, x_high, y_low, y_high, subtile, block_type = xcon.generate_region_from_pin(region)
    assert (x_low, x_high, y_low, y_high, subtile, block_type) == (5, 5, 6, 6, 2, 'clb')

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


@pytest.fixture
def faux_fpga():
    """Factory: configure a minimal FPGA + arch/graph files so VPRTask resolves."""
    def _setup(proj):
        fpga = VPRFPGA()
        fpga.set_name("faux")
        fpga.set_vpr_devicecode("faux_device")
        fpga.set_vpr_clockmodel("ideal")
        fpga.set_vpr_channelwidth(50)
        fpga.set_vpr_archfile("test.xml")
        fpga.set_vpr_graphfile("test_graph.xml")
        proj.set_fpga(fpga)

        for fn in ("test.xml", "test_graph.xml"):
            with open(fn, "w") as f:
                f.write("test")
    return _setup


@pytest.fixture
def write_design_files():
    """Factory: create the blif/net/place/route files VPR show/screenshot read."""
    def _write(directory):
        os.makedirs(directory, exist_ok=True)
        for ext in ("blif", "net", "place", "route"):
            with open(os.path.join(directory, f"gcd.{ext}"), "w") as f:
                f.write("test")
    return _write


@pytest.fixture
def expected_vpr_args():
    """Factory: the full VPR command (built by VPRTask + show) for the faux FPGA.

    ``file_dir`` is the directory the design files are read from and ``tail`` is the
    task-specific suffix (``--disp on`` for show, ``--graphics_commands ...`` for
    screenshot). Threads are pinned to 2 by the caller patching get_cores.
    """
    def _build(file_dir, tail):
        return [
            '--device', 'faux_device',
            '--verify_file_digests', 'off',
            '--write_block_usage', 'reports/block_usage.json',
            '--outfile_prefix', 'outputs/',
            os.path.abspath('test.xml'),
            '--num_workers', '2',
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
            '--read_rr_graph', os.path.abspath('test_graph.xml'),
            '--route_chan_width', '50',
            os.path.join(file_dir, 'gcd.blif'),
            '--net_file', os.path.join(file_dir, 'gcd.net'),
            '--analysis',
            '--place_file', os.path.join(file_dir, 'gcd.place'),
            '--route_file', os.path.join(file_dir, 'gcd.route'),
        ] + tail
    return _build


def test_vpr_show_runtime_args_from_inputs(gcd_design, faux_fpga, write_design_files,
                                           expected_vpr_args):
    # Regression: ShowTask.runtime_options() called os.path.dirname(showfilepath)
    # unconditionally and crashed when no showfilepath was set (driven from an
    # upstream node). It must fall back to the inputs/ directory.
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("show", VPRShowTask())
    proj.set_flow(flow)

    faux_fpga(proj)
    write_design_files("inputs")

    node = SchedulerNode(proj, step="show", index="0")
    with node.runtime():
        with patch("siliconcompiler.utils.get_cores") as get_cores:
            get_cores.return_value = 2
            assert node.setup() is True
        # No showfilepath set -> must not raise, must read from inputs/.
        arguments = node.task.get_runtime_arguments()

    assert arguments == expected_vpr_args("inputs", ["--disp", "on"])


def test_vpr_show_runtime_args_with_showfilepath(gcd_design, faux_fpga, write_design_files,
                                                 expected_vpr_args):
    # When showfilepath is set, the design files are read from its directory.
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("show", VPRShowTask())
    proj.set_flow(flow)

    faux_fpga(proj)
    write_design_files("showdir")

    VPRShowTask.find_task(proj).set("var", "showfilepath",
                                    os.path.join("showdir", "gcd.place"))

    node = SchedulerNode(proj, step="show", index="0")
    with node.runtime():
        with patch("siliconcompiler.utils.get_cores") as get_cores:
            get_cores.return_value = 2
            assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments == expected_vpr_args("showdir", ["--disp", "on"])


@pytest.mark.parametrize("filetype,command", [
    ("route", "set_draw_block_text 0; set_draw_block_outlines 0; set_routing_util 1; "
              "save_graphics outputs/gcd.png;"),
    ("place", "set_draw_block_text 1; set_draw_block_outlines 1; "
              "save_graphics outputs/gcd.png;"),
])
def test_vpr_screenshot_runtime_args(gcd_design, faux_fpga, write_design_files,
                                     expected_vpr_args, filetype, command):
    # Regression: screenshot read an undefined "showtype" var (KeyError); it must
    # read "showfiletype", which _set_filetype derives as place/route. The
    # interactive "--disp on" is also stripped in favour of --graphics_commands.
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("screenshot", VPRScreenshotTask())
    proj.set_flow(flow)

    faux_fpga(proj)
    write_design_files("inputs")

    VPRScreenshotTask.find_task(proj).set("var", "showfiletype", filetype)

    node = SchedulerNode(proj, step="screenshot", index="0")
    with node.runtime():
        with patch("siliconcompiler.utils.get_cores") as get_cores:
            get_cores.return_value = 2
            assert node.setup() is True
        arguments = node.task.get_runtime_arguments()

    assert arguments == expected_vpr_args("inputs", ["--graphics_commands", command])


def test_vpr_screenshot_runtime_args_invalid_filetype(gcd_design, faux_fpga, write_design_files):
    # An unknown showfiletype should raise a clear ValueError, not a KeyError.
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("screenshot", VPRScreenshotTask())
    proj.set_flow(flow)

    faux_fpga(proj)
    write_design_files("inputs")

    VPRScreenshotTask.find_task(proj).set("var", "showfiletype", "bogus")

    node = SchedulerNode(proj, step="screenshot", index="0")
    with node.runtime():
        assert node.setup() is True
        with pytest.raises(ValueError, match="Incorrect file type bogus"):
            node.task.get_runtime_arguments()
