import pytest

import os.path

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import ASIC, Design, Flowgraph, FPGA
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.yosys.lec_asic import ASICLECTask
from siliconcompiler.tools.slang import elaborate
from siliconcompiler.tools.yosys import YosysFPGA
from siliconcompiler.tools.yosys.syn_fpga import FPGASynthesis

from tools.inputimporter import ImporterTask

from siliconcompiler.utils import sc_open


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_version(gcd_design):
    proj = ASIC(gcd_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("testflow")
    flow.node("version", ASICLECTask())
    proj.set_flow(flow)

    node = SchedulerNode(proj, "version", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.check_exe_version(node.task.get_exe_version()) is True


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_yosys_lec(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lec")
    flow.node('import', ImporterTask())
    flow.node("lec", ASICLECTask())
    flow.edge('import', 'lec')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'lec', 'foo.v'))
    ImporterTask.find_task(proj).add("var", "input_files",
                                     os.path.join(datadir, 'lec', 'foo.vg'))

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='lec', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_yosys_lec_broken(datadir):
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("lec")
    flow.node('import', ImporterTask())
    flow.node("lec", ASICLECTask())
    flow.edge('import', 'lec')
    proj.set_flow(flow)

    ImporterTask.find_task(proj).add(
        "var", "input_files", os.path.join(datadir, 'lec', 'broken', 'foo.v'))
    ImporterTask.find_task(proj).add(
        "var", "input_files", os.path.join(datadir, 'lec', 'broken', 'foo.vg'))

    assert proj.run()
    assert proj.history("job0").get('metric', 'drvs', step='lec', index='0') == 2


class DummyYosysFPGA(YosysFPGA):
    def __init__(self):
        super().__init__()
        self.set_name("test_z1000")

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")

        with self.active_dataroot("siliconcompiler"):
            self.set_yosys_config('data/demo_fpga/z1000_yosys_config.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_wildebeest_is_run(heartbeat_design):
    proj = FPGA(heartbeat_design)
    proj.add_fileset('rtl')

    flow = Flowgraph("elab_and_synth")
    flow.node('elaborate', elaborate.Elaborate())
    flow.node("synthesis", FPGASynthesis())
    flow.edge('elaborate', 'synthesis')
    proj.set_flow(flow)

    proj.set_fpga(DummyYosysFPGA())
    proj.run()

    node = SchedulerNode(proj, step='synthesis', index='0')

    log_file = os.path.join(node.workdir, 'synthesis.log')
    assert os.path.exists(log_file), "synthesis log file was not created"

    with sc_open(log_file) as f:
        found = any("Executing Zero Asic 'synth_fpga' flow" in line for line in f)

    assert found, "wildebeest yosys plugin was not run (log file "\
        "did not contain expected execution message)"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_memory_init_files(datadir):
    """Test that .hex and .mem files are properly registered in synthesis."""
    design = Design("memory_test")

    with design.active_fileset("rtl"):
        design.set_topmodule("memory_test")
        design.add_file(os.path.join(datadir, "memory_init", "memory_test.v"))
        design.add_file(os.path.join(datadir, "memory_init", "init.hex"))
        design.add_file(os.path.join(datadir, "memory_init", "init.mem"))

    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    # Set up a synthesis node to test file collection
    node = SchedulerNode(proj, step='synthesis', index='0')
    with node.runtime():
        node.setup()

        # Verify the synthesis task has the memory files marked as required
        task = node.task
        hex_files = task.get_fileset_file_keys("hex")
        mem_files = task.get_fileset_file_keys("mem")

        assert len(hex_files) > 0, ".hex files were not detected in filesets"
        assert len(mem_files) > 0, ".mem files were not detected in filesets"

        # hex_files and mem_files are tuples of (object, keypath)
        # Verify the files can be found using the design object and its keypath
        hex_lib, hex_key = hex_files[0]
        mem_lib, mem_key = mem_files[0]

        hex_found = hex_lib.find_files(*hex_key)
        mem_found = mem_lib.find_files(*mem_key)

        assert hex_found, ".hex file could not be resolved"
        assert mem_found, ".mem file could not be resolved"
        assert "init.hex" in str(hex_found), f"Expected init.hex in {hex_found}"
        assert "init.mem" in str(mem_found), f"Expected init.mem in {mem_found}"
