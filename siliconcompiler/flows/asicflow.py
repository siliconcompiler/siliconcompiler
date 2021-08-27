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

    * **synopt**: Timing driven synthesis

    * **floorplan**: Floorplanning

    * **place**: Gloal placement

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
                'synopt',
                'floorplan',
                'place',
                'cts',
                'route',
                'dfm',
                'export',
                # TODO: sta is currently broken, don't include in flow
                # 'sta'
                ]

    # TODO: implement these steps for processes other than Skywater
    verification_steps = [ 'lvs', 'drc']
    if process == 'skywater130':
        flowpipe += verification_steps

    # Setting up flowgraph
    for i, step in enumerate(flowpipe):
        chip.set('flowgraph', flowpipe[i], 'mergeop',  'min')
        chip.set('flowgraph', flowpipe[i], 'nproc',  1)
        for metric in chip.getkeys('metric','default', 'default'):
            chip.set('flowgraph', flowpipe[i], 'weight',  metric, 1.0)
        #TODO: Set up metrics
        if i > 0:
            chip.add('flowgraph', flowpipe[i], 'input',  flowpipe[i-1])
        else:
            chip.set('flowgraph', flowpipe[i], 'input',  'source')

    # Per step tool selection
    for step in flowpipe:
        if step == 'import':
            #tool = 'morty'
            #tool = 'surelog'
            tool = 'verilator'
            showtool = 'open'
        elif step == 'importvhdl':
            tool = 'ghdl'
            showtool = None
        elif step == 'convert':
            tool = 'sv2v'
            showtool = None
        elif step == 'syn':
            tool = 'yosys'
            showtool = 'yosys'
        elif step == 'export':
            tool = 'klayout'
            showtool = 'klayout'
        elif step in ('lvs', 'drc'):
            tool = 'magic'
            showtool = 'klayout'
        else:
            tool = 'openroad'
            showtool = 'openroad'
        chip.set('flowgraph', step, 'tool', tool)
        if showtool:
            chip.set('flowgraph', step, 'showtool', showtool)

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
    #chip.write_flowgraph(prefix + ".svg")
