import importlib
import os
import siliconcompiler
import re

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A configurable FPGA compilation flow.
.
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
    setup_flow(chip)

    return chip

############################################################################
# Flowgraph Setup
############################################################################
def setup_flow(chip):
    '''
    Setup function for 'fpgaflow'

    Args:
        chip (object): SC Chip object

    '''

    if chip.get('fpga', 'partname'):
        partname = chip.get('fpga', 'partname')
    else:
        partname = "UNDEFINED"

    # Partname lookup
    (vendor, flow) = flow_lookup(partname)
    chip.set('fpga', 'vendor', vendor)

    #Setting up pipeline
    #TODO: Going forward we want to standardize steps
    if  flow in ('vivado', 'quartus'):
        flowpipe = ['import', 'syn', 'place', 'route', 'bitstream']
    else:
        flowpipe = ['import', 'syn', 'apr', 'bitstream']

    # Set the steplist which can run remotely (if required)
    chip.set('remote', 'steplist', flowpipe[1:])

    # Minimal setup
    index = '0'
    for i, step in enumerate(flowpipe):

        # Metrics
        chip.set('flowgraph', step, index, 'weight',  'cellarea', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'peakpower', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'standbypower', 1.0)

        # Goals
        chip.set('metric', step, index, 'drv', 'errors', 0)
        chip.set('metric', step, index, 'drv', 'goal', 0.0)
        chip.set('metric', step, index, 'holdwns', 'goal', 0.0)
        chip.set('metric', step, index, 'holdtns', 'goal', 0.0)
        chip.set('metric', step, index, 'setupwns', 'goal', 0.0)
        chip.set('metric', step, index, 'setuptns', 'goal', 0.0)

        # Inputs
        if i > 0:
            chip.add('flowgraph', flowpipe[i], index, 'input', flowpipe[i-1], "0")

        # Tools
        tool = tool_lookup(flow, step)
        chip.set('flowgraph', step, index, 'tool', tool)

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

    # common first step
    if step == "import":
        tool = 'verilator'
    # open source ice40 flow
    elif flow == "yosys-nextpnr":
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
    chip.writecfg("fpgaflow.json")
