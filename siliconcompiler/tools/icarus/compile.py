import os
from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_input_files, get_frontend_options


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

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    options = ['-o', f'outputs/{design}.vvp']
    options += ['-s', chip.top()]

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

    add_require_input(chip, 'input', 'rtl', 'netlist')
    add_frontend_requires(chip, ['ydir', 'vlib', 'idir', 'cmdfile', 'define', 'libext'])


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returns list of command line options.
    '''

    cmdlist = []

    opts = get_frontend_options(chip, ['ydir', 'vlib', 'idir', 'cmdfile', 'define', 'libext'])

    for libext in opts['libext']:
        cmdlist.append(f'-Y.{libext}')

    # source files
    for value in opts['ydir']:
        cmdlist.append('-y ' + value)
    for value in opts['vlib']:
        cmdlist.append('-v ' + value)
    for value in opts['idir']:
        cmdlist.append('-I' + value)
    for value in opts['define']:
        cmdlist.append('-D' + value)
    for value in opts['cmdfile']:
        cmdlist.append('-f ' + value)
    for value in get_input_files(chip, 'input', 'rtl', 'verilog'):
        cmdlist.append(value)

    return cmdlist
