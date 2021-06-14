import importlib
import os
import siliconcompiler

from eda.targets.importstep import get_import_info

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):
    chip.logger.debug("Setting up an FPGA compilation flow'")

    # Define Compilation Steps
    importstep, importvendor = get_import_info(chip)

    chip.cfg['steplist']['value'] = importstep + ['syn',
                                                  'apr']

    for step in chip.cfg['steplist']['value']:
        if step == 'validate':
            vendor = 'surelog'
        elif step == 'import':
            vendor = importvendor
        elif step == 'syn':
            vendor = 'yosys'
        elif step == 'apr':
            vendor = 'openfpga'

        #Load per step EDA setup scripts
        packdir = "eda." + vendor
        modulename = '.'+vendor+'_setup'
        module = importlib.import_module(modulename, package=packdir)
        setup_tool = getattr(module,'setup_tool')
        setup_tool(chip, step)
