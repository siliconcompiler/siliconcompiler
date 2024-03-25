def setup(chip):
    tool = 'run'

    chip.set('tool', tool, 'exe', 'sh')


def parse_version(stdout):
    '''
    Version check based on stdout
    Depends on tool reported string
    '''
    return '0'
