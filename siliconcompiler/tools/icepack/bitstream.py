
def setup(chip):
    ''' Sets up default settings on a per step basis
    '''
    tool = 'icepack'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'bitstream'

    clobber = False
    design = chip.top()

    chip.set('tool', tool, 'exe', tool)

    chip.set('tool', tool, 'task', task, 'option', step, index, "", clobber=clobber)
    chip.set('tool', tool, 'task', task, 'input', step, index, f'{design}.asc')
    chip.set('tool', tool, 'task', task, 'output', step, index, f'{design}.bit')
