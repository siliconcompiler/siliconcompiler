import importlib
import os
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, process):
    '''
    Basic parallel testing flow.

    * **import**: Sources are collected and packaged for compilation

    * **compile**: Design compilation

    * **testgen**: Test generator

    * **refsim**: Reference simulation

    * **sim**: Design simulation

    * **compare**: Compare results

    * **validate**: Compare results (built-in)

    * **signoff**: Merge results (built-in)

    '''

    # A simple linear flow
    flowpipe = ['import',
                'compile',
                'testgen',
                'refsim',
                'sim',
                'compare',
                'validate',
                'signoff',


    ]

    tools = {
        'import': 'verilator',
        'compile': 'verilator',
        'testgen': 'fuzzer',
        'refsim': 'risc-v-sim',
        'sim': './a.out',
        'compare': 'diff',
        'validate': 'builtin',
        'signoff': 'builtin',
    }

    # Flow setup
    N = 1
    index = '0'

    for i in range(len(flowpipe)):
        step = flowpipe[i]
        if step == 'import':
        # Tool
        chip.set('flowgraph', step, index, 'tool', tools[step])

        # Flow
        if step != 'import':
            chip.add('flowgraph', step, index, 'input', flowpipe[i-1], "0")

        # Metrics
        chip.set('flowgraph', step, index, 'weight',  'cellarea', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'peakpower', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'standbypower', 1.0)

        # Goals
        chip.set('metric', step, index, 'drv', 'goal', 0.0)
        chip.set('metric', step, index, 'holdwns', 'goal', 0.0)
        chip.set('metric', step, index, 'holdtns', 'goal', 0.0)
        chip.set('metric', step, index, 'setupwns', 'goal', 0.0)
        chip.set('metric', step, index, 'setuptns', 'goal', 0.0)


    # Set the steplist which can run remotely (if required)
    chip.set('remote', 'steplist', flowpipe[1:])

    # Showtool definitions
    chip.set('showtool', 'def', 'openroad')
    chip.set('showtool', 'gds', 'klayout')


##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_flow(chip, "freepdk45")
    # write out results
    chip.writecfg(output)
    chip.writegraph(prefix + ".png")
