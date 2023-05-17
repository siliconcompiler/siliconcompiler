import siliconcompiler
import re

from siliconcompiler.flows._common import setup_frontend
from siliconcompiler.tools.yosys import syn_fpga
from siliconcompiler.tools.vpr import place
from siliconcompiler.tools.vpr import route
from siliconcompiler.tools.genfasm import bitstream

############################################################################
# DOCS
############################################################################
def make_docs(chip):
    return setup(chip)


############################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='fpgaflow'):
    '''
    A configurable FPGA compilation flow.

    The 'fpgaflow' module is a configurable FPGA flow with support for
    open source and commercial tool flows. 

    The following step convention is recommended
    for tools.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into an device specific netlist
    * **place**: FPGA specific placement and routing step
    * **route**: FPGA specific placement and routing step
    * **bitstream**: Bitstream generation

    The fpgaflow can be configured througthe following schema parameters

    Schema keypaths:

    '''

    flow = siliconcompiler.Flow(chip, flowname)

    # Setting up pipeline
    # TODO: Going forward we want to standardize steps
    flowpipe = ['syn', 'place', 'route', 'bitstream']

    tasks = {
        'syn': syn_fpga,
        'place': place,
        'route': route,
        'bitstream': bitstream
    }
    
    flowtools = setup_frontend(chip)
    for step in flowpipe:
        flowtools.append((step, tasks[step]))

    # Minimal setup
    index = '0'
    prevstep = None
    for step, task in flowtools:
        # Flow
        flow.node(flowname, step, task)
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
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
