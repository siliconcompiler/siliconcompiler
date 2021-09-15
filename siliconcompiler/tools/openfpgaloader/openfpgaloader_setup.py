import os
import subprocess
import re
import sys
import shutil
import siliconcompiler

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' openFPGALoader setup function
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'openfpgaloader'
    configured = chip.get('eda', tool, step, index, 'exe', field='lock')
    if configured and (configured != 'false'):
        chip.logger.warning('Tool already configured: ' + tool)
        return

    # tool setup
    chip.set('eda', tool, step, index, 'exe', 'openFPGALoader', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '--Version', clobber=False)
    chip.set('eda', tool, step, index, 'version', 'v0.5.0', clobber=False)

    options = []
    options.append("inputs" + chip.get('design') + ".bit")
    chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'verilator', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0
