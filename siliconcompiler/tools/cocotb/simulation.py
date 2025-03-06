"""
Silicon compiler cocotb runner.
"""

import os
from pathlib import Path

from siliconcompiler.tools._common import (
    get_input_files,
    get_tool_task,
)

from cocotb.runner import get_runner, get_results


def setup(chip):
    """
    Setup cocotb runner tool fields
    """
    step = chip.get("arg", "step")
    index = chip.get("arg", "index")
    tool, task = get_tool_task(chip, step, index)

    # Add help field to simulator var
    chip.set('tool', tool, 'task', task, 'var', 'simulator',
             'Instructs cocotb on what simulator to use. ex: icarus, verilator, etc',
             field='help')

    # User is required to specify a simulator
    chip.add(
       "tool", tool, "task", task, "require",
       ",".join(['tool', tool, 'task', task, 'var', 'simulator']),
       step=step, index=index
    )

    # Set timescale, leave unspecified to use timescale specified in HDL
    chip.set('tool', tool, 'task', task, 'var', 'timescale',
             'Set to manually specify simulation timescale. ex: ["1ns", "1ps"]',
             field='help')

    # Input requirements
    chip.set(
       "tool", tool, "task", task, "input", chip.design + ".v", step=step, index=index
    )

    chip.add(
       "tool", tool, "task", task, "require",
       "input,cocotb,python",
       step=step, index=index
    )


def run(chip):
    """
    Run cocotb
    """
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # Get input files
    sources = [f"inputs/{design}.v"]
    python_module = get_input_files(chip, "input", "cocotb", "python")[0]

    # Get parameters
    simulator_name = chip.get('tool', tool, 'task', task, 'var', 'simulator',
                              step=step, index=index)[0]

    timescale = chip.get('tool', tool, 'task', task, 'var', 'timescale',
                         step=step, index=index)
    timescale = (timescale[0], timescale[1]) if len(timescale) == 2 else None

    # Get absolute path for cocotb build_dir
    current_path = Path(os.getcwd())
    py_test_module_name = str(Path(python_module).stem)
    build_dir = current_path / py_test_module_name

    # Get path to testbench for cocotb
    test_dir = Path(python_module).parent

    # Build HDL in chosen simulator
    runner = get_runner(simulator_name)
    runner.build(
        sources=sources,
        hdl_toplevel=design,
        waves=True,
        timescale=timescale,
        build_dir=build_dir,
    )

    # Cocotb requires that results_xml be set to none when running inside pytest
    pytest_current_test = os.getenv("PYTEST_CURRENT_TEST", None)
    results_xml = None
    if not pytest_current_test:
        results_xml = build_dir / f"../reports/{py_test_module_name}.xml"

    # Run test
    _, tests_failed = get_results(runner.test(
        hdl_toplevel=design,
        test_module=py_test_module_name,
        test_dir=test_dir,
        build_dir=build_dir,
        results_xml=results_xml,
        waves=True,
    ))

    return tests_failed
