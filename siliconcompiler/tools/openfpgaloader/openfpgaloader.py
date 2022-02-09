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

    Status: SC integration WIP

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','program')
    chip.set('arg','index','0')
    chip.set('design', '<design>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' openFPGALoader setup function
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'openfpgaloader'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # tool setup
    chip.set('eda', tool, 'exe', tool, clobber=False)
    chip.set('eda', tool, 'vswitch', '--Version', clobber=False)
    chip.set('eda', tool, 'version', 'v0.5.0', clobber=False)

    options = []
    options.append("inputs" + chip.get('design') + ".bit")
    chip.add('eda', tool, 'option', step, index,  options)
