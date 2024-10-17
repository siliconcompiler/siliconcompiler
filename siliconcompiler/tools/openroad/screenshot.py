from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools.openroad import make_docs as or_make_docs
from siliconcompiler.tools.openroad import show
from siliconcompiler.tools.openroad._apr import set_reports


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    or_make_docs(chip)
    chip.set('tool', 'openroad', 'task', 'screenshot', 'var', 'show_filepath', '<path>')


def setup(chip):
    '''
    Generate a PNG file from a layout file
    '''
    show.generic_show_setup(chip, True)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.add('tool', tool, 'task', task, 'output', f'{chip.top()}.png', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'show_vertical_resolution', '1024',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'include_report_images', 'false',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'include_report_images',
             'true/false, include the images in reports/',
             field='help')

    set_reports(chip, [
        # Images
        'placement_density',
        'routing_congestion',
        'power_density',
        'ir_drop',
        'clock_placement',
        'clock_trees',
        'optimization_placement'
    ])


def pre_process(chip):
    show.pre_process(chip)
