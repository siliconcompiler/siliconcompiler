import os
import re
import shutil
import siliconcompiler
from siliconcompiler.tools.magic import count_lvs

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Magic is a chip layout viewer, editor, and circuit verifier with
    built in DRC and LVS engines.

    Documentation: http://opencircuitdesign.com/magic/userguide.html

    Installation: https://github.com/RTimothyEdwards/magic

    Sources: https://github.com/RTimothyEdwards/magic

    '''

    chip = siliconcompiler.Chip()
    chip.target('skywater130')
    chip.set('arg','index','<index>')

    # check drc
    chip.set('arg','step','drc')
    setup_tool(chip)

    # check lvs
    chip.set('arg','lvs')
    setup_tool(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Setup function for 'magic' tool
    '''

    tool = 'magic'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # magic used for drc and lvs
    if step == 'drc':
        script = 'gds_drc.tcl'
    elif step == 'lvs':
        script = 'lvs.tcl'

    chip.set('eda', tool, step, index, 'exe', tool)
    chip.set('eda', tool, step, index, 'version', '0.0')
    chip.set('eda', tool, step, index, 'threads', 4)
    chip.set('eda', tool, step, index, 'refdir', refdir)
    chip.set('eda', tool, step, index, 'script', refdir + '/' + script)

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    stackup = chip.get('pdk','stackup')[0]

    magicfile = chip.find(chip.get('pdk','drc','magic', stackup, 'runset')[0])

    pdk_path = os.path.dirname(magicfile)

    with open('pdkpath.tcl', 'w') as f:
        f.write(f'set PDKPATH {pdk_path}')

    options = []
    options.append('-rcfile ' + magicfile)

    return options

################################
# Version Check
################################

def check_version(chip, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'magic', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0

################################
# Post_process (post executable)
################################

def post_process(chip, step, index):
    ''' Tool specific function to run after step execution

    Reads error count from output and fills in appropriate entry in metrics
    '''
    design = chip.get('design')

    if step == 'drc':
        with open(f'outputs/{design}.drc', 'r') as f:
            for line in f:
                errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

                if errors:
                    chip.set('metric', step, index, 'errors', 'real', errors.group(1))
    elif step == 'lvs':
        # Export metrics
        lvs_failures = count_lvs.count_LVS_failures(f'outputs/{design}.lvs.json')
        chip.set('metric', step, index, 'errors', 'real', lvs_failures[0])

    # Need to pass along DEF and GDS to future verification stages
    shutil.copy(f'inputs/{design}.def', f'outputs/{design}.def')
    shutil.copy(f'inputs/{design}.gds', f'outputs/{design}.gds')

    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(loglevel="INFO")
    # load configuration
    chip.target('skywater130_asicflow')
    chip.set('arg','index','0')
    chip.set('arg','step','drc')
    setup_tool(chip)
    # write out results
    chip.writecfg(output)
