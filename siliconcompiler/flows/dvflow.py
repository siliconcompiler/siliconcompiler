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

    chip = siliconcompiler.Chip('<topmodule>')
    chip.set('option', 'flow', 'dvflow')
    chip.set('arg', 'flow', 'np', '5')
    setup(chip)

    return chip

#############################################################################
# Flowgraph Setup
#############################################################################
def setup(chip, flow='dflow'):
    '''
    Setup function for 'dvflow'
    '''

    # Definting a flow
    flow = 'dvflow'

    # A simple linear flow
    flowpipe = ['import',
                'compile',
                'testgen',
                'refsim',
                'sim',
                'compare',
                'signoff']

    tools = {
        'import': ('verilator', 'import'),
        'compile': ('verilator', 'compile'),
        'testgen': ('verilator', 'testgen'),
        'refsim': ('verilator', 'refsim'),
        'sim': ('verilator', 'sim'),
        'compare': ('verilator', 'compare'),
        'signoff': ('verify', 'signoff')
    }


    # Parallelism
    if 'np' in chip.getkeys('arg', 'flow'):
        np = int(chip.get('arg', 'flow', 'np')[0])
    else:
        np = 1

    # Setting mode as 'sim'
    chip.set('option', 'mode', 'sim')

    # Flow setup
    for step in flowpipe:
        tool, task = tools[step]
        #start
        if step == 'import':
            chip.node(flow, step, tool, task)
        #serial
        elif step == 'compile':
            chip.node(flow, step, tool, task)
            chip.edge(flow, prevstep, step)
        #fork
        elif step == 'testgen':
            for index in range(np):
                chip.node(flow, step, tool, task, index=index)
                chip.edge(flow, prevstep, step, head_index=index)
        #join
        elif step == 'signoff':
            chip.node(flow, step, tool, task)
            for index in range(np):
                chip.edge(flow, prevstep, step, tail_index=index)
        else:
            for index in range(np):
                chip.node(flow, step, tool, task, index=index)
                chip.edge(flow, prevstep, step, head_index=index, tail_index=index)

        prevstep = step

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("dvflow.png")
