#fpga_yosys_vpr.py
#Peter Grossmann
#11 January 2023
#$Id$
#$Log$

import siliconcompiler
import re

from siliconcompiler.flows._common import setup_frontend

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A custom FPGA compilation flow for emulating F4PGA's Xilinx RTL to
    bitstream flow.

    The 'fpga_yosys_vpr' module is an FPGA flow tuned to work with
    Yosys + VPR for Xilinx devices supported by F4PGA (i.e. with known good
    VPR architecture files). 

    The following step convention is used in this flow.
    * **import**: Sources are collected and packaged for compilation
    * **syn**: Synthesize RTL into a device specific netlist with yosys
    * **place_route**: FPGA specific placement and routing step with VPR
    * **bitstream**: Bitstream generation--NOT YET IMPLEMENTED
    * **program**: Program the device--NOT YET IMPLEMENTED

    The fpga_yosys_vpr can be configured through the following schema parameters
    Schema keypaths:
    * ['fpga', 'partname']: Used to select partname to vendor and tool flow
    * ['fpga', 'program']: Used to turn on/off HW programming step
    '''

    chip = siliconcompiler.Chip('<topmodule>')
    chip.set('option', 'flow', 'fpga_yosys_vpr')
    chip.set('fpga', 'partname', 'xilinx')
    setup(chip)

    return chip

############################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='fpga_yosys_vpr'):
    '''
    Setup function for 'fpga_yosys_vpr'
    Args:
        chip (object): SC Chip object
    '''

    # Check that fpga arch has been set for vpr flow or partname has been set for others
    flow = 'vpr'

    #***TO DO:  Add something partname-related to help vet that the partname is
    #           is supported by this flow

    # Set FPGA mode if not set
    chip.set('option', 'mode', 'fpga')
    
    #Setting up pipeline
    flowpipe = ['syn', 'apr']

    flowtools = setup_frontend(chip)
    for step in flowpipe:
        if (step == "syn") :
            flowtools.append((step, "yosys"))
        elif (step == "apr") :
            flowtools.append((step, "vpr"))
            
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
            chip.set('flowgraph', flowname, step, index, 'goal', metric, 0)
        # Metrics
        for metric in ('luts','dsps','brams','registers',
                       'pins','peakpower','leakagepower'):
            chip.set('flowgraph', flowname, step, index, 'weight', metric, 1.0)
        prevstep = step

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("fpga_yosys_vpr.png")
