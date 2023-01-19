
def setup(chip):
    ''' Helper method for configs specific to screenshot tasks.
    '''

    tool = 'openroad'
    task = 'screenshot'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    mode = 'show'
    clobber = True
    option = "-no_init -gui"

    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.png')
    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_vertical_resolution', '1024', clobber=False)

    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_exit', "true", clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', step, index, 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', step, index, 'show_filepath']))
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.set('tool', tool, 'task', task, 'var', step, index, 'show_filetype', incoming_ext)
        chip.add('tool', tool, 'task', task, 'input', step, index, f'{design}.{incoming_ext}')
