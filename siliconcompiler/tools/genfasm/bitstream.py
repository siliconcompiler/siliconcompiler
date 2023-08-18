import os
import shutil


def setup(chip):
    '''
    Generates a bitstream
    '''
    tool = 'genfasm'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)


################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    design = chip.top()
    shutil.move(f'{design}.fasm', 'outputs')
    # TODO: return error code
    return 0
