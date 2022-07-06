import re

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

    chip = siliconcompiler.Chip('<design>')
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
    #if step not in ('drc', 'extspice'):
    #    raise ValueError(f"Magic tool doesn't support step {step}.")
    script = 'sc_magic.tcl'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=8.3.196', clobber=False)
    chip.set('tool', tool, 'format', 'tcl')
    chip.set('tool', tool, 'threads', step, index,  4, clobber=False)
    chip.set('tool', tool, 'refdir', step, index,  refdir, clobber=False)
    chip.set('tool', tool, 'script', step, index,  script, clobber=False)

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    chip.set('tool', tool, 'option', step, index,  options, clobber=False)

    design = chip.get_entrypoint()
    if chip.valid('input', 'gds'):
        chip.add('tool', tool, 'require', step, index, ','.join(['input', 'gds']))
    else:
        chip.add('tool', tool, 'input', step, index, f'{design}.gds')
    if step == 'extspice':
        chip.add('tool', tool, 'output', step, index, f'{design}.spice')

    chip.set('tool', tool, 'regex', step, index, 'errors', r'^Error', clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'warnings', r'warning', clobber=False)

    if step == 'drc':
        report_path = f'reports/{design}.drc'
        chip.set('tool', tool, 'report', step, index, 'drvs', report_path)

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
    design = chip.get_entrypoint()

    if step == 'drc':
        report_path = f'reports/{design}.drc'
        with open(report_path, 'r') as f:
            for line in f:
                errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

                if errors:
                    chip.set('metric', step, index, 'drvs', errors.group(1))

    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("magic.json")
