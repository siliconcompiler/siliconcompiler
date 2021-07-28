import os
import subprocess
import re
import sys
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

################################
# Setup sv2v
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    chip.logger.debug("Setting up sv2v")

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'exe', 'sv2v')
    chip.add('flow', step, 'vendor', 'sv2v')

################################
# Set sv2v Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''
    options = chip.set('flow', step, 'option', [])

    topmodule = chip.cfg['design']['value'][-1]
    options.append("inputs/" + topmodule + ".v")
    options.append("--write=outputs/" + topmodule + ".v")

    #Wite back options tp cfg
    chip.set('flow', step, 'option', options)
            
    return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
