import importlib
import os
import siliconcompiler

####################################################
# EDA Setup
####################################################
def setup_eda(chip, name=None):

    # Define Compilation Flow
    importstep = ['import'] # standard verilog import just runs Verilator
    importvendor = 'verilator'
    chip.cfg['start']['value'] = ['import']

    if chip.get('sv')[-1]:
        if chip.get('ir')[-1] == 'uhdm':
            # UHDM import only runs SureLog in UHDM mode
            importstep = ['import']
            importvendor = 'surelog'
        else:
            # Verilog SV import runs SureLog to validate SV and then sv2v to convert
            # Since sv2v's parser is not strict we first parse using SureLog to ensure
            # that the input SV is valid. Compiling invalid SV using sv2v may result
            # in valid but buggy Verilog code, which we want to avoid.
            importstep = ['validate', 'import']
            chip.cfg['start']['value'] = ['validate']
            importvendor = 'sv2v'

    chip.cfg['stop']['value'] = ['export']

    chip.cfg['steplist']['value'] = importstep + ['syn',
                                                  'floorplan',
                                                  'place',
                                                  'cts',
                                                  'route',
                                                  'dfm',
                                                  'export']

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
