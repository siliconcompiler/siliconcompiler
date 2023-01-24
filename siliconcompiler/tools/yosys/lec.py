import re

from .yosys import setup as setup_tool

def setup(chip):
    ''' Helper method for configuring LEC steps.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'yosys'
    task = 'lec'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', step, index, 'sc_lec.tcl', clobber=False)

    # Input/output requirements.
    if (not chip.valid('input', 'netlist', 'verilog') or
        not chip.get('input', 'netlist', 'verilog')):
        chip.set('tool', tool, 'task', task, 'input', step, index, design + '.vg')
    #if not chip.get('input', 'rtl', 'verilog'):
        # TODO: Not sure this logic makes sense? Seems like reverse of tcl
        #chip.set('tool', tool, 'task', task, 'input', step, index, design + '.v')

##################################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    with open(step + ".log") as f:
        for line in f:
            if line.endswith('Equivalence successfully proven!\n'):
                chip.set('metric', step, index, 'drvs', 0, clobber=True)
                continue

            errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
            if errors is not None:
                num_errors = int(errors.group(1))
                chip.set('metric', step, index, 'drvs', num_errors, clobber=True)
