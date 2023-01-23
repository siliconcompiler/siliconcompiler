
from .yosys import setup as setup_tool
from .yosys import setup_asic, setup_fpga

def setup(chip):
    ''' Helper method for configuring LEC steps.
    '''

    # Generic tool setup.
    setup_tool(chip)

    # Generic ASIC / FPGA mode setup.
    mode = chip.get('option', 'mode')
    if mode == 'asic':
        setup_asic(chip, task)
    elif mode == 'fpga':
        setup_fpga(chip, task)

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
