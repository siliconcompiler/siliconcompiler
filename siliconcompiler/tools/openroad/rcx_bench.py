from siliconcompiler.tools import openroad
from siliconcompiler.tools._common import get_tool_task


def setup_tool(chip):
    ''' Helper method for configs specific to extraction tasks.
    '''

    openroad.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'script', 'sc_rcx.tcl',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'threads', 1,
             step=step, index=index)


def setup_task(chip):
    # Generic tool setup.
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    chip.set('tool', tool, 'task', task, 'var', 'libtype',
             list(chip.getkeys('pdk', pdk, 'aprtech', tool, stackup))[0],
             clobber=False, step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'libtype',
             'Library type used to select the lef file',
             field='help')
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['tool', tool, 'task', task, 'var', 'libtype']),
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['pdk',
                       pdk,
                       'aprtech',
                       tool,
                       stackup,
                       chip.get('tool', tool, 'task', task, 'var', 'libtype',
                                step=step, index=index)[0],
                       'lef']),
             step=step, index=index)


def setup(chip):
    '''
    Builds the RCX extraction bench
    '''

    # Generic tool setup.
    setup_task(chip)

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.add('tool', tool, 'task', task, 'output', f'{design}.def', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.vg', step=step, index=index)

    pdk = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    if chip.valid('pdk', pdk, 'var', 'openroad', 'rcx_bench_max_layer', stackup):
        chip.set('tool', tool, 'task', task, 'var', 'max_layer',
                 chip.get('pdk', pdk, 'var', 'openroad', 'rcx_bench_max_layer', stackup)[0],
                 clobber=False, step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['pdk', pdk, 'var', 'openroad', 'rcx_bench_max_layer', stackup]),
                 step=step, index=index)
    else:
        chip.set('tool', tool, 'task', task, 'var', 'max_layer',
                 chip.get('pdk', pdk, 'maxlayer', stackup),
                 clobber=False, step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'max_layer',
             'Maximum layer to generate extraction bench for',
             field='help')
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['tool', tool, 'task', task, 'var', 'max_layer']),
             step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'bench_length', '100',
             clobber=False, step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'bench_length',
             'Length of bench wires',
             field='help')
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['tool', tool, 'task', task, 'var', 'bench_length']),
             step=step, index=index)
