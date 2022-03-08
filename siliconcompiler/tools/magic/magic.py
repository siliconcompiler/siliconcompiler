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
    chip.load_pdk('skywater130')
    chip.set('arg','index','<index>')

    # check drc
    chip.set('arg','step','drc')
    setup(chip)

    # check lvs
    chip.set('arg','step', 'extspice')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
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

    chip.set('eda', tool, 'exe', tool)
    chip.set('eda', tool, 'vswitch', '--version')
    chip.set('eda', tool, 'version', '8.3.274')
    chip.set('eda', tool, 'format', 'tcl')
    chip.set('eda', tool, 'copy', 'true') # copy in .magicrc file
    chip.set('eda', tool, 'threads', step, index,  4)
    chip.set('eda', tool, 'refdir', step, index,  refdir)
    chip.set('eda', tool, 'script', step, index,  refdir + '/' + script)

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    options.append('-rcfile')
    options.append('sc.magicrc')
    chip.set('eda', tool, 'option', step, index,  options, clobber=False)

    design = chip.get('design')
    chip.add('eda', tool, 'input', step, index, f'{design}.gds')
    if step == 'extspice':
        chip.add('eda', tool, 'output', step, index, f'{design}.spice')
    elif step == 'drc':
        chip.add('eda', tool, 'output', step, index, f'{design}.drc')

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

    chip = make_docs()
    chip.write_manifest("magic.json")
