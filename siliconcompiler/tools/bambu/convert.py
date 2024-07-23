import os
import shutil
from siliconcompiler.tools._common import \
    add_frontend_requires, add_require_input, get_frontend_options, get_input_files, \
    get_tool_task, has_input_files


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    if not has_input_files(chip, 'input', 'hll', 'c'):
        return "no files in [input,hll,c]"

    tool = 'bambu'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'bambu')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=2024.03', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    add_require_input(chip, 'input', 'hll', 'c')
    add_frontend_requires(chip, ['idir', 'define'])


################################
#  Custom runtime options
################################
def runtime_options(chip):
    cmdlist = []

    cmdlist.append('--memory-allocation-policy=NO_BRAM')

    opts = get_frontend_options(chip, ['idir', 'define'])

    for value in opts['idir']:
        cmdlist.append('-I' + value)
    for value in opts['define']:
        cmdlist.append('-D' + value)
    for value in get_input_files(chip, 'input', 'hll', 'c'):
        cmdlist.append(value)

    cmdlist.append('--memory-allocation-policy=NO_BRAM')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    cmdlist.append(f'--top-fname={chip.top(step, index)}')

    return cmdlist


################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    shutil.copy2(f'{chip.top(step, index)}.v', os.path.join('outputs', f'{chip.top()}.v'))
