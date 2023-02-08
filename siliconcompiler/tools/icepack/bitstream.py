
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

    chip.set('tool', tool, 'task', task, 'option', "", clobber=clobber, step=step, index=index)
    chip.set('tool', tool, 'task', task, 'input', f'{design}.asc', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{design}.bit', step=step, index=index)
