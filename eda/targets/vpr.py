import importlib
import os
import siliconcompiler

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):
    chip.logger.debug("Setting up an FPGA compilation flow'")

    # Define Compilation Steps
    chip.cfg['steps']['value'] = ['import',
                                  'syn',
                                  'apr']

    chip.cfg['start']['value'] = [chip.cfg['steps']['value'][0]]
    chip.cfg['stop']['value'] = [chip.cfg['steps']['value'][-1]]

    for step in chip.cfg['steps']['value']:
        if step == 'import':
            vendor = 'verilator'
        elif step == 'syn':
            vendor = 'yosys'
        elif step == 'apr':
            vendor = 'openfpga'

        #Load per step EDA setup scripts
        packdir = "eda." + vendor
        module = importlib.import_module('.'+vendor, package=packdir)
        setup_tool = getattr(module,'setup_tool')
        setup_tool(chip, step)
