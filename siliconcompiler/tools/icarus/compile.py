import os


def setup(chip):
    '''
    Compile the input verilog into a vvp file that can be simulated.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'icarus'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    # Standard Setup
    chip.set('tool', tool, 'exe', 'iverilog')
    chip.set('tool', tool, 'vswitch', '-V')
    chip.set('tool', tool, 'version', '>=10.3', clobber=False)

    # Only one task (compile)
    chip.add('tool', tool, 'task', task, 'require', 'input,rtl,verilog',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'option', f'-o outputs/{design}.vvp',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)
