'''
Magic is a chip layout viewer, editor, and circuit verifier with
built in DRC and LVS engines.

Documentation: http://opencircuitdesign.com/magic/userguide.html

Installation: https://github.com/RTimothyEdwards/magic

Sources: https://github.com/RTimothyEdwards/magic
'''

import os
from siliconcompiler.tools._common import input_provides, get_tool_task
from siliconcompiler.targets import freepdk45_demo


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    chip.use(freepdk45_demo)


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    ''' Setup function for 'magic' tool
    '''

    tool = 'magic'
    refdir = 'tools/' + tool
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # magic used for drc and lvs
    # if step not in ('drc', 'extspice'):
    #    raise ValueError(f"Magic tool doesn't support step {step}.")
    script = 'sc_magic.tcl'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=8.3.196', clobber=False)
    chip.set('tool', tool, 'format', 'tcl')

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'script', script,
             step=step, index=index, clobber=False)

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    chip.set('tool', tool, 'task', task, 'option', options, step=step, index=index, clobber=False)

    design = chip.top()
    if f'{design}.gds' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.gds', step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['input', 'layout', 'gds']),
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^Error',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'warning',
             step=step, index=index, clobber=False)


################################
# Version Check
################################
def parse_version(stdout):
    return stdout.strip('\n')


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("magic.json")
