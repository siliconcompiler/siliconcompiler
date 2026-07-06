from typing import Tuple, Optional
from siliconcompiler import Sim
from siliconcompiler.flows.dvflow import (
    IcarusCocotbDVFlow, VerilatorCocotbDVFlow
)

from siliconcompiler.tools.icarus.compile import CompileTask as IcarusCompileTask
from siliconcompiler.tools.icarus.cocotb_exec import CocotbExecTask as IcarusCocotbExecTask

from siliconcompiler.tools.verilator.cocotb_compile import CocotbCompileTask as VerilatorCompileTask
from siliconcompiler.tools.verilator.cocotb_exec import CocotbExecTask as VerilatorCocotbExecTask


def cocotb_dvflow(
    project: Sim,
    trace: bool = True,
    trace_type: str = "fst",
    timescale: Optional[Tuple[str, str]] = None,
    seed: Optional[int] = None,
    np: int = 1
):
    """Configures a simulation project for a cocotb design verification run.

    Registers both the Icarus and Verilator cocotb flows on the project
    (Icarus is selected as the active flow; Verilator is added as a
    dependency so it can be selected later via
    ``project.set_flow("verilatorcocotbdvflow")``) and applies the shared
    trace, timescale, and seed settings to the compile and execution tasks
    of each flow.

    Args:
        project (Sim): The simulation project to configure.
        trace (bool, optional): Enable waveform tracing. Defaults to True.
        trace_type (str, optional): Waveform format for Verilator, 'vcd' or
            'fst'. Defaults to "fst".
        timescale (tuple[str, str], optional): Simulation timescale as a
            (unit, precision) pair, e.g. ("1ns", "1ps"). If None, no
            timescale is set. Defaults to None.
        seed (int, optional): Random seed for cocotb test reproducibility.
            If None, cocotb generates a random seed. Defaults to None.
        np (int, optional): Number of parallel simulation nodes in each
            flow. Defaults to 1.
    """

    # Add cocotb flows
    project.set_flow(IcarusCocotbDVFlow(np=np))
    project.add_dep(VerilatorCocotbDVFlow(np=np))

    ####################################
    # Setup icarus flow
    ####################################
    compile_task = IcarusCompileTask.find_task(project)

    compile_task.set_trace_enabled(trace)

    if timescale is not None:
        compile_task.set_icarus_timescale(unit=timescale[0], precision=timescale[1])

    if seed is not None:
        IcarusCocotbExecTask.find_task(project).set_cocotb_randomseed(seed)

    ####################################
    # Setup verilator flow
    ####################################

    # Enable waveform tracing (must be enabled on both compile and simulate tasks)
    compile_task = VerilatorCompileTask.find_task(project)
    compile_task.set_verilator_trace(trace)
    compile_task.set_verilator_tracetype(trace_type)

    if timescale is not None:
        compile_task.set_verilator_timescale(unit=timescale[0], precision=timescale[1])

    cocotb_task = VerilatorCocotbExecTask.find_task(project)
    cocotb_task.set_cocotb_trace(
        enable=trace,
        trace_type=trace_type
    )

    # Optionally set a random seed for reproducibility
    if seed is not None:
        cocotb_task.set_cocotb_randomseed(seed)
