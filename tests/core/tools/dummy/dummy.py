def setup(chip):
    chip.set('tool', 'dummy', 'exe', 'echo')
    chip.set('tool', 'dummy', 'vswitch', '--version')
    chip.set('tool', 'dummy', 'version', '>=1.13', clobber=False)
    chip.add('tool', 'dummy', 'task', 'import', 'output', chip.top() + '.v', step='import', index='0')


def parse_version(stdout):
    raise IndexError('This is an index error')
