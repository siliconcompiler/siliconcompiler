import os

from siliconcompiler.tools.gtkwave import setup as tool_setup
from siliconcompiler.tools._common import \
    add_require_input, get_tool_task, input_provides


def setup(chip):
    '''
    Show a VCD file.
    '''

    tool_setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index)

    chip.set('tool', tool, 'task', task, 'refdir',
             'tools/gtkwave/scripts',
             step=step, index=index, package='siliconcompiler')

    chip.set('tool', tool, 'task', task, 'refdir',
             'tools/gtkwave/scripts',
             step=step, index=index, package='siliconcompiler')
    chip.set('tool', tool, 'task', task, 'script', 'sc_show.tcl',
             step=step, index=index)

    if f'{chip.top()}.vcd' in input_provides:
        chip.set('tool', tool, 'task', task, 'input', f'{chip.top()}.vcd', step=step, index=index)
    else:
        add_require_input(chip, 'input', 'waveform', 'vcd')


def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options = []

    threads = chip.get('tool', tool, 'task', task, 'threads', step=step, index=index)
    if threads:
        options.append(f'--cpu={threads}')

    script = chip.find_files('tool', tool, 'task', task, 'script', step=step, index=index)[0]
    options.append(f'--script={script}')

    if os.path.exists(f'inputs/{chip.top()}.vcd'):
        dump = f'inputs/{chip.top()}.vcd'
    else:
        dump = chip.find_files('input', 'waveform', 'vcd', step=step, index=index)[0]
    options.append(f'--dump={dump}')

    return options
