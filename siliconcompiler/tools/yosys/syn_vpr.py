import importlib
import os
import shutil

import siliconcompiler

from .syn import setup as setup_syn

def setup(chip):
    ''' Helper method for configs specific to VPR synthesis steps.
    '''

    # Currently, VPR synthesis uses the same args as normal ASIC/FPGA synthesis.
    setup_syn(chip)

