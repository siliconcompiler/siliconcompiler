"""
Cocotb is a COroutine based COsimulation TestBench environment for verifying VHDL and SystemVerilog
RTL using Python.

Documentation: http://cocotb.readthedocs.org/

Sources: https://github.com/cocotb/cocotb

Installation: https://docs.cocotb.org/en/stable/install.html
"""

import os
from functools import reduce
from siliconcompiler import sc_open
from siliconcompiler.tools._common import record_metric
from siliconcompiler.tools._common import (
    get_frontend_options,
    get_input_files,
    get_tool_task,
)

from siliconcompiler.tools._common import (
    add_require_input,
    get_input_files,
    add_frontend_requires,
    get_frontend_options,
    get_tool_task,
    has_input_files,
)

from siliconcompiler.tools.surelog import setup as setup_tool

from siliconcompiler import utils
from pathlib import Path

from cocotb.runner import get_runner, get_results


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    tool = "cocotb"

    step = chip.get("arg", "step")
    index = chip.get("arg", "index")
    _, task = get_tool_task(chip, step, index)

    if not has_input_files(chip, "input", "cocotb", "python"):
        return "no files in [input,cocotb,python]"

    #chip.set("tool", tool, "sim", "icarus")

    chip.set('tool', tool, 'task', task, 'var', 'sim',
             'Instructs cocotb on what simulator to use.',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'sim', 'icarus',
             step=step, index=index, clobber=False)

    # Input/Output requirements
    # chip.set(
    #    "tool", tool, "task", task, "output", __outputfile(chip), step=step, index=index
    # )

    # Schema requirements
    add_require_input(chip, "input", "cocotb", "python")


def run(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    _, task = get_tool_task(chip, step, index)
    tool = "cocotb"
    design = chip.top()
    sources = [f"inputs/{design}.v"]

    current_path = os.getcwd()
    chip.logger.info(f"Current execution path using os.getcwd(): {current_path}")

    sim_name = chip.get('tool', tool, 'task', task, 'var', 'sim', step=step, index=index)[0]
    chip.logger.info(f"SIMULATOR {sim_name} TOOL {tool} TASK {task}")
    sim = os.getenv("SIM", str(sim_name))
    runner = get_runner(sim)

    results_xml_paths = []

    python_modules = get_input_files(chip, "input", "cocotb", "python")
    chip.logger.info(f"python srcs = {python_modules}")
    for py_test_module in python_modules:
        test_dir = Path(py_test_module).parent
        chip.logger.info(f"test_dir: {test_dir}")
        py_test_module_name = str(Path(py_test_module).stem)

        build_dir = Path(current_path) / "outputs" / py_test_module_name
        runner.build(
            sources=sources,
            hdl_toplevel=design,
            waves=True,
            build_dir=build_dir,
        )

        results_xml_paths.append(
            runner.test(
                hdl_toplevel=design,
                test_module=py_test_module_name,
                test_dir=test_dir,
                build_dir=build_dir,
                results_xml=build_dir / f"../../reports/{py_test_module_name}.xml",
                waves=True,
            )
        )

    results = [get_results(results_xml) for results_xml in results_xml_paths]

    results_sum = reduce(lambda x, y: (x[0] + y[0], x[1] + y[1]), results, (0, 0))

    tests_run = results_sum[0]
    tests_failed = results_sum[1]

    if tests_failed != 0:
        chip.logger.warn(f"Failed {tests_failed} tests out of {tests_run}.")

    return tests_failed
