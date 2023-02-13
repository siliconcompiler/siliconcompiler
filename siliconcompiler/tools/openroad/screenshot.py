import siliconcompiler
from siliconcompiler.tools.openroad.openroad import setup as setup_tool
from siliconcompiler.tools.openroad.openroad import build_pex_corners
from siliconcompiler.tools.openroad.show import copy_show_files, find_incoming_ext

def make_docs():
    chip = siliconcompiler.Chip('<design>')
    chip.load_target('freepdk45_demo')
    step = 'screenshot'
    index = '<index>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('flowgraph', chip.get('option', 'flow'), step, index, 'task', 'screenshot')
    chip.set('tool', 'openroad', 'task', 'screenshot', 'var', 'show_filepath', '<path>')
    setup(chip)

    return chip

def setup(chip):
    ''' Helper method for configs specific to screenshot tasks.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'openroad'
    task = 'screenshot'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    mode = 'show'
    clobber = True
    option = "-no_init -gui"

    chip.add('tool', tool, 'task', task, 'output', design + '.png', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution', '1024', step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'show_exit', "true", step=step, index=index, clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require', ",".join(['tool', tool, 'task', task, 'var', 'show_filepath']), step=step, index=index)
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.set('tool', tool, 'task', task, 'var', 'show_filetype', incoming_ext, step=step, index=index)
        chip.add('tool', tool, 'task', task, 'input', f'{design}.{incoming_ext}', step=step, index=index)

    # Add to option string.
    cur_options = ' '.join(chip.get('tool', tool, 'task', task, 'option', step=step, index=index))
    new_options = f'{cur_options} {option}'
    chip.set('tool', tool, 'task', task, 'option', new_options, step=step, index=index, clobber=True)

def pre_process(chip):
    copy_show_files(chip)
    build_pex_corners(chip)
