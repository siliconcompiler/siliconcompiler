import os
import re
import shutil
import siliconcompiler

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
    chip.set('arg','step', 'extspice')
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
        script = 'sc_drc.tcl'
    elif step == 'extspice':
        script = 'sc_extspice.tcl'
    else:
        raise ValueError(f"Magic tool doesn't support step {step}.")

    chip.set('eda', tool, step, index, 'exe', tool)
    chip.set('eda', tool, step, index, 'vswitch', '--version')
    chip.set('eda', tool, step, index, 'version', '8.3.196')
    chip.set('eda', tool, step, index, 'threads', 4)
    chip.set('eda', tool, step, index, 'refdir', refdir)
    chip.set('eda', tool, step, index, 'script', refdir + '/' + script)

    # copy in .magicrc file
    chip.set('eda', tool, step, index, 'copy', 'true')

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    options.append('-rcfile')
    options.append('sc.magicrc')
    chip.set('eda', tool, step, index, 'option', options, clobber=False)

################################
# Version Check
################################

def parse_version(stdout):
    return stdout.strip('\n')

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution

    Reads error count from output and fills in appropriate entry in metrics
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.get('design')

    if step == 'drc':
        with open(f'outputs/{design}.drc', 'r') as f:
            for line in f:
                errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

                if errors:
                    chip.set('metric', step, index, 'errors', 'real', errors.group(1))

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
    chip.target('asicflow_skywater130')
    chip.set('arg','index','0')
    chip.set('arg','step','drc')
    setup_tool(chip)
    # write out results
    chip.writecfg(output)
