import os
import re
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
    * **signoff**: Merge results (built-in)

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

    # Flow setup
    index = '0'
    for step in flowpipe:
        if re.match(r'join|maximum|minimum|verify', tools[step]):
            chip.set('flowgraph', step, index, 'function', tools[step])
        else:
            chip.set('flowgraph', step, index, 'tool', tools[step])
        # order
        if step == 'import':
            pass
        else:
            chip.add('flowgraph', step, index, 'input', prevstep, "0")

        prevstep = step


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
