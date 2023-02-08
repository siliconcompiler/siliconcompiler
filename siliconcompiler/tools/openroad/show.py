
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

    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_exit', "false", clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', step, index, 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', step, index, 'show_filepath']))
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.set('tool', tool, 'task', task, 'var', step, index, 'show_filetype', incoming_ext)
        chip.add('tool', tool, 'task', task, 'input', step, index, f'{design}.{incoming_ext}')

    # Add to option string.
    cur_options = ' '.join(chip.get('tool', tool, 'task', task, 'option',  step, index))
    new_options = f'{cur_options} {option}'
    chip.set('tool', tool, 'task', task, 'option',  step, index, new_options, clobber=True)

def pre_process(chip):
    copy_show_files(chip)
    build_pex_corners(chip)
