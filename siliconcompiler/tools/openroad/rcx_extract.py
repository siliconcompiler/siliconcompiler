from siliconcompiler.tools.openroad.rcx_bench import setup_task
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    ''' Helper method for configs specific to extraction tasks.
    '''

    # Generic tool setup.
    setup_task(chip)

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'var', 'corner',
             'Parasitic corner to generate RCX file for',
             field='help')
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['tool', tool, 'task', task, 'var', 'corner']),
             step=step, index=index)

    if chip.valid('tool', tool, 'task', task, 'var', 'corner') and \
       chip.get('tool', tool, 'task', task, 'var', 'corner', step=step, index=index):
        corner = chip.get('tool', tool, 'task', task, 'var', 'corner', step=step, index=index)[0]
    else:
        # Placeholder since require will cause this to fail
        corner = 'corner'

    chip.add('tool', tool, 'task', task, 'input', f'{design}.def', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', f'{design}.{corner}.spef', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', f'{design}.{corner}.rcx', step=step, index=index)
