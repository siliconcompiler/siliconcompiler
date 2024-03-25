def setup(chip):
    tool = 'run'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', tool, 'exe', 'sh')


def parse_version(stdout):
    '''
    Version check based on stdout
    Depends on tool reported string
    '''
    return '0'
