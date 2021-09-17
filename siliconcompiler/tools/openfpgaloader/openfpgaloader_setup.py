import os
import subprocess
import re
import sys
import shutil
import siliconcompiler

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    The OpenFPGALoader is a universal utility for programming
    FPGAs. Compatible with many boards, cables and FPGA from
    major manufacturers (Xilinx, Altera/Intel, Lattice, Gowin,
    Efinix, Anlogic). openFPGALoader works on Linux, Windows and
    macOS.

    Documentation: https://github.com/trabucayre/openFPGALoader

    Sources: https://github.com/trabucayre/openFPGALoader

    Installation: https://github.com/trabucayre/openFPGALoader

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'program','<index>')
    return chip

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
