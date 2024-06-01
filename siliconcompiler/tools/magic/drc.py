import re

from siliconcompiler.tools.magic.magic import setup as setup_tool
from siliconcompiler import sc_open


def setup(chip):
    '''
    Perform DRC checks
    '''

    # Generic tool setup
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    design = chip.top()

    chip.set('tool', tool, 'task', task, 'output', f'{design}.drc.mag', step=step, index=index)


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
    drvs = 0
    with sc_open(report_path) as f:
        for line in f:
            errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

            if errors:
                drvs = errors.group(1)
    chip._record_metric(step, index, 'drvs', drvs, report_path)

    # TODO: return error code
    return 0
