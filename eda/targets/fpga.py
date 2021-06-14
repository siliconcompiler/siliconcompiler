import importlib
import os
import siliconcompiler

from eda.targets.importstep import get_import_info

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):
    chip.logger.debug("Setting up an FPGA compilation flow'")     


    if name == 'ice40':
        # Define Compilation Steps
        importstep, importvendor, start = get_import_info(chip)
        chip.cfg['start']['value'] = start
        chip.cfg['stop']['value'] = ['export']

        chip.cfg['steplist']['value'] = importstep + ['syn',
                                                      'apr',
                                                      'export']

        for step in chip.cfg['steplist']['value']:         
            if step == 'validate':
                vendor = 'surelog'
            elif step == 'import':
                vendor = importvendor
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

#########################
if __name__ == "__main__":    

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_eda(chip)
    # write out result
    chip.writecfg(output)
