import re

from siliconcompiler.tools.magic.magic import setup as setup_tool
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric


def setup(chip):
    '''
    Perform DRC checks
    '''

    # Generic tool setup
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

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
    drcs = 0
    with sc_open(report_path) as f:
        for line in f:
            errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

            if errors:
                drcs = errors.group(1)
    record_metric(chip, step, index, 'drcs', drcs, report_path)

    # TODO: return error code
    return 0
