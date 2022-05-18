def setup(chip):
    tool = 'echo'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'option',  step, index, step + index, clobber=False)

def parse_version(stdout):
    '''
    Version check based on stdout
    Depends on tool reported string
    '''
    return '0'

def post_process(chip):
    return 0
