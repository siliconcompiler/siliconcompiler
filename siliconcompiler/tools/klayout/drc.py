import os
from siliconcompiler.tools._common import input_provides, has_input_files, \
    get_input_files, get_tool_task, record_metric

from siliconcompiler.tools.klayout import klayout
from siliconcompiler.tools.klayout.klayout import setup as setup_tool
import xml.etree.ElementTree as ET


def make_docs(chip):
    klayout.make_docs(chip)
    chip.set('tool', 'klayout', 'task', 'show', 'var', 'show_filepath', '<path>')


def setup(chip):
    '''
    Performs a design rule check on the provided layout
    '''

    # Generic tool setup.
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    design = chip.top()

    clobber = False

    option = ['-z', '-nc', '-rx']
    chip.set('tool', tool, 'task', task, 'option', option,
             step=step, index=index, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=clobber)

    chip.add('tool', tool, 'task', task, 'require', 'option,pdk')
    chip.add('tool', tool, 'task', task, 'require', 'option,stackup')

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    chip.add('tool', tool, 'task', task, 'require',
             f'pdk,{pdk},drc,runset,klayout,{stackup},drc')

    if f'{design}.gds' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.gds',
                 step=step, index=index)
    elif f'{design}.oas' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.oas',
                 step=step, index=index)
    elif has_input_files(chip, 'input', 'layout', 'oas', check_library_files=False):
        chip.add('tool', tool, 'task', task, 'require', 'input,layout,oas',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,layout,gds',
                 step=step, index=index)


def runtime_options(chip):
    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    layout = None
    for file in [f'input/{design}.gds', f'input/{design}.oas']:
        if os.path.isfile(file):
            layout = file
            break

    if not layout:
        for file in [
                get_input_files(chip, 'input', 'layout', 'oas', add_library_files=False),
                get_input_files(chip, 'input', 'layout', 'gds', add_library_files=False)]:
            if file:
                layout = file[0]

    threads = chip.get('tool', tool, 'task', task, 'threads', step=step, index=index)
    if not threads:
        threads = 1

    return [
        '-r', chip.find_files('pdk', pdk, 'drc', 'runset', 'klayout', stackup, 'drc')[0],
        '-rd', f'report={os.path.abspath(f"reports/{chip.top()}.lyrdb")}',
        '-rd', f'input={layout}',
        '-rd', f'topcell={chip.top()}',
        '-rd', f'threads={threads}'
    ]


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    drc_db = f"reports/{chip.top()}.lyrdb"

    drc_report = None
    if os.path.isfile(drc_db):
        with open(drc_db, "r") as f:
            drc_report = ET.fromstring(f.read())
    if drc_report is None:
        drc_db = []

    violation_count = 0
    if drc_report:
        violations = drc_report.find('items')
        if violations:
            violation_count = len(violations.findall('item'))

    record_metric(chip, step, index, 'drcs', violation_count, drc_db)
