import os

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'bambu'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = chip.get_task(step, index)

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('tool', tool, 'exe', 'bambu')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.9.6', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', step, index, refdir, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', step, index, os.cpu_count(), clobber=False)
    chip.set('tool', tool, 'task', task, 'option', step, index, [])

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', step, index, chip.top() + '.v')

    # Schema requirements
    chip.add('tool', tool, 'task', task, 'require', step, index, 'input,hll,c')
