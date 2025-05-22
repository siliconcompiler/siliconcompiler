import os
import shlex

from siliconcompiler.tools._common import input_provides, has_input_files, \
    get_input_files, get_tool_task, record_metric
from siliconcompiler.tools._common.asic import set_tool_task_var, get_tool_task_var

from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from xml.etree import ElementTree
from siliconcompiler import utils


def make_docs(chip):
    from siliconcompiler.tools.klayout import klayout
    klayout.make_docs(chip)
    chip.set('tool', 'klayout', 'task', 'drc', 'var', 'drc_name', '<drc_name>',
             step='<step>', index='<index>')


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

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=clobber)

    chip.add('tool', tool, 'task', task, 'require', 'option,pdk')
    chip.add('tool', tool, 'task', task, 'require', 'option,stackup')

    chip.set('tool', tool, 'task', task, 'var', 'drc_name', 'drc',
             step=step, index=index, clobber=False)
    chip.add('tool', tool, 'task', task, 'require', f'tool,{tool},task,{task},var,drc_name',
             step=step, index=index)

    drc_name = chip.get('tool', tool, 'task', task, 'var', 'drc_name', step=step, index=index)
    if not drc_name:
        raise ValueError('drc_name is required')
    drc_name = drc_name[0]

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    chip.add('tool', tool, 'task', task, 'require',
             f'pdk,{pdk},drc,runset,klayout,{stackup},{drc_name}')

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

    chip.add('tool', tool, 'task', task, 'output', design + '.lyrdb',
             step=step, index=index)

    set_tool_task_var(
        chip,
        f'drc_params:{drc_name}',
        schelp="Input parameter to DRC script, in the form of key=value, if the value "
               "is <topcell>, <input>, <report>, <threads> these will be automatically "
               "determined.",
        skip='lib')


def runtime_options(chip):
    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    layout = None
    for file in [f'inputs/{design}.gds', f'inputs/{design}.oas']:
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

    drc_name = chip.get('tool', tool, 'task', task, 'var', 'drc_name',
                        step=step, index=index)[0]
    report = os.path.abspath(f"outputs/{chip.top()}.lyrdb")

    runset = chip.find_files('pdk', pdk, 'drc', 'runset', 'klayout', stackup, drc_name)[0]

    params_lookup = {
        "<topcell>": chip.top(),
        "<report>": shlex.quote(report),
        "<threads>": threads,
        "<input>": shlex.quote(layout)
    }

    args = [
        '-r', shlex.quote(runset)
    ]

    for param in get_tool_task_var(chip, f'drc_params:{drc_name}', skip='lib'):
        for lookup, value in params_lookup.items():
            param = param.replace(lookup, str(value))
        args.extend(
            ['-rd', param]
        )
    return args


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    drc_db = f"outputs/{chip.top()}.lyrdb"

    drc_report = None
    if os.path.isfile(drc_db):
        with open(drc_db, "r") as f:
            drc_report = ElementTree.fromstring(f.read())
    if drc_report is None:
        drc_db = []

    violation_count = 0
    if drc_report:
        violations = drc_report.find('items')
        if violations:
            violation_count = len(violations.findall('item'))

    record_metric(chip, step, index, 'drcs', violation_count, drc_db)
