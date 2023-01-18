import os
import sys
import shutil

import siliconcompiler

def setup(chip):
    ''' Configure Surelog settings particular to the 'import' step.
    '''

    tool = 'surelog'
    task = 'import'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Runtime parameters.
    chip.set('tool', tool, 'task', task, 'threads', step, index,  os.cpu_count(), clobber=False)

    # Command-line options.
    options = []
    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options.append('-parse')
    # We don't use UHDM currently, so disable. For large designs, this file is
    # very big and takes a while to write out.
    options.append('-nouhdm')
    # Wite back options to cfg
    chip.add('tool', tool, 'task', task, 'option', step, index, options)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', step, index, chip.top() + '.v')

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['input', 'rtl', 'verilog']))
