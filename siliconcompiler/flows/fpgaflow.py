import siliconcompiler
import re

from siliconcompiler import SiliconCompilerError
from siliconcompiler.flows._common import setup_multiple_frontends
from siliconcompiler.flows._common import _make_docs

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
    _make_docs(chip)
    chip.set('fpga', 'partname', 'example_arch')
    return setup(chip)


############################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='fpgaflow', fpgaflow_type=None, partname=None):
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

    Args:
        - fpgaflow_type (str): this parameter can be used to select a specific
          fpga flow instead of one selected from the partname.
        - partname (str): this parameter can be used to select a specific fpga
          flow instead of one selected from the partname set in the schema.
    '''

    flow = siliconcompiler.Flow(chip, flowname)

    if not partname:
        partname = chip.get('fpga', 'partname')

    if fpgaflow_type:
        flow_pipe = flow_lookup_by_type(fpgaflow_type)
    else:
        flow_pipe = flow_lookup(partname)

    # Minimal setup
    prevstep = setup_multiple_frontends(chip, flow)
    for step, tool_module in flow_pipe:
        # Flow
        flow.node(flowname, step, tool_module)
        if prevstep:
            flow.edge(flowname, prevstep, step)
        # Hard goals
        for metric in ('errors', 'warnings', 'drvs', 'unconstrained',
                       'holdwns', 'holdtns', 'holdpaths',
                       'setupwns', 'setuptns', 'setuppaths'):
            flow.set('flowgraph', flowname, step, '0', 'goal', metric, 0)
        # Metrics
        for metric in ('luts', 'dsps', 'brams', 'registers', 'pins'):
            flow.set('flowgraph', flowname, step, '0', 'weight', metric, 1.0)
        prevstep = step

    return flow


##################################################
def flow_lookup_by_type(name):
    '''
    Returns a list for the the flow selected based on name of the flow type.
    '''

    vivado_flow = [
        ('syn_fpga', vivado_syn),
        ('place', vivado_place),
        ('route', vivado_route),
        ('bitstream', vivado_bitstream)]
    nextpnr_flow = [('syn', yosys_syn),
                    ('apr', nextpnr_apr)]
    vpr_flow = [('syn', yosys_syn),
                ('place', vpr_place),
                ('route', vpr_route),
                ('bitstream', genfasm_bitstream)]

    flow_map = {
        "vivado": vivado_flow,
        "nextpnr": nextpnr_flow,
        "vpr": vpr_flow
    }

    if name not in flow_map:
        raise SiliconCompilerError(f'{name} is not a supported FPGA flow type')

    return flow_map[name]


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

    #############
    # intel
    #############

    cyclone4 = bool(re.match('^ep4', partname))
    cyclone5 = bool(re.match('^5cs', partname))
    cyclone10 = bool(re.match('^10cl', partname))
    stratix5 = bool(re.match('^5sg', partname))

    intel = cyclone10 or cyclone4 or cyclone5 or stratix5

    ###########
    # lattice
    ###########

    ice40 = re.match('^ice40', partname)

    ###########
    # example
    ###########

    example = re.match('^example_arch', partname)

    flow = None
    if xilinx:
        flow = flow_lookup_by_type('vivado')
    elif intel:
        flow = flow_lookup_by_type('intel')
    elif ice40:
        flow = flow_lookup_by_type('nextpnr')
    elif example:
        flow = flow_lookup_by_type('vpr')

    if not flow:
        raise SiliconCompilerError(
            f'fpgaflow: unsupported partname {partname}'
        )

    return flow


##################################################
if __name__ == "__main__":
    chip = siliconcompiler.Chip('design')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
