import os
from siliconcompiler.tools._common import add_require_input, get_tool_task, input_provides


def setup(chip):
    '''
    Show a VCD file.
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # Standard setup
    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.3.0', clobber=False)

    # Require VCD file
    if f'{chip.top()}.vcd' in input_provides(chip, step, index):
        chip.set('tool', tool, 'task', task, 'input', f'{chip.top()}.vcd',
                 step=step, index=index)
    elif chip.valid('tool', tool, 'task', task, 'var', 'show_filepath') and \
            chip.get('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['tool', tool, 'task', task, 'var', 'show_filepath']),
                 step=step, index=index)
    else:
        add_require_input(chip, 'input', 'waveform', 'vcd')

    # Don't exit on show
    chip.set('tool', tool, 'task', task, 'var', 'show_exit', False,
             step=step, index=index, clobber=False)


def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options = []

    # Get VCD file
    if os.path.exists(f'inputs/{chip.top()}.vcd'):
        dump = f'inputs/{chip.top()}.vcd'
    elif chip.valid('tool', tool, 'task', task, 'var', 'show_filepath') and \
            chip.get('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index):
        dump = chip.get('tool', tool, 'task', task, 'var', 'show_filepath',
                        step=step, index=index)[0]
    else:
        dump = chip.find_files('input', 'waveform', 'vcd', step=step, index=index)[0]
    options.append(dump)

    return options
