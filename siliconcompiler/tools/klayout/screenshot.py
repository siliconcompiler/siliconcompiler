from siliconcompiler.tools.klayout import klayout
from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.show import general_gui_setup


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
    task = chip._get_task(step, index)
    design = chip.top()
    clobber = False

    general_gui_setup(chip, task, True)

    option = ['-nc', '-z', '-rm']
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)

    chip.add('tool', tool, 'task', task, 'output', design + '.png', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'show_horizontal_resolution', '4096', step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution', '4096', step=step, index=index, clobber=False)

    # Help
    chip.set('tool', tool, 'task', task, 'var', 'show_horizontal_resolution', 'Horizontal resolution in pixels', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution', 'Vertical resolution in pixels', field='help')
