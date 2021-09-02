import os
import subprocess
import re
import sys

import siliconcompiler
from siliconcompiler.schema_utils import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Sets up default settings on a per step basis
    '''

    # Standard Setup
    chip.set('eda', tool, step, index, 'exe', 'surelog')
    chip.set('eda', tool, step, index, 'vendor', 'sureolog')
    chip.set('eda', tool, step, index, 'version', '0.0')
    chip.set('eda', tool, step, index, 'threads', '4')

    # -parse is slow but ensures the SV code is valid
    # we might want an option to control when to enable this
    # or replace surelog with a SV linter for the validate step
    options = []
    options.append('-parse')
    options.append('-I' + "../../../")

    #Source Level Controls

    for value in chip.cfg['ydir']['value']:
        options.append('-y ' + schema_path(value))

    for value in chip.cfg['vlib']['value']:
        options.append('-v ' + schema_path(value))

    for value in chip.cfg['idir']['value']:
        options.append('-I' + schema_path(value))

    for value in chip.cfg['define']['value']:
        options.append('+define+' + schema_path(value))

    for value in chip.cfg['cmdfile']['value']:
        options.append('-f ' + schema_path(value))

    for value in chip.cfg['source']['value']:
        options.append(schema_path(value))

    # Wite back options tp cfg
    chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Post_process (post executable)
################################

def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''
    # setting top module of design
    if step in 'import':
        modules = 0
        if len(chip.cfg['design']['value']) < 1:
            with open("slpp_all/surelog.log", "r") as open_file:
                for line in open_file:
                    modmatch = re.match(r'Top level module "\w+@(\w+)"', line)
                    if modmatch:
                        modules = modules + 1
                        topmodule = modmatch.group(1)
            # Only setting design when possible
            if (modules > 1) & (chip.cfg['design']['value'] == ""):
                chip.logger.error('Multiple modules found during import, \
                but sc_design was not set')
                sys.exit()
            else:
                chip.logger.info('Setting design (topmodule) to %s', topmodule)
                chip.cfg['design']['value'].append(topmodule)
        else:
            topmodule = chip.cfg['design']['value'][-1]

        subprocess.run("cp slpp_all/surelog.uhdm " + "outputs/" + topmodule + ".uhdm",
                       shell=True)

    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='lint', index='0')
    # write out results
    chip.writecfg(output)
