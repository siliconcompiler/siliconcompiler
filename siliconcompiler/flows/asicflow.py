import importlib
import os
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, process):
    '''
    This is a standard open source ASIC flow based on high quality tools.
    The flow supports SystemVerilog, VHDL, and mixed SystemVerilog/VHDL 
    flows. The asic flow is a linera pipeline that includes the 
    stages below. To skip the last three verification steps, you can
    specify "-stop export" at the command line.

    import: Sources are collected and packaged for compilation.
            A design manifest is created to simplify design sharing.

    syn: Translates RTL to netlist using Yosys

    synopt: Timing driven synthesis

    floorplan: Floorplanning

    place: Gloal placement

    cts: Clock tree synthesis

    route: Global and detailed routing

    dfm: Metal fill, atenna fixes and any other post routing steps

    export: Merge library GDS files with design DEF to produce a single GDS

    sta: Signoff static timing analysis

    lvs: Layout versus schematic check

    drc: Design rule check
  
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

    for i in range(len(flowpipe)-1):
        chip.add('flowgraph', flowpipe[i], 'output', flowpipe[i+1])

    # Per step tool selection
    for step in flowpipe:
        if step == 'import':
            #tool = 'morty'
            #tool = 'surelog'
            tool = 'verilator'
        elif step == 'importvhdl':
            tool = 'ghdl'
        elif step == 'convert':
            tool = 'sv2v' 
        elif step == 'syn':
            tool = 'yosys'
        elif step == 'export':
            tool = 'klayout'
        elif step in ('lvs', 'drc'):
            tool = 'magic' 
        else:
            tool = 'openroad'
        chip.set('flowgraph', step, 'tool', tool)


##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_flow(chip, "freepdk45")
    # write out results
    chip.writecfg(output)
    chip.write_flowgraph(prefix + ".svg")
