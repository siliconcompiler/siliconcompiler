import pytest

import os.path

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import ASIC, Design, Flowgraph, FPGA
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.yosys.lec_asic import ASICLECTask
from siliconcompiler.tools.yosys.open import OpenTask as YosysOpen
from siliconcompiler.tools.slang import elaborate
from siliconcompiler.tools.yosys import YosysFPGA
from siliconcompiler.tools.yosys.syn_asic import ASICSynthesis
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


def _run_asic_synthesis(design, use_slang):
    '''Run an elaborate -> synthesis flow and return the lines of synthesis.log.'''
    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("elab_and_synth")
    flow.node('elaborate', elaborate.Elaborate())
    flow.node("synthesis", ASICSynthesis())
    flow.edge('elaborate', 'synthesis')
    proj.set_flow(flow)

    ASICSynthesis.find_task(proj).set_yosys_useslang(use_slang)

    proj.run()

    node = SchedulerNode(proj, step='synthesis', index='0')
    log_file = os.path.join(node.workdir, 'synthesis.log')
    assert os.path.exists(log_file), "synthesis log file was not created"

    with sc_open(log_file) as f:
        return f.readlines()


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_synthesis_uses_slang(heartbeat_design):
    '''The slang frontend is used to read the design when use_slang is set.'''
    lines = _run_asic_synthesis(heartbeat_design, use_slang=True)

    assert any("read_slang" in line for line in lines), \
        "expected the slang frontend (read_slang) to be used"
    assert not any("read_verilog -noblackbox" in line for line in lines), \
        "did not expect the design to be read with read_verilog when slang is enabled"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_synthesis_does_not_use_slang(heartbeat_design):
    '''The design is read with read_verilog when use_slang is not set.'''
    lines = _run_asic_synthesis(heartbeat_design, use_slang=False)

    assert any("read_verilog -noblackbox" in line for line in lines), \
        "expected the design to be read with read_verilog when slang is disabled"
    assert not any("read_slang" in line for line in lines), \
        "did not expect the slang frontend (read_slang) to be used"


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


def test_syn_fpga_marks_design_params_required(heartbeat_design):
    """sc_read_design_verilog applies the design parameters, so they must be hashed."""
    heartbeat_design.set_param("N", "8", "rtl")

    proj = FPGA(heartbeat_design)
    proj.add_fileset("rtl")

    flow = Flowgraph("synthflow")
    flow.node("synthesis", FPGASynthesis())
    proj.set_flow(flow)
    proj.set_fpga(DummyYosysFPGA())

    node = SchedulerNode(proj, "synthesis", "0")
    with node.runtime():
        assert node.setup() is True
        assert "library,heartbeat,fileset,rtl,param,N" in node.task.get("require")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_yosys_open(datadir):
    '''The open task reads the liberty and netlist, then stops.'''
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("foo")

    proj = ASIC(design)
    proj.add_fileset(["rtl"])
    freepdk45_demo(proj)

    flow = Flowgraph("open")
    flow.node("open", YosysOpen())
    proj.set_flow(flow)

    task = YosysOpen.find_task(proj)
    task.set_showfilepath(os.path.join(datadir, "lec", "foo.vg"))
    # Without this the session is a breakpoint and the node never returns.
    task.set_showexit(True)

    assert proj.run()

    workdir = os.path.join("build", "testdesign", "job0", "open", "0")

    with sc_open(os.path.join(workdir, "open.log")) as f:
        log = f.read()

    assert os.path.isfile(os.path.join(workdir, "inputs", "foo.vg"))
    assert "Reading netlist verilog: inputs/foo.vg" in log
    # the prepared synthesis liberty is read, so the netlist binds to real cells
    assert "read_liberty" in log
    assert "NangateOpenCellLibrary_typical" in log
    assert "2   DFF_X1" in log

    # showexit drops -C, so yosys terminates instead of waiting at its shell
    assert "-C" not in proj.history("job0").get(
        "record", "toolargs", step="open", index="0")
    # the node manifest and nothing else -- no design artifacts
    assert os.listdir(os.path.join(workdir, "outputs")) == ["testdesign.pkg.json"]
