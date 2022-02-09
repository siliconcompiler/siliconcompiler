import siliconcompiler
import re
import sys

from siliconcompiler.flows._common import setup_frontend

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A configurable FPGA compilation flow.

    The 'fpgaflow' module is a configurable FPGA flow with support for
    open source and commercial tool flows. The fpgaflow relies on the
    FPGA partname to determine which design tools to use for RTL to
    bitstream generation. All flows go through a common design import
    step that collects all source files from disk before proceeding.
    The implementation pipeline and tools used depend on the FPGA
    device being targeted. The following step convention is recommended
    for tools.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **apr**: FPGA specific placement and routing step
    * **bitstream**: Bitstream generation
    * **program**: Program the device

    Some FPGA target flows have a single 'compile' step that combines the
    syn, apr, and bitstream steps.

    The fpgaflow can be configured througthe following schema parameters

    Schema keypaths:

    * ['fpga', 'partname']: Used to select partname to vendor and tool flow
    * ['fpga', 'program']: Used to turn on/off HW programming step

    '''

    chip = siliconcompiler.Chip()
    chip.set('flow', 'fpgaflow')
    chip.set('fpga', 'partname', '<fpga-partname>')
    setup(chip)

    return chip

############################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='fpgaflow'):
    '''
    Setup function for 'fpgaflow'

    Args:
        chip (object): SC Chip object

    '''

    # Check that partname has been set

    if chip.get('fpga', 'partname'):
        partname = chip.get('fpga', 'partname')
    else:
        chip.logger.error("FPGA partname not specified")
        sys.exit()

    # Set FPGA mode if not set
    chip.set('mode', 'fpga')

    # Partname lookup
    (vendor, flow) = flow_lookup(partname)
    chip.set('fpga', 'vendor', vendor)

    #Setting up pipeline
    #TODO: Going forward we want to standardize steps
    if  flow in ('vivado', 'quartus'):
        flowpipe = ['syn', 'place', 'route', 'bitstream']
    else:
        flowpipe = ['syn', 'apr', 'bitstream']

    flowtools = setup_frontend(chip)
    for step in flowpipe:
        flowtools.append((step, tool_lookup(flow, step)))

    # Minimal setup
    index = '0'
    for step, tool in flowtools:
        # Flow
        chip.node(flowname, step, tool)
        if step != 'import':
            chip.edge(flowname, prevstep, step)
        # Hard goals
        for metric in ('errors','warnings','drvs','unconstrained',
                       'holdwns','holdtns', 'holdpaths',
                       'setupwns', 'setuptns', 'setuppaths'):
            chip.set('metric', step, index, metric, 'goal', 0)
        # Metrics
        for metric in ('luts','dsps','brams','registers',
                       'pins','peakpower','standbypower'):
            chip.set('flowgraph', flowname, step, index, 'weight', metric, 1.0)
        prevstep = step

##################################################

def flow_lookup(partname):
    '''
    Returns a flow,vendor tuple based on a partnumber
    regular expression.
    '''

    partname = partname.lower()

    ###########
    # xilinx
    ###########

    spartan6 = bool(re.match('^xc6', partname))
    spartan7 = bool(re.match('^xc7s', partname))
    artix = bool(re.match('^xc7a', partname))
    artixultra = bool(re.match('^au', partname))
    kintex7 = bool(re.match('^xc7k', partname))
    kintexultra = bool(re.match('^xcku', partname))
    zynq = bool(re.match('^z\-7', partname))
    zynqultra = bool(re.match('^zu', partname))
    virtex7 = bool(re.match('^xc7v', partname))
    virtexultra = bool(re.match('^xcvu', partname))

    xilinx = (spartan6 | spartan7 |
              artix | artixultra |
              kintex7 | kintexultra |
              zynq | zynqultra |
              virtex7 | virtexultra)

    #############
    # intel
    #############

    cyclone4 = bool(re.match('^ep4', partname))
    cyclone5 = bool(re.match('^5cs', partname))
    cyclone10 = bool(re.match('^10cl', partname))
    stratix5 = bool(re.match('^5sg', partname))

    intel = (cyclone10 | cyclone4 | cyclone5 |
             stratix5)

    ###########
    # yosys
    ###########

    ice40 = re.match('^ice40', partname)

    ###########
    # openfpga
    ###########

    openfpga = re.match('^openfpga', partname)

    if xilinx:
        vendor = 'xilinx'
        flow = 'vivado'
    elif intel:
        vendor = 'intel'
        flow = 'quartus'
    elif ice40:
        vendor = 'lattice'
        flow = 'yosys-nextpnr'
    elif openfpga:
        vendor = 'openfpga'
        flow = 'openfpga'
    else:
        vendor = 'openfpga'
        flow = 'openfpga'

    return (vendor, flow)

##################################################

def tool_lookup(flow, step):
    '''
    Return tool based on flow and step combo.
    '''

    '''
    Utility function for looking up tool
    based on flow and step.
    '''

    # open source ice40 flow
    if flow == "yosys-nextpnr":
        if step == "syn":
            tool = "yosys"
        elif step == "apr":
            tool = "nextpnr"
        elif step == "bitstream":
            tool = "icepack"
        elif step == "program":
            tool = "iceprog"
    # experimental flow
    elif flow == "openfpga":
        if step == "syn":
            tool = "yosys"
        else:
            tool = 'openfpga'
    # intel/quartus
    elif flow == "quartus":
        tool = 'quartus'
    # xilinx/vivado
    elif flow == "vivado":
        tool = 'vivado'

    return tool

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("fpgaflow.png")
