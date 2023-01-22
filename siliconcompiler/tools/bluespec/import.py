import os

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'bluespec'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'import'

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('tool', tool, 'exe', 'bsc')
    # This is technically the 'verbose' flag, but used alone it happens to give
    # us the version and exit cleanly, so we'll use it here.
    chip.set('tool', tool, 'vswitch', '-v')
    chip.set('tool', tool, 'version', '>=2021.07', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', step, index,  refdir, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', step, index,  os.cpu_count(), clobber=False)
    chip.set('tool', tool, 'task', task, 'option', step, index,  [], clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task,'output', step, index, chip.top() + '.v')

    # Schema requirements
    chip.add('tool', tool, 'task', task,'require', step, index, 'input,hll,bsv')
