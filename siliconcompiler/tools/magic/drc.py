import re

from siliconcompiler.tools.magic.magic import setup as setup_tool

def setup(chip):
    '''
    Perform DRC checks
    '''

    # Generic tool setup
    setup_tool(chip)

    tool = 'magic'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'drc'
    design = chip.top()

    report_path = f'reports/{design}.drc'
    chip.set('tool', tool, 'task', task, 'report', 'drvs', report_path, step=step, index=index)

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution

    Reads error count from output and fills in appropriate entry in metrics
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.top()

    report_path = f'reports/{design}.drc'
    with open(report_path, 'r') as f:
        for line in f:
            errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

            if errors:
                chip.set('metric', 'drvs', errors.group(1), step=step, index=index)

    #TODO: return error code
    return 0
