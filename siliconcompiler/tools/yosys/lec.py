import re

from siliconcompiler.tools.yosys import setup as setup_tool
from siliconcompiler.tools.yosys.syn_asic import prepare_synthesis_libraries, setup_asic
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric, input_provides


def setup(chip):
    '''
    Perform logical equivalence checks
    '''

    # Generic tool setup.
    setup_tool(chip)

    # Setup for asic
    setup_asic(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', 'sc_lec.tcl',
             step=step, index=index, clobber=False)

    # Input/output requirements.
    if f"{design}.lec.vg" in input_provides(chip, step, index):
        chip.set('tool', tool, 'task', task, 'input', design + '.lec.vg',
                 step=step, index=index)
    elif f"{design}.vg" in input_provides(chip, step, index):
        chip.set('tool', tool, 'task', task, 'input', design + '.vg',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'induction_steps', '10',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'induction_steps',
             'Number of induction steps for yosys equivalence checking',
             field='help')


def pre_process(chip):
    prepare_synthesis_libraries(chip)


##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    with sc_open(step + ".log") as f:
        for line in f:
            if line.endswith('Equivalence successfully proven!\n'):
                record_metric(chip, step, index, 'drvs', 0, step + ".log")
                continue

            errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
            if errors is not None:
                num_errors = int(errors.group(1))
                record_metric(chip, step, index, 'drvs', num_errors, step + ".log")
