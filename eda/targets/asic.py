import importlib
import os
import siliconcompiler

from eda.targets.importstep import get_import_info

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):

    # Define Compilation Flow
    importstep, importvendor = get_import_info(chip)

    chip.cfg['steplist']['value'] = importstep + ['syn',
                                                  'floorplan',
                                                  'place',
                                                  'cts',
                                                  'route',
                                                  'dfm',
                                                  'export']

    chip.cfg['start']['value'] = [chip.cfg['steplist']['value'][0]]
    chip.cfg['stop']['value'] = [chip.cfg['steplist']['value'][-1]]

    # Setup tool based on flow step
    for step in chip.cfg['steplist']['value']:
        if step == 'validate':
            vendor = 'surelog'
        elif step == 'import':
            vendor = importvendor
        elif step == 'syn':
            vendor = 'yosys'
        elif step == 'export':
            vendor = 'klayout'
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
