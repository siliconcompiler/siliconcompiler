import os
import subprocess
import re
import sys
import siliconcompiler
from siliconcompiler.schema_utils import schema_path

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''sv2v converts SystemVerilog to Verilog (IEEE 1364-2005)

    sv2v converts SystemVerilog (IEEE 1800-2017) to Verilog
    (IEEE 1364-2005), with an emphasis on supporting synthesizable
    language constructs. The primary goal of this project is to
    create a completely free and open-source tool for converting
    SystemVerilog to Verilog. While methods for performing this
    conversion already exist, they generally either rely on
    commercial tools, or are limited in scope.

    Documentation:
    * https://github.com/zachjs/sv2v

    Installation instructions:

    Source Code:
    * https://github.com/zachjs/sv2v

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'<step>','<index>')
    return chip


################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    chip.logger.debug("Setting up sv2v")


    tool = 'sv2v'
    chip.set('eda', tool, step, index, 'threads', 4)
    chip.set('eda', tool, step, index, 'exe', 'sv2v')
    chip.set('eda', tool, step, index, 'vendor', 'sv2v')
    chip.set('eda', tool, step, index, 'version', '0.0')

    # Since we run sv2v after the import/preprocess step, there should be no
    # need for specifying include dirs/defines. However we don't want to pass
    # --skip-preprocessor because the morty there may still be unused
    # preprocessor directives not removed by morty/the importer and passing the
    # --skip-preprocessor flag would cause sv2v to error.

    # since this step should run after import, the top design module should be
    # set and we can read the pickled Verilog without accessing the original
    # sources
    topmodule = chip.get('design')
    chip.add('eda', tool, step, index, 'option', 'cmdline', "inputs/" + topmodule + ".v")
    chip.add('eda', tool, step, index, 'option', 'cmdline', "--write=outputs/" + topmodule + ".v")

################################
# Post_process (post executable)
################################

def post_process(chip, step, index):
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
    setup_tool(chip, step='transalate', index='0')
    # write out results
    chip.writecfg(output)
