import importlib
import os
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, process):
    '''
    This is a standard open source ASIC flow. The flow supports SystemVerilog,
    VHDL, and mixed SystemVerilog/VHDL flows. The asic flow is a linera
    pipeline that includes the stages below.

    * **import**: Sources are collected and packaged for compilation

    * **syn**: Translates RTL to netlist using Yosys

    * **floorplan**: Floorplanning

    * **physyn**: Physical Synthesis

    * **place**: Global and detailed placement

    * **cts**: Clock tree synthesis

    * **route**: Global and detailed routing

    * **dfm**: Metal fill, atenna fixes and any other post routing steps

    * **export**: Export design from APR tool and merge with library GDS

    * **sta**: Static timing analysis (signoff)

    * **lvs**: Layout versus schematic check (signoff)

    * **drc**: Design rule check (signoff)

    * **package**: Package design for reuse

    * **archive**: Archive design

    Args:
        process (string): Specifies the the process of the compilation.
            Used in complex flows and reserved for future use.

    '''


    # A simple linear flow
    flowpipe = ['import',
                'syn',
                'floorplan',
                'physyn',
                'place',
                'cts',
                'route',
                'dfm',
                'export'
    ]

    tools = {
        'import': 'verilator',
        'syn': 'yosys',
        'apr': 'openroad',
        'floorplan': 'openroad',
        'physyn': 'openroad',
        'place': 'openroad',
        'cts': 'openroad',
        'route': 'openroad',
        'dfm': 'openroad',
        'drc': 'magic',
        'lvs': 'magic',
        'export': 'klayout'
    }

    # TODO: implement these steps for processes other than Skywater
    verification_steps = [ 'lvs', 'drc']
    if process == 'skywater130':
        flowpipe += verification_steps


    # Flow setup
    N = 1
    index = '0'

    for i in range(len(flowpipe)):
        step = flowpipe[i]

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
