import os
from siliconcompiler.tools._common import add_require_if_set


def setup(chip):
    '''
    Imports VHDL and converts it to verilog
    '''

    # Standard Setup
    tool = 'ghdl'
    clobber = False

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', tool, 'exe', 'ghdl')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=4.0.0-dev', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', '',
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'stdout', 'destination', 'output',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'stdout', 'suffix', 'v',
             step=step, index=index)

    # Schema requirements
    add_require_if_set(chip, 'input', 'rtl', 'vhdl')

    design = chip.top()

    chip.set('tool', tool, 'task', task, 'output', f'{design}.v', step=step, index=index)
