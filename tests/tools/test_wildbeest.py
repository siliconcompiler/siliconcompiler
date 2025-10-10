import os
import pytest
from siliconcompiler.flows.fpgaflow import FPGAVPRFlow
from siliconcompiler import Flowgraph
from siliconcompiler.tools import get_task
from siliconcompiler import FPGA
from siliconcompiler.tools.yosys.syn_fpga import FPGASynthesis
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.slang import elaborate
from siliconcompiler import FPGADevice, FPGA

from siliconcompiler import FPGA, Design
from siliconcompiler.flows.fpgaflow import FPGAVPROpenSTAFlow

from siliconcompiler.tools.vpr import VPRFPGA
from siliconcompiler.tools.yosys import YosysFPGA
from siliconcompiler.tools.opensta import OpenSTAFPGA
from siliconcompiler.utils import sc_open

class TestYosysFPGA(YosysFPGA):
    '''
    z1000 is the first in a series of open FPGA architectures.
    The baseline z1000 part is an architecture with 2K LUTs
    and no hard macros.
    '''
    def __init__(self):
        super().__init__()
        self.set_name("z1000")

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")
        self.package.set_vendor("ZeroASIC")
        self.set_lutsize(4)

        # self.add_yosys_registertype(["dff", "dffr", "dffe", "dffer"])
        # self.add_yosys_featureset(["async_reset", "enable"])
        with self.active_dataroot("siliconcompiler"):
            # self.set_yosys_flipfloptechmap("data/demo_fpga/tech_flops.v")
            self.set_yosys_config('data/demo_fpga/z1000_yosys_config.json')


@pytest.mark.eda
@pytest.mark.quick
def test_wildebeest_is_run(heartbeat_design):
    proj = FPGA(heartbeat_design)
    proj.add_fileset('rtl')

    flow = Flowgraph("elab_and_synth")
    flow.node('elaborate', elaborate.Elaborate())
    flow.node("synthesis", FPGASynthesis())
    flow.edge('elaborate', 'synthesis')
    proj.set_flow(flow)

    proj.set_fpga(TestYosysFPGA())
    proj.run()

    node = SchedulerNode(proj, step='synthesis', index='0')

    log_file = os.path.join(node.workdir, 'synthesis.log')
    assert os.path.exists(log_file), "synthesis log file was not created"

    with sc_open(log_file) as f:
        found = any("Executing Zero Asic 'synth_fpga' flow" in line for line in f)

    assert found, "wildebeest yosys plugin was not run (log file "\
        "did not contain expected execution message)"
