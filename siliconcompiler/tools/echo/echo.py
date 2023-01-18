def setup(chip):
    tool = 'echo'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = step

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'task', task, 'option',  step, index, step + index, clobber=False)

def parse_version(stdout):
    '''
    Version check based on stdout
    Depends on tool reported string
    '''
    return '0'
