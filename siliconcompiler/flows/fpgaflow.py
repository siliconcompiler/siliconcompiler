import siliconcompiler
import re

from siliconcompiler import SiliconCompilerError
from siliconcompiler.flows._common import setup_frontend

from siliconcompiler.tools.yosys import syn_fpga as yosys_syn
from siliconcompiler.tools.vpr import place as vpr_place
from siliconcompiler.tools.vpr import route as vpr_route
from siliconcompiler.tools.genfasm import bitstream as genfasm_bitstream

from siliconcompiler.tools.vivado import syn_fpga as vivado_syn
from siliconcompiler.tools.vivado import place as vivado_place
from siliconcompiler.tools.vivado import route as vivado_route
from siliconcompiler.tools.vivado import bitstream as vivado_bitstream

from siliconcompiler.tools.nextpnr import apr as nextpnr_apr


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    return setup(chip)


############################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='fpgaflow'):
    '''
    A configurable FPGA compilation flow.

    The 'fpgaflow' module is a configurable FPGA flow with support for
    open source and commercial tool flows.

    The following step convention is recommended for VPR.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **place**: FPGA specific placement step
    * **route**: FPGA specific routing step
    * **bitstream**: Bitstream generation

    Note that nextpnr does not appear to support breaking placement, routing,
    and bitstream generation into individual steps, leading to the following
    recommended step convention

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **apr**: One-step execution of place, route, bitstream with nextpnr

    Schema keypaths:

    '''

    flow = siliconcompiler.Flow(chip, flowname)

    flow_pipe = flow_lookup(chip.get('fpga', 'partname'))

    flowtools = setup_frontend(chip)
    flowtools.extend(flow_pipe)

    # Minimal setup
    index = '0'
    prevstep = None
    for step, tool_module in flowtools:
        # Flow
        flow.node(flowname, step, tool_module)
        if prevstep:
            flow.edge(flowname, prevstep, step)
        # Hard goals
        for metric in ('errors', 'warnings', 'drvs', 'unconstrained',
                       'holdwns', 'holdtns', 'holdpaths',
                       'setupwns', 'setuptns', 'setuppaths'):
            flow.set('flowgraph', flowname, step, index, 'goal', metric, 0)
        # Metrics
        for metric in ('luts', 'dsps', 'brams', 'registers',
                       'pins', 'peakpower', 'leakagepower'):
            flow.set('flowgraph', flowname, step, index, 'weight', metric, 1.0)
        prevstep = step

    return flow


##################################################
def flow_lookup(partname):
    '''
    Returns a list for the the flow selected based on the part number
    regular expression.
    '''

    if not partname:
        raise SiliconCompilerError('A part number must be specified to setup the fpga flow.')

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

    xilinx = spartan6 or spartan7 or \
        artix or artixultra or \
        kintex7 or kintexultra or \
        zynq or zynqultra or \
        virtex7 or virtexultra
    xilinx_flow = [
        ('syn_fpga', vivado_syn),
        ('place', vivado_place),
        ('route', vivado_route),
        ('bitstream', vivado_bitstream)]

    #############
    # intel
    #############

    cyclone4 = bool(re.match('^ep4', partname))
    cyclone5 = bool(re.match('^5cs', partname))
    cyclone10 = bool(re.match('^10cl', partname))
    stratix5 = bool(re.match('^5sg', partname))

    intel = cyclone10 or cyclone4 or cyclone5 or stratix5
    intel_flow = None

    ###########
    # lattice
    ###########

    ice40 = re.match('^ice40', partname)
    ice40_flow = [('syn', yosys_syn),
                  ('apr', nextpnr_apr)]

    ###########
    # example
    ###########

    example = re.match('^example_arch', partname)
    example_flow = [('syn', yosys_syn),
                    ('place', vpr_place),
                    ('route', vpr_route),
                    ('bitstream', genfasm_bitstream)]

    flow = None
    if xilinx:
        flow = xilinx_flow
    elif intel:
        flow = intel_flow
    elif ice40:
        flow = ice40_flow
    elif example:
        flow = example_flow

    if not flow:
        raise SiliconCompilerError(
            f'fpgaflow: unsupported partname {partname}'
        )

    return flow


##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
