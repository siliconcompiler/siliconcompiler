import siliconcompiler
import re

from siliconcompiler.flows._common import setup_frontend

############################################################################
# DOCS
############################################################################
def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40')
    return setup(chip)

############################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='fpgaflow'):
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

    flow = siliconcompiler.Flow(chip, flowname)

    # Check that fpga arch has been set for vpr flow or partname has been set for others
    flowtype = ''
    if chip.get('fpga', 'arch'):
        flowtype = 'vpr'
    elif chip.get('fpga', 'partname'):
        partname = chip.get('fpga', 'partname')
    else:
        chip.error('FPGA partname not specified', fatal=True)

    # Partname lookup for flows other than vpr
    if flowtype != 'vpr':
        _, flowtype = flow_lookup(partname)

    #Setting up pipeline
    #TODO: Going forward we want to standardize steps
    if  flowtype in ('vivado', 'quartus'):
        flowpipe = ['syn_fpga', 'place', 'route', 'bitstream']
    elif flowtype =='vpr':
        flowpipe = ['syn_vpr', 'apr', 'bitstream']
        # flowpipe = ['syn_vpr', 'apr']
    else:
        flowpipe = ['syn_fpga', 'apr', 'bitstream']

    flowtools = setup_frontend(chip)
    for step in flowpipe:
        task = step
        if (step == 'syn_vpr') and (flowtype == 'vpr'):
            task = 'syn_fpga'
        flowtools.append((step, tool_lookup(flowtype, step), task))

    # Minimal setup
    index = '0'
    for step,tool,task in flowtools:
        # Flow
        flow.node(flowname, step, tool,task)
        if task != 'import':
            flow.edge(flowname, prevstep, step)
        # Hard goals
        for metric in ('errors','warnings','drvs','unconstrained',
                       'holdwns','holdtns', 'holdpaths',
                       'setupwns', 'setuptns', 'setuppaths'):
            flow.set('flowgraph', flowname, step, index, 'goal', metric, 0)
        # Metrics
        for metric in ('luts','dsps','brams','registers',
                       'pins','peakpower','leakagepower'):
            flow.set('flowgraph', flowname, step, index, 'weight', metric, 1.0)
        prevstep = step

    return flow

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
    zynq = bool(re.match(r'^z\-7', partname))
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

    if xilinx:
        vendor = 'xilinx'
        flow = 'vivado'
    elif intel:
        vendor = 'intel'
        flow = 'quartus'
    elif ice40:
        vendor = 'lattice'
        flow = 'yosys-nextpnr'
    else:
        raise siliconcompiler.SiliconCompilerError(
            f'fpgaflow: unsupported partname {partname}'
        )

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
        if step == "syn_fpga":
            tool = "yosys"
        elif step == "apr":
            tool = "nextpnr"
        elif step == "bitstream":
            tool = "icepack"
        elif step == "program":
            tool = "iceprog"
    # intel/quartus
    elif flow == "quartus":
        tool = 'quartus'
    # xilinx/vivado
    elif flow == "vivado":
        tool = 'vivado'
    # open source vpr flow
    elif flow == 'vpr':
        if step == "syn_vpr":
            tool = "yosys"
        elif step == "apr":
            tool = "vpr"
        else:
            tool = "genfasm"

    return tool

##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
