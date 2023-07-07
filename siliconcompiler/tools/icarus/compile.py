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

    chip.add('tool', tool, 'task', task, 'require', 'input,rtl,verilog',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    options = ['-o', f'outputs/{design}.vvp']
    options += ['-s', chip.top()]

    for libext in chip.get('option', 'libext'):
        options.append(f'-Y.{libext}')

    verilog_gen = chip.get('tool', tool, 'task', task, 'var', 'verilog_generation',
                           step=step, index=index)
    if verilog_gen:
        options.append(f'-g{verilog_gen[0]}')

    chip.set('tool', tool, 'task', task, 'option', options, step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'verilog_generation',
             'Select Verilog language generation for Icarus to use. Legal values are '
             '"1995", "2001", "2001-noconfig", "2005", "2005-sv", "2009", or "2012". '
             'See the corresponding "-g" flags in the Icarus manual for more information.',
             field='help')
