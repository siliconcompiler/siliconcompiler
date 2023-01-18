import importlib
import os
import shutil

import siliconcompiler

def setup(chip):
    ''' Helper method for configuring LEC steps.
    '''

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
