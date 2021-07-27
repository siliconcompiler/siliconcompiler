import importlib
import os
import siliconcompiler

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):
    chip.logger.debug("Setting up an FPGA compilation flow'")

    # Define Compilation Steps
    chip.cfg['steplist']['value'] = ['import',
                                  'importvhdl',
                                  'syn',
                                  'apr',
                                  'export']

    for step in chip.cfg['steplist']['value']:
        if step == 'import':
            vendor = 'morty'
        elif step == 'importvhdl':
            vendor = 'ghdlyos'
        elif step == 'syn':
            vendor = 'yosys'
        elif step == 'apr':
            vendor = 'nextpnr'
        elif step == 'export':
            vendor = 'icepack'

        #Load per step EDA setup scripts
        packdir = "eda." + vendor
        modulename = '.'+vendor+'_setup'    
        module = importlib.import_module(modulename, package=packdir)
        setup_tool = getattr(module,'setup_tool')
        setup_tool(chip, step)
       
