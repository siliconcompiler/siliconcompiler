from siliconcompiler.tools.magic.magic import setup as setup_tool
from siliconcompiler.tools.magic.magic import process_file
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools._common.asic import get_mainlib, get_libraries


def setup(chip):
    '''
    Extract spice netlists from a GDS file for simulation use
    '''

    # Generic tool setup
    setup_tool(chip)

    tool = 'magic'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'output', f'{design}.spice', step=step, index=index)


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
