import os
import shutil
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_frontend_options, get_input_files, \
    get_tool_task, has_input_files
from siliconcompiler import sc_open

# Directory inside step/index dir to store bsc intermediate results.
VLOG_DIR = 'verilog'


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    if not has_input_files(chip, 'input', 'hll', 'bsv'):
        return "no files in [input,hll,bsv]"

    tool = 'bluespec'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'bsc')
    # This is technically the 'verbose' flag, but used alone it happens to give
    # us the version and exit cleanly, so we'll use it here.
    chip.set('tool', tool, 'vswitch', '-v')
    chip.set('tool', tool, 'version', '>=2021.07', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    add_require_input(chip, 'input', 'hll', 'bsv')
    add_frontend_requires(chip, ['idir', 'ydir', 'define'])


################################
# Pre-process
################################
def pre_process(chip):
    # bsc requires its output directory exists before being called.
    if os.path.isdir(VLOG_DIR):
        shutil.rmtree(VLOG_DIR)
    os.makedirs(VLOG_DIR)


################################
#  Custom runtime options
################################
def runtime_options(chip):
    cmdlist = []

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    opts = get_frontend_options(chip, ['idir', 'ydir', 'define'])

    cmdlist.append('-verilog')
    cmdlist.append(f'-vdir {VLOG_DIR}')
    cmdlist.append('-u')

    cmdlist.append(f'-g {chip.top(step, index)}')

    bsc_path = ':'.join(opts['ydir'] + ['%/Libraries'])
    cmdlist.append('-p ' + bsc_path)

    for value in opts['idir']:
        cmdlist.append('-I ' + value)
    for value in opts['define']:
        cmdlist.append('-D ' + value)

    sources = get_input_files(chip, 'input', 'hll', 'bsv', add_library_files=False)
    if len(sources) != 1:
        raise ValueError('Bluespec frontend only supports one source file!')
    cmdlist.extend(sources)

    return cmdlist


################################
# Post-process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # bsc outputs each compiled module to its own Verilog file, so we
    # concatenate them all to create a pickled output we can pass along.
    design = chip.top()
    with open(os.path.join('outputs', f'{design}.v'), 'w') as pickled_vlog:
        for src in os.listdir(VLOG_DIR):
            with sc_open(os.path.join(VLOG_DIR, src)) as vlog_mod:
                pickled_vlog.write(vlog_mod.read())
