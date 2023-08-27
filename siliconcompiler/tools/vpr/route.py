import os
import shutil

from siliconcompiler.tools.vpr import vpr


def setup(chip, clobber=True):
    '''
    Perform automated place and route with VPR
    '''

    tool = 'vpr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    vpr.setup_tool(chip, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=clobber)

    # TO-DO: PRIOROTIZE the post-routing packing results?
    design = chip.top()
    chip.add('tool', tool, 'task', task, 'output', design + '.route', step=step, index=index)


################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    for file in chip.get('tool', 'vpr', 'task', task, 'output', step=step, index=index):
        shutil.copy(file, 'outputs')
    design = chip.top()
    # Forward all of the prior step inputs forward for bitstream generation
    shutil.copy(f'inputs/{design}.blif', 'outputs')
    shutil.copy(f'inputs/{design}.net', 'outputs')
    shutil.copy(f'inputs/{design}.place', 'outputs')
    # TODO: return error code
    return 0
