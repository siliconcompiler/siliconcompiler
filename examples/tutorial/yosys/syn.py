import os
from siliconcompiler.tools.yosys import synth_post_process

################################################
# Mandatory Task Setup
###############################################

def setup(chip):
    ''' Tool specific function to run before step execution
    '''

    #TODO
    #2. put in require,input,output
    #3. fix dff/ties
    #4. add custom apr script from scratch
    #5. metrics/write data at end of tcl (no

    # hard coded values to keep things simple

    tool = 'yosys'
    task = 'syn'
    keypath = ['tool', tool, 'task', task]
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    # global tool setup
    chip.set('tool', tool, 'exe', 'yosys')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.48')
    chip.set('tool', tool, 'format', 'tcl')

    # per task options
    option = []
    option.append('-c')
    chip.set(*keypath, 'option', option, step=step, index=index)

    # universal regex parsing for warnings and errors
    chip.set(*keypath, 'regex', 'warnings', "Warning:", step=step, index=index)
    chip.set(*keypath, 'regex', 'errors', "^ERROR", step=step, index=index)

    # synthesis scripts taken locallyy
    refdir = os.path.dirname(os.path.abspath(__file__))
    chip.set(*keypath, 'refdir', refdir, step=step, index=index)
    chip.set(*keypath, 'script', 'syn.tcl', step=step, index=index)

    # defining input/output files ("ports") for flowgraph
    chip.set(*keypath, 'input', design + '.v', step=step, index=index)
    chip.set(*keypath, 'output', design + '.vg', step=step, index=index)
    chip.add(*keypath, 'output', design + '.netlist.json', step=step, index=index)

    # defining required set of varibales used by TCL for error handling
    chip.add(*keypath, 'task', task, 'require',
             ",".join(['asic', 'logiclib']),
             step=step, index=index)


################################################
# Metric Collection (strongly encouraged)
###############################################

def post_process(chip):
    synth_post_process(chip)
