from siliconcompiler import Sim
from siliconcompiler.flows.dvflow import DVFlow

from siliconcompiler.tools.icarus.compile import CompileTask as IcarusCompileTask
from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask as IcarusCocotbExecTask

from siliconcompiler.tools.verilator.cocotb_compile import CocotbCompileTask as VerilatorCompileTask
from siliconcompiler.tools.verilator.cocotb_exec import CocotbExecTask as VerilatorCocotbExecTask


def cocotb_target(
    project: Sim,
    trace=True,
    trace_type="fst",
    seed=None,
):

    # Add cocotb flows
    project.set_flow(DVFlow(tool="icarus-cocotb"))
    project.add_dep(DVFlow(tool="verilator-cocotb"))

    ####################################
    # Setup icarus flow
    ####################################
    IcarusCompileTask.find_task(project).set_trace_enabled(trace)

    if seed is not None:
        IcarusCocotbExecTask.find_task(project).set_cocotb_randomseed(seed)

    ####################################
    # Setup verilator flow
    ####################################

    # Enable waveform tracing (must be enabled on both compile and simulate tasks)
    compile_task = VerilatorCompileTask.find_task(project)
    compile_task.set_verilator_trace(trace)
    compile_task.set_verilator_tracetype(trace_type)

    cocotb_task = VerilatorCocotbExecTask.find_task(project)
    cocotb_task.set_cocotb_trace(
        enable=trace,
        trace_type=trace_type
    )

    # Optionally set a random seed for reproducibility
    if seed is not None:
        cocotb_task.set_cocotb_randomseed(seed)
