
def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'nextpnr'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'apr'

    topmodule = chip.top()

    clobber = False
    chip.set('tool', tool, 'exe', 'nextpnr-ice40')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.2', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'option', step, index, "", clobber=clobber)
    chip.set('tool', tool, 'task', task, 'input', step, index, f'{topmodule}_netlist.json')
    chip.set('tool', tool, 'task', task, 'output', step, index, f'{topmodule}.asc')

