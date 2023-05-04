import os
import shutil


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    tool = 'chisel'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'sbt')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=1.5.5', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    design = chip.top()
    option = f'"runMain SCDriver --module {design} -o ../outputs/{design}.v"'
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'keep', ['build.sbt', 'SCDriver.scala'],
             step=step, index=index)


def pre_process(chip):
    tool = 'chisel'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    refdir = chip.find_files('tool', tool, 'task', task, 'refdir', step=step, index=index)[0]

    for filename in ('build.sbt', 'SCDriver.scala'):
        src = os.path.join(refdir, filename)
        dst = filename
        shutil.copyfile(src, dst)

    # Chisel driver relies on Scala files being collected into '$CWD/inputs'
    chip.set('input', 'hll', 'scala', True, field='copy')
    chip._collect(directory=os.path.join(chip._getworkdir(step=step, index=index), 'inputs'))
