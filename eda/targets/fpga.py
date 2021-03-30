import importlib
import os
import siliconcompiler

####################################################
# EDA Setup
####################################################
def setup_eda(chip, target=None):
    chip.logger.debug("Setting up an FPGA compilation flow'")     


    if target == 'ice40':    
        # Define Compilation Steps
        chip.cfg['steps']['value'] = ['import',
                                      'syn',
                                      'apr',
                                      'export']

        for step in chip.cfg['steps']['value']:         
            if step == 'import':
                vendor = 'verilator'
            elif step == 'syn':
                vendor = 'yosys'
            elif step == 'apr':
                vendor = 'nextpnr'
            elif step == 'export':
                vendor = 'icepack'
            #Load per step EDA setup scripts
            packdir = "eda." + vendor    
            module = importlib.import_module('.'+vendor, package=packdir)
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
