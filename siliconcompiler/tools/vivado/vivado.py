import os
import importlib
import re
import shutil
import sys
import siliconcompiler


####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Vivado is an FPGA programming tool suite from Xilinx used to
    program Xilinx devices.

    Documentation: https://www.xilinx.com/products/design-tools/vivado.html

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step', 'compile')
    chip.set('arg','index', '<index>')
    setup_tool(chip)
    return chip


################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, mode='batch'):
    '''
    '''

    # default tool settings, note, not additive!
    tool = 'vivado'
    vendor = 'xilinx'
    refdir = 'tools/'+tool
    script = 'compile.tcl'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    clobber = True

    if mode == 'batch':
        clobber = True
        script = '/compile.tcl'
        option = "-mode batch -source"

    # General settings
    chip.set('eda', tool, 'exe', tool, clobber=clobber)
    chip.set('eda', tool, 'vendor', vendor, clobber=clobber)
    chip.set('eda', tool, 'vswitch', '-version', clobber=clobber)
    chip.set('eda', tool, 'version', '0', clobber=clobber)
    chip.set('eda', tool, 'refdir', step, index, refdir, clobber=clobber)
    chip.set('eda', tool, 'script', step, index, refdir + script, clobber=clobber)
    chip.set('eda', tool, 'threads', step, index, os.cpu_count(), clobber=clobber)
    chip.set('eda', tool, 'option', step, index, option, clobber=clobber)

################################
# Post_process (post executable)
################################

def post_process(chip):
     ''' Tool specific function to run after step execution
     '''
     step = chip.get('arg','step')
     index = chip.get('arg','index')

     #Return 0 if successful
     return 0
