import os
import pytest

from siliconcompiler import Flowgraph, FPGA

from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.slang import elaborate
from siliconcompiler.tools.yosys import YosysFPGA
from siliconcompiler.tools.yosys.syn_fpga import FPGASynthesis

from siliconcompiler.utils import sc_open


class TestYosysFPGA(YosysFPGA):
    def __init__(self):
        super().__init__()
        self.set_name("z1000")

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")

        with self.active_dataroot("siliconcompiler"):
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
