from siliconcompiler.tools.klayout import klayout
from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.show import general_gui_setup
from siliconcompiler.tools.klayout.show import pre_process as show_pre_process
from siliconcompiler.tools._common import get_tool_task


def make_docs(chip):
    klayout.make_docs(chip)
    chip.set('tool', 'klayout', 'task', 'screenshot', 'var', 'show_filepath', '<path>')


def setup(chip):
    '''
    Generate a PNG file from a layout file
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'klayout'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    clobber = False

    setup_gui_screenshot(chip)

    option = ['-nc', '-z', '-rm']
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)


def pre_process(chip):
    show_pre_process(chip)


def setup_gui_screenshot(chip, require_input=True):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    design = chip.top()

    general_gui_setup(chip, task, True, require_input=require_input)

    chip.set('tool', tool, 'task', task, 'var', 'show_horizontal_resolution', '4096',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution', '4096',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'xbins', '1',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'ybins', '1',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'margin', '10',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'linewidth', '0',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'oversampling', '2',
             step=step, index=index, clobber=False)

    # Help
    chip.set('tool', tool, 'task', task, 'var', 'show_horizontal_resolution',
             'Horizontal resolution in pixels',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution',
             'Vertical resolution in pixels',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'xbins',
             'If greater than 1, splits the image into multiple segments along x-axis',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'ybins',
             'If greater than 1, splits the image into multiple segments along y-axis',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'margin',
             'Margin around design in microns',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'linewidth',
             'Width of lines in detailed screenshots',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'oversampling',
             'Image oversampling used in detailed screenshots',
             field='help')

    xbins = int(chip.get('tool', tool, 'task', task, 'var', 'xbins',
                         step=step, index=index)[0])
    ybins = int(chip.get('tool', tool, 'task', task, 'var', 'ybins',
                         step=step, index=index)[0])

    if xbins == 1 and ybins == 1:
        chip.add('tool', tool, 'task', task, 'output', design + '.png',
                 step=step, index=index)
    else:
        for x in range(xbins):
            for y in range(ybins):
                chip.add('tool', tool, 'task', task, 'output', f'{design}_X{x}_Y{y}.png',
                         step=step, index=index)
