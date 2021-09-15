import os
import re
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip):
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


    # Parallelism
    if 'np' in chip.getkeys('flowarg'):
        np = int(chip.get('flowarg', 'np')[0])
    else:
        np = 1

    # Flow setup
    for step in flowpipe:
        #start
        if step == 'import':
            chip.set('flowgraph', step, '0', 'tool', tools[step])
        #serial
        elif step == 'compile':
            chip.set('flowgraph', step, '0', 'tool', tools[step])
            chip.set('flowgraph', step, '0', 'input','import','0')
        #fork
        elif step == 'testgen':
            for index in range(np):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.set('flowgraph', step, str(index), 'input','compile','0')
        #join
        elif step == 'signoff':
            chip.set('flowgraph', step, '0', 'function', tools[step])
            for index in range(np):
                chip.add('flowgraph', step, '0', 'input', prevstep, str(index))
        else:
            for index in range(np):
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.set('flowgraph', step, str(index), 'input',prevstep,str(index))

        prevstep = step


##################################################
if __name__ == "__main__":

    prefix = os.path.splitext(os.path.basename(__file__))[0]
    chip = siliconcompiler.Chip()
    setup_flow(chip)
    chip.writecfg(prefix + '.json')
    chip.writegraph(prefix + ".png")
