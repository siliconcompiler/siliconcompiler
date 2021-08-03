import os
import subprocess
import re
import sys

import siliconcompiler
from siliconcompiler.schema import schema_istrue
from siliconcompiler.schema import schema_path

################################
# Setup sv2v
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''
    chip.logger.debug("Setting up sv2v")


    tool = 'sv2v'

    chip.set('eda', tool, step, 'threads', '4')
    chip.set('eda', tool, step, 'format', 'cmdline')
    chip.set('eda', tool, step, 'copy', 'false')
    chip.set('eda', tool, step, 'exe', tool)
    chip.set('eda', tool, step, 'vendor', tool)

    options = []

    # Include cwd in search path
    options.append('-I' + "../../../")

    for value in chip.cfg['idir']['value']:
        options.append('-I' + schema_path(value))

    for value in chip.cfg['define']['value']:
        options.append('-D ' + schema_path(value))

    for value in chip.cfg['source']['value']:
        options.append(schema_path(value))

    #Wite back options tp cfg
    chip.set('eda', tool, step, 'option', options)

    return options


################################
# Post_process (post executable)
################################
def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    # setting top module of design
    modules = 0
    if len(chip.cfg['design']['value']) < 1:
        with open("sv2v.log", "r") as open_file:
            for line in open_file:
                modmatch = re.match(r'^module\s+(\w+)', line)
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

    subprocess.run("cp sv2v.log outputs/" + topmodule + ".v", shell=True)


    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='transalate')
    # write out results
    chip.writecfg(output)
