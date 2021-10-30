import os
import re
import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A configurable constrained random stimulus DV flow.

    The verification pipeline includes the followins teps:

    * **import**: Sources are collected and packaged for compilation
    * **compile**: RTL sources are compiled into object form (once)
    * **testgen**: A random seed is used to generate a unique test
    * **refsim**: A golden trace of test is generated using a reference sim.
    * **sim**: Compiled RTL is exercised using generated test
    * **compare**: The outputs of the sim and refsim are compared
    * **signoff**: Parallel verification pipelines are merged and checked

    The dvflow can be parametrized using a single 'np' flowarg parameter.
    Setting 'np' > 1 results in multiple independent verificaiton
    pipelines to be launched.

    '''

    chip = siliconcompiler.Chip()
    setup_flow(chip)

    return chip

#############################################################################
# Flowgraph Setup
#############################################################################
def setup_flow(chip):
    '''
    Setup function for 'dvflow'
    '''

    # A simple linear flow
    flowpipe = ['import',
                'compile',
                'testgen',
                'refsim',
                'sim',
                'compare',
                'signoff']

    tools = {
        'import': 'verilator',
        'compile': 'verilator',
        'testgen': 'verilator',
        'refsim': 'verilator',
        'sim': 'verilator',
        'compare': 'verilator',
        'signoff': 'verify'
    }


    # Parallelism
    if 'np' in chip.getkeys('flowarg'):
        np = int(chip.get('flowarg', 'np')[0])
    else:
        np = 1

    # Setting mode as 'sim'
    chip.set('mode', 'sim')

    # Flow setup
    for step in flowpipe:
        #start
        if step == 'import':
            chip.set('flowgraph', step, '0', 'tool', tools[step])
        #serial
        elif step == 'compile':
            chip.set('flowgraph', step, '0', 'tool', tools[step])
            chip.set('flowgraph', step, '0', 'input', ('import', '0'))
        #fork
        elif step == 'testgen':
            for index in range(np):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.set('flowgraph', step, str(index), 'input', ('compile', '0'))
        #join
        elif step == 'signoff':
            chip.set('flowgraph', step, '0', 'tool', tools[step])
            for index in range(np):
                chip.add('flowgraph', step, '0', 'input', (prevstep, str(index)))
        else:
            for index in range(np):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.set('flowgraph', step, str(index), 'input', (prevstep, str(index)))

        prevstep = step

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.writecfg("dvflow.json")
