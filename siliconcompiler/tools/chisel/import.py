import os

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'chisel'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = chip.get_task(step, index)

    # Standard Setup
    refdir = 'tools/'+tool
    chip.set('tool', tool, 'exe', 'sbt')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=1.5.5', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', step, index,  refdir, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', step, index,  os.cpu_count(), clobber=False)

    design = chip.top()
    option = f'"runMain SCDriver --module {design} -o ../outputs/{design}.v"'
    chip.set('tool', tool, 'task', task, 'option', step, index,  option)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', step, index, chip.top() + '.v')

    chip.set('tool', tool, 'task', task, 'keep', step, index, ['build.sbt', 'SCDriver.scala'])
