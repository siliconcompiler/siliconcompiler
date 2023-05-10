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


######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    from tools.vpr.apr import setup
    setup(chip)
    return chip


def assemble_options(chip, tool):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    # task = chip._get_task(step, index)

    options = []

    topmodule = chip.top()
    blif = f"inputs/{topmodule}.blif"

    for arch in chip.get('fpga', 'arch'):
        options.append(arch)

    options.append(blif)

    if 'sdc' in chip.getkeys('input'):
        options.append(f"--sdc_file {chip.get('input', 'fpga', 'sdc', step=step, index=index)}")
    else:
        options.append("--timing_analysis off")

    # Routing graph XML:
    rr_graphs = chip.get('tool', 'vpr', 'task', 'apr', 'var', 'rr_graph', step=step, index=index)
    # if (len(rr_graph_files) == 1):
    options.append("--read_rr_graph " + rr_graphs[0])

    # ***NOTE: For real FPGA chips you need to specify the routing channel
    #          width explicitly.  VPR requires an explicit routing channel
    #          with when --read_rr_graph is used (typically the case for
    #          real chips).  Otherwise VPR performs a binary search for
    #          the minimum routing channel width that the circuit fits in.
    #          -PG 1/13/2023
    # Given the above, it may be appropriate to couple these variables somehow,
    # but --route_chan_width CAN be used by itself.
    num_routing_channels = chip.get('tool', 'vpr', 'task', 'apr', 'var', 'route_chan_width')
    if (len(num_routing_channels) == 1):
        options.append(f'--route_chan_width {num_routing_channels[0]}')

    return options


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("vpr.json")
