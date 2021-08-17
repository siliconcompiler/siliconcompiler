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

    * **rtlgen**: Generates netlist for the OpenFPGA architecture

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
    flowpipe = ['rtlgen',
                'import',
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
        #TODO: Set up metrics
        if i > 0:
            chip.add('flowgraph', flowpipe[i], 'input', flowpipe[i-1])

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
        elif step == 'rtlgen':
            tool = 'python3'
            # TODO: Should yosys be the show tool? (Output is .v sources)
            showtool = None
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

    # Save the FPGA design path, even though it is only used in the 'rtlgen' step.
    chip.status['openfpga_task_dir'] = os.path.abspath(os.path.dirname(chip.get('source')[0]) + '/..')
    # Configure the config dictionary for the ASIC flow.
    rtlgen_path = '/'.join([os.path.abspath(chip.get('build_dir')),
                            chip.get('design'),
                            f"job{chip.get('jobid')}",
                            f"rtlgen{chip.get('jobid')}"])
    # To avoid errors, bypass 'chip.set()' because the files don't exist yet.
    chip.cfg['source']['value'] = [rtlgen_path + '/outputs/SRC/fabric_netlists.v']
    chip.cfg['constraint']['value'] = [rtlgen_path + '/outputs/global_ports.sdc']

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
