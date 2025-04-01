import os

def setup(chip):
    ''' Tool specific function to run before step execution
    '''


    # setup is flow specific
    flow = chip.get('option', 'flow')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    tool = chip.get('flowgraph', flow, step, index, 'tool')
    task = chip.get('flowgraph', flow, step, index, 'task')

    keypath = ['tool', tool, 'task', task]
    refdir = os.path.dirname(os.path.abspath(__file__))

    # global tool setup
    chip.set('tool', tool, 'exe', 'yosys')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.48')
    chip.set('tool', tool, 'format', 'tcl')

    # per tool options
    option = []
    option.append('-c')
    chip.set(*keypath, 'option', option, step=step, index=index)
    chip.set(*keypath, 'refdir', refdir, step=step, index=index)
    chip.set(*keypath, 'regex', 'warnings', "Warning:", step=step, index=index)
    chip.set(*keypath, 'regex', 'errors', "^ERROR", step=step, index=index)

    # synthesis script
    chip.set(*keypath, 'script', 'syn.tcl', step=step, index=index)
