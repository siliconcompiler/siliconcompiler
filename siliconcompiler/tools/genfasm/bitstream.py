import os
import shutil
from siliconcompiler.tools.vpr import vpr


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

    chip.set('tool', tool, 'task', task, 'regex', 'warnings', "^Warning",
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', "^Error",
             step=step, index=index, clobber=False)


def runtime_options(chip):
    options = vpr.runtime_options(chip)

    design = chip.top()

    blif = f"inputs/{design}.blif"
    options.append(blif)

    options.append(f'--net_file inputs/{design}.net')
    options.append(f'--place_file inputs/{design}.place')
    options.append(f'--route_file inputs/{design}.route')

    return options

################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    vpr.vpr_post_process(chip)

    design = chip.top()
    shutil.move(f'{design}.fasm', 'outputs')
