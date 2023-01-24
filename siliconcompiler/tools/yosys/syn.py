import json
import re

from .yosys import setup as setup_tool

# TODO: Move to 'syn_asic'
from .yosys import prepare_synthesis_libraries, create_abc_synthesis_constraints
# TODO: Move to 'syn_fpga'
from .yosys import create_vpr_lib

def setup(chip):
    ''' Helper method for configs specific to synthesis tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = chip._get_task(step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', step, index, 'sc_syn.tcl', clobber=False)

    # Input/output requirements.
    chip.set('tool', tool, 'task', task, 'input', step, index, design + '.v')
    chip.set('tool', tool, 'task', task, 'output', step, index, design + '.vg')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '_netlist.json')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.blif')

##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # TODO: Move to 'syn_fpga'
    # copy the VPR library to the yosys input directory and render the placeholders
    if chip.get('fpga', 'arch'):
        create_vpr_lib(chip)
        return

    # TODO: Move to 'syn_asic'
    if chip.get('option', 'mode') == 'asic':
        prepare_synthesis_libraries(chip)
        create_abc_synthesis_constraints(chip)
        return

##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    #TODO: looks like Yosys exits on error, so no need to check metric
    chip.set('metric', step, index, 'errors', 0, clobber=True)
    with open("reports/stat.json", 'r') as f:
        metrics = json.load(f)
        if "design" in metrics:
            metrics = metrics["design"]

        if "area" in metrics:
            chip.set('metric', step, index, 'cellarea', float(metrics["area"]), clobber=True)
        if "num_cells" in metrics:
            chip.set('metric', step, index, 'cells', int(metrics["num_cells"]), clobber=True)

    registers = None
    with open(f"{step}.log", 'r') as f:
        for line in f:
            area_metric = re.findall(r"^SC_METRIC: area: ([0-9.]+)", line)
            if area_metric:
                chip.set('metric', step, index, 'cellarea', float(area_metric[0]), clobber=True)
            line_registers = re.findall(r"^\s*mapped ([0-9]+) \$_DFF.*", line)
            if line_registers:
                if registers is None:
                    registers = 0
                registers += int(line_registers[0])
    if registers is not None:
        chip.set('metric', step, index, 'registers', registers, clobber=True)
