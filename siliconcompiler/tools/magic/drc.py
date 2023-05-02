import re

from siliconcompiler.tools.magic.magic import setup as setup_tool


def setup(chip):
    '''
    Perform DRC checks
    '''

    # Generic tool setup
    setup_tool(chip)


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
    with open(report_path, 'r') as f:
        for line in f:
            errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

            if errors:
                drvs = errors.group(1)
    chip._record_metric(step, index, 'drvs', drvs, report_path)

    # TODO: return error code
    return 0
