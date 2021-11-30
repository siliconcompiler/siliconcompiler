import os
import subprocess
import re
import sys
import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    sv2v converts SystemVerilog (IEEE 1800-2017) to Verilog
    (IEEE 1364-2005), with an emphasis on supporting synthesizable
    language constructs. The primary goal of this project is to
    create a completely free and open-source tool for converting
    SystemVerilog to Verilog. While methods for performing this
    conversion already exist, they generally either rely on
    commercial tools, or are limited in scope.

    Documentation: https://github.com/zachjs/sv2v

    Sources: https://github.com/zachjs/sv2v

    Installation: https://github.com/zachjs/sv2v

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step', '<step>')
    chip.set('arg','index', '<index>')
    chip.set('design', '<design>')
    setup_tool(chip)
    return chip


################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    chip.logger.debug("Setting up sv2v")

    tool = 'sv2v'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('eda', tool, step, index, 'exe', tool)
    chip.set('eda', tool, step, index, 'vswitch', '--numeric-version')
    chip.set('eda', tool, step, index, 'version', '0.0.9')
    chip.set('eda', tool, step, index, 'threads', 4)

    # Since we run sv2v after the import/preprocess step, there should be no
    # need for specifying include dirs/defines. However we don't want to pass
    # --skip-preprocessor because there may still be unused preprocessor
    # directives not removed by the importer and passing the --skip-preprocessor
    # flag would cause sv2v to error.

    # since this step should run after import, the top design module should be
    # set and we can read the pickled Verilog without accessing the original
    # sources
    topmodule = chip.get('design')
    chip.set('eda', tool, step, index, 'option', [])
    chip.add('eda', tool, step, index, 'option', "inputs/" + topmodule + ".v")
    chip.add('eda', tool, step, index, 'option', "--write=outputs/" + topmodule + ".v")

def parse_version(stdout):
    # 0.0.7-130-g1aa30ea
    return stdout.split('-')[0]

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip)
    # write out results
    chip.writecfg(output)
