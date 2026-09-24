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


def _run_asic_synthesis(design, use_slang, **task_vars):
    '''Run an elaborate -> synthesis flow and return the lines of synthesis.log.'''
    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("elab_and_synth")
    flow.node('elaborate', elaborate.Elaborate())
    flow.node("synthesis", ASICSynthesis())
    flow.edge('elaborate', 'synthesis')
    proj.set_flow(flow)

    task = ASICSynthesis.find_task(proj)
    task.set_yosys_useslang(use_slang)
    for name, value in task_vars.items():
        task.set("var", name, value)

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


def _deep_hierarchy_design():
    '''A design whose top ties a constant through four levels of hierarchy.

    opt_hier crosses one level per round, so the constant only reaches the leaf
    (killing the subtractor there) if the convergence loop runs to completion.
    '''
    with open("deep.v", "w") as f:
        f.write('''
module leaf (input clk, input en, input [7:0] a, input [7:0] b, output reg [7:0] y);
    always @(posedge clk) if (en) y <= a + b; else y <= a - b;
endmodule
module lvl3 (input clk, input en, input [7:0] a, input [7:0] b, output [7:0] y);
    leaf u (.clk(clk), .en(en), .a(a), .b(b), .y(y));
endmodule
module lvl2 (input clk, input en, input [7:0] a, input [7:0] b, output [7:0] y);
    lvl3 u (.clk(clk), .en(en), .a(a), .b(b), .y(y));
endmodule
module lvl1 (input clk, input en, input [7:0] a, input [7:0] b, output [7:0] y);
    lvl2 u (.clk(clk), .en(en), .a(a), .b(b), .y(y));
endmodule
module deep (input clk, input [7:0] a, output [7:0] y);
    lvl1 u (.clk(clk), .en(1'b1), .a(a), .b(8'd0), .y(y));
endmodule
''')

    design = Design("deep")
    design.set_dataroot("deep", os.path.abspath("."))
    with design.active_fileset("rtl"), design.active_dataroot("deep"):
        design.set_topmodule("deep")
        design.add_file("deep.v")
    return design


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_hier_opt_not_used_when_flattening():
    '''opt_hier has nothing to cross once the design is flattened, so it is not run.'''
    lines = _run_asic_synthesis(_deep_hierarchy_design(), True, flatten=True)

    assert not any("-hieropt" in line for line in lines), \
        "did not expect -hieropt to be passed to synth when the design is flattened"
    assert not any("opt -hier" in line for line in lines), \
        "did not expect the opt_hier loop to run when the design is flattened"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_hier_opt_loop_converges():
    '''The opt_hier loop repeats until the design stops changing.

    A single opt_hier only advances one level of hierarchy, so a converged run has
    to report more rounds than that on a four-deep design.
    '''
    lines = _run_asic_synthesis(_deep_hierarchy_design(), True,
                                flatten=False, auto_flatten=False,
                                hier_opt=True, hier_opt_max_rounds=10)

    assert any("-hieropt" in line for line in lines), \
        "expected -hieropt to be passed to synth when the design keeps its hierarchy"

    converged = [line for line in lines if "opt_hier converged after" in line]
    assert converged, "expected the opt_hier loop to report convergence"

    rounds = int(converged[0].split("converged after")[1].split("round")[0])
    assert rounds > 1, \
        f"expected more than one round on a four-deep design, got {rounds}"
    assert not any("did not converge" in line for line in lines), \
        "expected the loop to converge within hier_opt_max_rounds"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_hier_opt_max_rounds_zero_skips_loop():
    '''hier_opt_max_rounds = 0 leaves only the opt_hier calls inside synth.'''
    lines = _run_asic_synthesis(_deep_hierarchy_design(), True,
                                flatten=False, auto_flatten=False,
                                hier_opt=True, hier_opt_max_rounds=0)

    assert any("-hieropt" in line for line in lines), \
        "expected -hieropt to still be passed to synth"
    assert not any("opt_hier converged after" in line for line in lines), \
        "did not expect the opt_hier loop to run when hier_opt_max_rounds is 0"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_opt_dff_sat_reaches_opt_dff(heartbeat_design):
    '''opt_dff_sat passes -sat through opt to opt_dff before dfflibmap.'''
    lines = _run_asic_synthesis(heartbeat_design, True, opt_dff_sat=True)

    assert any("opt_dff -sat" in line for line in lines), \
        "expected -sat to be forwarded to opt_dff"


def _shared_module_design():
    '''A design that instantiates one module twice with different constant controls.

    Nothing about the two instances is common, so opt_hier can only specialize them
    once uniquify has given each its own copy. Read with read_verilog rather than
    read_slang, which already names a module per instance.
    '''
    with open("shared.v", "w") as f:
        f.write('''
module alu (input clk, input [1:0] op, input [7:0] a, input [7:0] b, output reg [7:0] y);
    always @(posedge clk)
        case (op)
            2'd0: y <= a + b;
            2'd1: y <= a - b;
            2'd2: y <= a & b;
            default: y <= a ^ b;
        endcase
endmodule
module datapath (input clk, input [7:0] x, input [7:0] w,
                 output [7:0] sum, output [7:0] andv);
    alu u_add (.clk(clk), .op(2'd0), .a(x), .b(w), .y(sum));
    alu u_and (.clk(clk), .op(2'd2), .a(x), .b(w), .y(andv));
endmodule
''')

    design = Design("shared")
    design.set_dataroot("shared", os.path.abspath("."))
    with design.active_fileset("rtl"), design.active_dataroot("shared"):
        design.set_topmodule("datapath")
        design.add_file("shared.v")
    return design


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_hier_opt_uniquify_copies_shared_modules():
    '''uniquify gives each instance of a shared module its own copy.'''
    lines = _run_asic_synthesis(_shared_module_design(), False,
                                flatten=False, auto_flatten=False,
                                hier_opt=True, hier_opt_uniquify=True)

    assert any("Creating module datapath.u_add from alu" in line for line in lines), \
        "expected uniquify to give u_add its own copy of alu"
    assert any("Creating module datapath.u_and from alu" in line for line in lines), \
        "expected uniquify to give u_and its own copy of alu"
    assert any("uniquify converged after" in line for line in lines), \
        "expected the uniquify loop to report convergence"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_hier_opt_uniquify_disabled_keeps_shared_module():
    '''The shared module is left alone when hier_opt_uniquify is off.'''
    lines = _run_asic_synthesis(_shared_module_design(), False,
                                flatten=False, auto_flatten=False,
                                hier_opt=True, hier_opt_uniquify=False)

    assert not any("Creating module" in line for line in lines), \
        "did not expect uniquify to run when hier_opt_uniquify is disabled"


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_hier_opt_uniquify_respects_preserve_modules():
    '''A module kept for reuse is not specialized away by uniquify.'''
    lines = _run_asic_synthesis(_shared_module_design(), False,
                                flatten=False, auto_flatten=False,
                                hier_opt=True, hier_opt_uniquify=True,
                                preserve_modules=["alu"])

    assert not any("Creating module datapath.u_" in line for line in lines), \
        "did not expect a preserved module to be copied per instance"


def _asic_synthesis_node(design, **task_vars):
    '''Set up a synthesis node without running it, and return it.'''
    proj = ASIC(design)
    proj.add_fileset("rtl")
    freepdk45_demo(proj)

    flow = Flowgraph("synthflow")
    flow.node("synthesis", ASICSynthesis())
    proj.set_flow(flow)

    task = ASICSynthesis.find_task(proj)
    for name, value in task_vars.items():
        task.set("var", name, value)

    return SchedulerNode(proj, "synthesis", "0")


def test_hier_opt_setters(heartbeat_design):
    """The hierarchical optimization parameters are reachable through typed setters."""
    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        task = node.task

        task.set_yosys_hieropt(False)
        assert task.get("var", "hier_opt") is False
        task.set_yosys_hieroptuniquify(False)
        assert task.get("var", "hier_opt_uniquify") is False
        task.set_yosys_hieroptmaxrounds(4)
        assert task.get("var", "hier_opt_max_rounds") == 4
        task.set_yosys_optdffsat(True)
        assert task.get("var", "opt_dff_sat") is True


def test_hier_opt_keys_required_only_when_read(heartbeat_design):
    """sc_synth_asic.tcl reads these only when the design keeps its hierarchy."""
    node = _asic_synthesis_node(heartbeat_design, flatten=True)
    with node.runtime():
        assert node.setup() is True
        require = node.task.get("require")
        prefix = "tool,yosys,task,syn_asic,"
        assert prefix + "var,opt_dff_sat" in require
        assert prefix + "var,hier_opt" not in require
        assert prefix + "var,hier_opt_uniquify" not in require
        assert prefix + "var,hier_opt_max_rounds" not in require

    node = _asic_synthesis_node(heartbeat_design, flatten=False, hier_opt=True)
    with node.runtime():
        assert node.setup() is True
        require = node.task.get("require")
        prefix = "tool,yosys,task,syn_asic,"
        assert prefix + "var,hier_opt" in require
        assert prefix + "var,hier_opt_uniquify" in require
        assert prefix + "var,hier_opt_max_rounds" in require

    node = _asic_synthesis_node(heartbeat_design, flatten=False, hier_opt=False)
    with node.runtime():
        assert node.setup() is True
        require = node.task.get("require")
        prefix = "tool,yosys,task,syn_asic,"
        assert prefix + "var,hier_opt" in require
        assert prefix + "var,hier_opt_uniquify" not in require
        assert prefix + "var,hier_opt_max_rounds" not in require
