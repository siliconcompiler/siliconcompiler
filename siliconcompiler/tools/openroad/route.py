
def setup(chip):
    ''' Helper method for configs specific to route tasks.
    '''

    tool = 'openroad'
    task = 'route'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if (not chip.valid('input', 'layout', 'def') or
        not chip.get('input', 'layout', 'def')):
        chip.add('tool', tool, 'task', task, 'input', step, index, design +'.def')
