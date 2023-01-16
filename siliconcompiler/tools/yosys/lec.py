import importlib
import os
import shutil

import siliconcompiler

def setup(chip):
    ''' Helper method for configuring LEC steps.
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'script', step, index, 'sc_lec.tcl', clobber=False)

    # Input/output requirements.
    if (not chip.valid('input', 'netlist') or
        not chip.get('input', 'netlist')):
        chip.set('tool', tool, 'input', step, index, design + '.vg')
    if not chip.get('input', 'verilog'):
        # TODO: Not sure this logic makes sense? Seems like reverse of
        # what's in TCL
        chip.set('tool', tool, 'input', step, index, design + '.v')
