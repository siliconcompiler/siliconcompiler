import re

from siliconcompiler.tools.yosys.yosys import setup as setup_tool
from siliconcompiler.tools.yosys.syn_asic import setup_asic
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric


def setup(chip):
    '''
    Perform logical equivalence checks
    '''

    # Generic tool setup.
    setup_tool(chip)

    # Generic setup.
    setup_asic(chip)

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', 'sc_lec.tcl',
             step=step, index=index, clobber=False)

    # Input/output requirements.
    if not chip.valid('input', 'netlist', 'verilog') or \
       not chip.get('input', 'netlist', 'verilog', step=step, index=index):
        chip.set('tool', tool, 'task', task, 'input', design + '.vg', step=step, index=index)
    # if not chip.get('input', 'rtl', 'verilog'):
        # TODO: Not sure this logic makes sense? Seems like reverse of tcl
        # chip.set('tool', tool, 'task', task, 'input', design + '.v', step=step, index=index)


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
