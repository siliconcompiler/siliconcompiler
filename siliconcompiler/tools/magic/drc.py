import re

from siliconcompiler.tools.magic.magic import setup as setup_tool
from siliconcompiler.tools.magic.magic import process_file
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric
from siliconcompiler.tools._common.asic import get_mainlib, get_libraries


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


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    mainlib = get_mainlib(chip)
    libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)
    process_file('lef', chip, 'pdk', pdk, 'aprtech', 'magic', stackup, libtype, 'lef')

    for lib in get_libraries(chip, 'logic'):
        process_file('lef', chip, 'library', lib, 'output', stackup, 'lef')

    for lib in get_libraries(chip, 'macro'):
        if lib in chip.get('tool', tool, 'task', task, 'var', 'exclude', step=step, index=index):
            process_file('lef', chip, 'library', lib, 'output', stackup, 'lef')


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
