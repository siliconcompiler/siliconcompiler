import importlib
import os
import siliconcompiler
import re
import sys

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

    # Set partname if not set
    partname = "UNDEFINED"
    if chip.get('fpga', 'partname'):
        partname = chip.get('fpga', 'partname')
    elif chip.get('target'):
        if len(chip.get('target').split('_')) == 2:
            partname = chip.get('target').split('_')[1]
    chip.set('fpga', 'partname', partname)

    # Set FPGA mode if not set
    chip.set('mode', 'fpga')

    # Partname lookup
    (vendor, flow) = flow_lookup(partname)
    chip.set('fpga', 'vendor', vendor)

    #Setting up pipeline
    #TODO: Going forward we want to standardize steps
    if  flow in ('vivado', 'quartus'):
        flowpipe = ['import', 'syn', 'place', 'route', 'bitstream']
    else:
        flowpipe = ['import', 'syn', 'apr', 'bitstream']

    # Perform SystemVerilog to Verilog conversion step only if `flowarg, sv` is True
    sv = ('sv' in chip.getkeys('flowarg') and
           len(chip.get('flowarg', 'sv')) > 0 and
           chip.get('flowarg', 'sv')[0] == 'true')
    if sv:
        flowpipe = flowpipe[:1] + ['convert'] + flowpipe[1:]

    # Minimal setup
    index = '0'
    for i, step in enumerate(flowpipe):
        # Flow
        tool = tool_lookup(flow, step)
        chip.node(step, tool)
        if i > 0:
            chip.edge(flowpipe[i-1], flowpipe[i])
        # Hard goals
        for metric in ('errors','warnings','drvs','unconstrained',
                       'holdwns','holdtns', 'holdpaths',
                       'setupwns', 'setuptns', 'setuppaths'):
            chip.set('metric', step, index, metric, 'goal', 0)
        # Metrics
        for metric in ('luts','dsps','brams','registers',
                       'pins','peakpower','standbypower'):
            chip.set('flowgraph', step, index, 'weight', metric, 1.0)

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
        tool = 'surelog'
    elif step == "convert":
        tool = 'sv2v'
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
