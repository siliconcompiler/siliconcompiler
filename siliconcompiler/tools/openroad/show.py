
def setup(chip):
    ''' Helper method for configs specific to show tasks.
    '''

    tool = 'openroad'
    task = 'show'
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    mode = 'show'
    clobber = True
    option = "-no_init -gui"

    chip.set('tool', tool, 'task', task, 'var', step, index, 'show_exit', "false", clobber=False)
    if chip.valid('tool', tool, 'task', task, 'var', step, index, 'show_filepath'):
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', step, index, 'show_filepath']))
    else:
        incoming_ext = find_incoming_ext(chip)
        chip.set('tool', tool, 'task', task, 'var', step, index, 'show_filetype', incoming_ext)
        chip.add('tool', tool, 'task', task, 'input', step, index, f'{design}.{incoming_ext}')
