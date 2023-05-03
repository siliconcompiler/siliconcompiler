import os
import shutil

# Directory inside step/index dir to store bsc intermediate results.
VLOG_DIR = 'verilog'


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    tool = 'bluespec'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'bsc')
    # This is technically the 'verbose' flag, but used alone it happens to give
    # us the version and exit cleanly, so we'll use it here.
    chip.set('tool', tool, 'vswitch', '-v')
    chip.set('tool', tool, 'version', '>=2021.07', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', 'input,hll,bsv')


################################
# Pre-process
################################
def pre_process(chip):
    # bsc requires its output directory exists before being called.
    if os.path.isdir(VLOG_DIR):
        shutil.rmtree(VLOG_DIR)
    os.makedirs(VLOG_DIR)


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
            with open(os.path.join(VLOG_DIR, src), 'r') as vlog_mod:
                pickled_vlog.write(vlog_mod.read())
