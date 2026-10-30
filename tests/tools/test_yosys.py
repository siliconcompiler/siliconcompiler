import gzip
import json
import pytest

import os.path

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import ASIC, Design, Flowgraph, FPGA, StdCellLibrary, utils
from siliconcompiler.fpgas.lattice_ice40 import ICE40Up5k_sg48
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.tools.yosys.lec_asic import ASICLECTask
from siliconcompiler.tools.yosys.open import OpenTask as YosysOpen
from siliconcompiler.tools.yosys.prepareLib import process_liberty_file
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


def _initial_value_design():
    '''Three flops on the same input that differ only in their initial value.

    r1 is given a 1, and r2 is a 2-state bit, which slang gives an implicit 0.
    '''
    with open("pwron.sv", "w") as f:
        f.write('''
module pwron (input clk, input d, output q1, output q2, output q3);
    reg r1 = 1'b1;
    bit r2;
    logic r3;
    always_ff @(posedge clk) begin
        r1 <= d;
        r2 <= d;
        r3 <= d;
    end
    assign q1 = r1;
    assign q2 = r2;
    assign q3 = r3;
endmodule
''')

    design = Design("pwron")
    design.set_dataroot("pwron", os.path.abspath("."))
    with design.active_fileset("rtl"), design.active_dataroot("pwron"):
        design.set_topmodule("pwron")
        design.add_file("pwron.sv")
    return design


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("use_slang", [True, False])
def test_asic_synthesis_drops_initial_values(use_slang):
    '''An ASIC flop has no power-on value, so the three flops merge into one on either frontend.'''
    _run_asic_synthesis(_initial_value_design(), use_slang)

    with open("build/pwron/job0/synthesis/0/reports/stat.json") as f:
        assert json.load(f)["design"]["num_cells_by_type"]["DFF_X1"] == 1


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.parametrize("use_slang", [True, False])
def test_fpga_synthesis_keeps_initial_values(use_slang):
    '''An ice40 flop powers up at 0, so r1's 1 takes LUTs to invert it on either frontend.'''
    proj = FPGA(_initial_value_design())
    proj.add_fileset("rtl")

    flow = Flowgraph("elab_and_synth")
    flow.node("elaborate", elaborate.Elaborate())
    flow.node("synthesis", FPGASynthesis())
    flow.edge("elaborate", "synthesis")
    proj.set_flow(flow)
    proj.set_fpga(ICE40Up5k_sg48())
    FPGASynthesis.find_task(proj).set_yosys_useslang(use_slang)

    proj.run()

    with open("build/pwron/job0/synthesis/0/reports/stat.json") as f:
        assert "SB_LUT4" in json.load(f)["design"]["num_cells_by_type"]


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


def test_yosys_max_threads_from_task_threads(heartbeat_design):
    """Every yosys task, not only syn_asic, hands its thread count to yosys's environment."""
    proj = FPGA(heartbeat_design)
    proj.add_fileset("rtl")
    proj.option.scheduler.set_maxthreads(3)

    flow = Flowgraph("synthflow")
    flow.node("synthesis", FPGASynthesis())
    proj.set_flow(flow)
    proj.set_fpga(DummyYosysFPGA())

    node = SchedulerNode(proj, "synthesis", "0")
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_threads() == 3
        assert node.task.get_runtime_environmental_variables()["YOSYS_MAX_THREADS"] == "3"


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
def test_hier_opt_converges():
    '''opt_hier runs to convergence, carrying the top's constants down four levels to the leaf.'''
    lines = _run_asic_synthesis(_deep_hierarchy_design(), True,
                                flatten=False, auto_flatten=False,
                                hier_opt=True, hier_opt_max_rounds=10)

    assert any("-hieropt" in line for line in lines), \
        "expected -hieropt to be passed to synth when the design keeps its hierarchy"

    with open("build/deep/job0/synthesis/0/reports/stat.json") as f:
        modules = json.load(f)["modules"]
    leaf = [info["num_cells_by_type"] for name, info in modules.items()
            if name.startswith("\\leaf")]
    assert len(leaf) == 1
    # With en tied high and b to zero, the adder and subtractor are gone, leaving the
    # flops and any buffers abc puts in front of them.
    assert {cell: count for cell, count in leaf[0].items()
            if not cell.startswith("BUF_")} == {"DFF_X1": 8}


@pytest.mark.timeout(60)
@pytest.mark.parametrize("message", [
    "Disconnected 3 input bits of instance 'u' (type 'leaf') in 'top'",
    "Substituting constant for 2 output bits of instance 'u' (type 'leaf') in 'top'",
    "Replacing 2 output bits with tie-togethers on instance 'u' of 'leaf' in 'top'",
    "Disconnected unused output terminal 'y' in module 'leaf'",
    "Substituting constant 1'1 for input terminal 'a' in module 'leaf'",
    "Replacing 2 input terminal bits with tie-togethers in module 'leaf'"])
def test_hier_opt_loop_sees_every_change(tcl_interp, message):
    '''Each message opt_hier prints for a change keeps the loop going for another round.'''
    interp = tcl_interp("yosys/scripts/common/procs.tcl")
    interp.setvar("message", message)
    interp.eval("""
        set rounds 0
        proc yosys { cmd args } {
            if { $cmd == "tee" && [incr ::rounds] == 1 } {
                return $::message
            }
            return ""
        }""")

    assert interp.eval("sc_opt_hier_loop 10 {}") == "2"


@pytest.mark.timeout(60)
@pytest.mark.parametrize("value", ['"hello"', "8'hff", "8"])
def test_apply_params_passes_value_unchanged(tcl_interp, value):
    '''chparam gets the param value as written; quoting a string is the user's job.'''
    interp = tcl_interp("yosys/scripts/common/procs.tcl")
    interp.setvar("value", value)
    interp.eval("""
        set sc_topmodule t
        proc sc_cfg_exists { args } { return 1 }
        proc sc_cfg_get { args } {
            if { [lindex $args end] == "param" } {
                return [dict create TYPE $::value]
            }
            return x
        }
        proc yosys { cmd args } {
            if { $cmd == "tee" } {
                return TYPE
            }
            if { $cmd == "chparam" && [lindex $args 0] == "-set" } {
                set ::got [lrange $args 1 end]
            }
            return ""
        }
        sc_apply_params""")

    assert interp.eval("lindex $::got 0") == "TYPE"
    assert interp.eval("lindex $::got 1") == value
    assert interp.eval("lindex $::got 2") == "t"


def test_hier_opt_max_rounds_rejects_zero(heartbeat_design):
    """hier_opt_max_rounds rejects zero, which would run neither opt_hier loop."""
    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        with pytest.raises(ValueError):
            node.task.set_yosys_hieroptmaxrounds(0)


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


@pytest.mark.parametrize("modules", [
    {"\\heartbeat": {"num_cells": 1, "num_submodules": 1, "area": 12.0,
                     "num_cells_by_type": {"XOR2": 1, "mid": 1}},
     "\\mid": {"num_cells": 1, "num_submodules": 2, "area": 7.0,
               "num_cells_by_type": {"OR2": 1, "leaf": 2}},
     "\\leaf": {"num_cells": 1, "num_submodules": 0, "area": 2.0,
                "num_cells_by_type": {"AND2": 1}}},
    {"\\heartbeat": {"num_cells": 2, "area": 5.0, "num_cells_by_type": {"XOR2": 1, "mid": 1}},
     "\\mid": {"num_cells": 3, "area": 3.0, "num_cells_by_type": {"OR2": 1, "leaf": 2}},
     "\\leaf": {"num_cells": 1, "area": 2.0, "num_cells_by_type": {"AND2": 1}}}],
    ids=["yosys-0.57-stat", "yosys-0.56-stat"])
def test_cell_area_report_counts_each_level_once(heartbeat_design, modules):
    '''Each instance's area and cell count include its submodules once, in either stat format.'''
    netlist = {"modules": {
        "heartbeat": {"cells": {"g": {"type": "XOR2"}, "m0": {"type": "mid"}}},
        "mid": {"cells": {"g": {"type": "OR2"}, "l0": {"type": "leaf"}, "l1": {"type": "leaf"}}},
        "leaf": {"cells": {"g": {"type": "AND2"}}}}}

    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        assert node.setup() is True
        os.makedirs("reports")
        os.makedirs("outputs")
        with open("reports/stat.json", "w") as f:
            json.dump({"modules": modules, "design": {"num_cells": 4, "area": 12.0}}, f)
        with open("outputs/heartbeat.netlist.json", "w") as f:
            json.dump(netlist, f)

        node.task._generate_cell_area_report()

    with open("reports/hierarchical_cell_area.json") as f:
        report = json.load(f)
    assert {name: (entry["cellarea"], entry["cellcount"]) for name, entry in report.items()} == {
        "heartbeat": (12.0, 4), "m0": (7.0, 3), "m0.l0": (2.0, 1), "m0.l1": (2.0, 1)}


def test_registers_counts_every_instance(heartbeat_design):
    '''registers counts the flops in every instance of a kept module, not in each module once.'''
    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        assert node.setup() is True
        # dfflibmap's lines for a leaf module instantiated twice, then for the top.
        with open(node.task.get_logpath("exe"), "w") as f:
            f.write("  mapped 16 $_DFF_P_ cells to \\DFF_X1 cells.\n"
                    "  mapped 1 $_DFF_PN0_ cells to \\DFFR_X1 cells.\n"
                    "  mapped 1 $_DFF_P_ cells to \\DFF_X1 cells.\n")
        os.makedirs("reports")
        with open("reports/stat.json", "w") as f:
            json.dump({"design": {"num_cells_by_type": {
                "DFF_X1": 33, "DFFR_X1": 2, "NAND2_X1": 40, "leaf": 2}}}, f)

        node.task._synthesis_post_process()

    assert node.project.get("metric", "registers", step="synthesis", index="0") == 35


@pytest.mark.parametrize("args", [["-c", "sc_synth_asic.tcl"], ["-C", "-c", "sc_synth_asic.tcl"]])
def test_yosys_replay_modes(args):
    """replay.sh --shell adds -C once, so yosys enters its Tcl shell when the script ends."""
    assert ASICSynthesis().replay_modes(args) == {"shell": ["-C", "-c", "sc_synth_asic.tcl"]}


def test_yosys_lib_prep_threads_honor_task(heartbeat_design):
    """Explicit task threads are honored for lib prep even when maxthreads differs."""
    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        node.task.set("threads", 3)
        node.task.project.option.scheduler.set_maxthreads(8)
        assert node.setup() is True
        assert node.task.get_threads() == 3


def test_yosys_lib_prep_threads_fallback_maxthreads(heartbeat_design):
    """Scheduler maxthreads is used when task threads is unset."""
    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        node.task.project.option.scheduler.set_maxthreads(4)
        assert node.setup() is True
        assert node.task.get_threads() == 4


def test_yosys_lib_prep_threads_fallback_cores(heartbeat_design):
    """Hardware cores are used when neither task threads nor maxthreads is set."""
    node = _asic_synthesis_node(heartbeat_design)
    with node.runtime():
        assert node.setup() is True
        assert node.task.get_threads() == utils.get_cores()


def test_process_liberty_file_output_file():
    """process_liberty_file writes output to output_file when provided."""
    raw = (
        "library (demo) {\n"
        "  capacitive_load_unit (0.001,pf);\n"
        "  cell (inv) {\n"
        "    pin (A) {\n"
        "      original_pin : true;\n"
        "    }\n"
        "    pin (Y) {\n"
        "      function : !A ;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    with open("input.lib", "w") as f:
        f.write(raw)

    content = process_liberty_file("input.lib", output_file="output.lib")
    assert os.path.exists("output.lib")
    with open("output.lib") as f:
        saved = f.read()
    assert saved == content
    assert "capacitive_load_unit (1,ff);" in saved
    assert "/*       original_pin : true; */;" in saved
    assert ': "!A" ;' in saved


def _create_multi_lib_project():
    design = Design("top")
    design.set_dataroot("top", ".")
    with design.active_fileset("rtl"), design.active_dataroot("top"):
        design.set_topmodule("top")

    raw1 = (
        "library (lib1) {\n"
        "  capacitive_load_unit (0.001,pf);\n"
        "  cell (c1) {\n"
        "    pin (A) {\n"
        "      original_pin : true;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    raw2 = (
        "library (lib2) {\n"
        "  cell (c2) {\n"
        "    pin (Y) {\n"
        "      function : !A ;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )

    with open("c1.lib", "w") as f:
        f.write(raw1)
    with gzip.open("c2.lib.gz", "wt") as f:
        f.write(raw2)

    l1 = StdCellLibrary("lib1")
    l1.set_dataroot("lib1", ".")
    l1.add_file("c1.lib", dataroot="lib1", fileset="typical")
    l1.add("asic", "libcornerfileset", "typical", "nldm", "typical")

    l2 = StdCellLibrary("lib2")
    l2.set_dataroot("lib2", ".")
    l2.add_file("c2.lib.gz", dataroot="lib2", fileset="typical")
    l2.add("asic", "libcornerfileset", "typical", "nldm", "typical")

    proj = ASIC(design)
    proj.add_fileset("rtl")
    proj.add_asiclib(l1)
    proj.add_asiclib(l2)
    proj.set("asic", "delaymodel", "nldm")

    flow = Flowgraph("synthflow")
    flow.node("synthesis", ASICSynthesis())
    proj.set_flow(flow)
    return proj


def test_yosys_prepare_synthesis_libraries_parallel():
    """Libraries are processed in parallel honoring task threads count."""
    proj = _create_multi_lib_project()
    node = SchedulerNode(proj, "synthesis", "0")
    with node.runtime():
        node.task.set("threads", 4)
        node.task.set("var", "synthesis_corner", "typical")
        node.task._prepare_synthesis_libraries()

        libs = node.task.get("var", "synthesis_libraries")
        assert len(libs) == 2
        assert libs[0].endswith("sc_lib1_c1.lib")
        assert libs[1].endswith("sc_lib2_c2.lib")

        for fpath in libs:
            assert os.path.exists(fpath)

        with open(libs[0]) as f:
            assert "capacitive_load_unit (1,ff);" in f.read()
        with open(libs[1]) as f:
            assert ': "!A" ;' in f.read()


def test_yosys_prepare_synthesis_libraries_serial():
    """Libraries are processed serially when threads is 1."""
    proj = _create_multi_lib_project()
    node = SchedulerNode(proj, "synthesis", "0")
    with node.runtime():
        node.task.set("threads", 1)
        node.task.set("var", "synthesis_corner", "typical")
        node.task._prepare_synthesis_libraries()

        libs = node.task.get("var", "synthesis_libraries")
        assert len(libs) == 2
        assert libs[0].endswith("sc_lib1_c1.lib")
        assert libs[1].endswith("sc_lib2_c2.lib")


def test_yosys_prepare_synthesis_libraries_exception():
    """Worker exceptions during lib prep are raised to the caller."""
    proj = _create_multi_lib_project()
    os.remove("c1.lib")
    node = SchedulerNode(proj, "synthesis", "0")
    with node.runtime():
        node.task.set("threads", 2)
        node.task.set("var", "synthesis_corner", "typical")
        with pytest.raises(FileNotFoundError):
            node.task._prepare_synthesis_libraries()
