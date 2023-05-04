import os
import shutil


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    tool = 'bambu'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'bambu')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.9.6', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', 'input,hll,c')


################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    design = chip.top()
    shutil.copy(f'{design}.v', os.path.join('outputs', f'{design}.v'))
