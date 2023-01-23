
from .magic import setup as setup_tool

def setup(chip):
    ''' Helper method to setup DRC-specific configs.
    '''

    # Generic tool setup
    setup_tool(chip)

    tool = 'magic'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'drc'
    design = chip.top()

    report_path = f'reports/{design}.drc'
    chip.set('tool', tool, 'task', task, 'report', step, index, 'drvs', report_path)
