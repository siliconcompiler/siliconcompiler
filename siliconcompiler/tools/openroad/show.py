
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import copy_show_files, build_pex_corners

def setup(chip):
    ''' Helper method for configs specific to show tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'show'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    mode = 'show'
    clobber = True
    option = "-no_init -gui"

    chip.set('tool', tool, 'task', task, 'var', 'show_exit', "false", clobber=False, step=step, index=index)
    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', 'show_filepath']), step=step, index=index)
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.set('tool', tool, 'task', task, 'var', 'show_filetype', incoming_ext, step=step, index=index)
        chip.add('tool', tool, 'task', task, 'input', f'{design}.{incoming_ext}', step=step, index=index)

    # Add to option string.
    cur_options = ' '.join(chip.get('tool', tool, 'task', task, 'option',  step, index))
    new_options = f'{cur_options} {option}'
    chip.set('tool', tool, 'task', task, 'option',  step, index, new_options, clobber=True)

def pre_process(chip):
    copy_show_files(chip)
    build_pex_corners(chip)
