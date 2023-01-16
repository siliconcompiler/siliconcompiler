import importlib
import os
import shutil

import siliconcompiler

def setup(chip):
    ''' Helper method for configs specific to synthesis steps.
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'script', step, index, 'sc_syn.tcl', clobber=False)

    # Input/output requirements.
    chip.set('tool', tool, 'input', step, index, design + '.v')
    chip.set('tool', tool, 'output', step, index, design + '.vg')
    chip.add('tool', tool, 'output', step, index, design + '_netlist.json')
    chip.add('tool', tool, 'output', step, index, design + '.blif')
