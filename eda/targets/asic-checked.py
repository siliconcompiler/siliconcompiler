import importlib
import os
import siliconcompiler

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):

    # Define Compilation Flow
    chip.cfg['steplist']['value'] = ['import',
                                     'syn',
                                     'floorplan',
                                     'place',
                                     'cts',
                                     'route',
                                     'dfm',
                                     'lvs',
                                     'export',
                                     'drc']

    # Setup tool based on flow step
    for step in chip.cfg['steplist']['value']:
        if step == 'import':
            vendor = 'verilator'
        elif step == 'syn':
            vendor = 'yosys'
        elif step == 'export':
            vendor = 'klayout'
        elif step in ('lvs', 'drc'):
            vendor = 'magic'
        else:
            vendor = 'openroad'

        #load module dynamically on each step
        packdir = "eda." + vendor
        modulename = '.'+vendor+'_setup'
        module = importlib.import_module(modulename, package=packdir)
        setup_tool = getattr(module, 'setup_tool')
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
