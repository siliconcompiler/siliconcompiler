
def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # Standard Setup
    tool = 'ghdl'
    clobber = False

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    #TODO: fix below
    task = step

    chip.set('tool', tool, 'exe', 'ghdl')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=2.0.0-dev', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', step, index, '4', clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', step, index, '', clobber=clobber)
    chip.set('tool', tool, 'task', task, 'stdout', step, index, 'destination', 'output')
    chip.set('tool', tool, 'task', task, 'stdout', step, index, 'suffix', 'v')

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', step, index, 'input,rtl,vhdl')

    design = chip.top()

    chip.set('tool', tool, 'task', task, 'output', step, index, f'{design}.v')
