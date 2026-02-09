from unittest.mock import patch
import pytest

import os.path

from siliconcompiler import FPGA, Flowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.genfasm.bitstream import BitstreamTask
from siliconcompiler.tools.vpr import VPRFPGA


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", BitstreamTask())
    proj.set_flow(flow)

    fpga = VPRFPGA()
    fpga.set_name("testfpga")
    proj.set_fpga(fpga)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


def test_runtime_args(gcd_design):
    proj = FPGA(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("bitstream", BitstreamTask())
    proj.set_flow(flow)

    fpga = VPRFPGA()
    fpga.set_name("testfpga")
    fpga.set_vpr_archfile("arch.xml")
    fpga.set_vpr_graphfile("graph.xml")
    fpga.set_vpr_devicecode("devicecode")
    fpga.set_vpr_router_lookahead("map")
    fpga.set_vpr_clockmodel("ideal")
    fpga.set_vpr_channelwidth(128)
    proj.set_fpga(fpga)

    with open("arch.xml", "w") as f:
        f.write("<arch></arch>")
    with open("graph.xml", "w") as f:
        f.write("<graph></graph>")

    node = SchedulerNode(proj, "bitstream", "0")
    with node.runtime():
        with patch("siliconcompiler.utils.get_cores") as get_cores:
            get_cores.return_value = 2
            assert node.setup() is True
            get_cores.assert_called_once()
        arguments = node.task.get_runtime_arguments()
        assert arguments == [
            '--device', 'devicecode',
            '--verify_file_digests', 'off',
            '--write_block_usage', 'reports/block_usage.json',
            '--outfile_prefix', 'outputs/',
            os.path.abspath("arch.xml"),
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
            '--read_rr_graph', os.path.abspath("graph.xml"),
            '--route_chan_width', '128',
            'inputs/gcd.blif',
            '--net_file', 'inputs/gcd.net',
            '--place_file', 'inputs/gcd.place',
            '--route_file', 'inputs/gcd.route'
        ]
