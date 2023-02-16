'''
VPR (Versatile Place and Route) is an open source CAD
tool designed for the exploration of new FPGA architectures and
CAD algorithms, at the packing, placement and routing phases of
the CAD flow. VPR takes, as input, a description of an FPGA
architecture along with a technology-mapped user circuit. It
then performs packing, placement, and routing to map the
circuit onto the FPGA. The output of VPR includes the FPGA
configuration needed to implement the circuit and statistics about
the final mapped design (eg. critical path delay, area, etc).

Documentation: https://docs.verilogtorouting.org/en/latest

Sources: https://github.com/verilog-to-routing/vtr-verilog-to-routing

Installation: https://github.com/verilog-to-routing/vtr-verilog-to-routing
'''

import siliconcompiler

######################################################################
# Make Docs
######################################################################
def make_docs(chip):


    chip = siliconcompiler.Chip('<design>')
    step = 'apr'
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    from tools.vpr.apr import setup
    setup(chip)
    return chip

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("vpr.json")
