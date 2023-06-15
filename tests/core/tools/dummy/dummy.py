def setup(chip):
    chip.set('tool', 'dummy', 'exe', 'echo')
    chip.add('tool', 'dummy', 'task', 'import', 'output', chip.top() + '.v',
             step='import', index='0')


def parse_version(stdout):
    raise IndexError('This is an index error')
