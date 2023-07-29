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


def setup_tool(chip, clobber=True):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', 'vpr', 'exe', 'vpr', clobber=clobber)
    chip.set('tool', 'vpr', 'vswitch', '--version')
    chip.set('tool', 'vpr', 'version', '>=8.1.0', clobber=clobber)

    chip.add('tool', 'vpr', 'task', task, 'require',
             ",".join(['tool', 'vpr', 'task', task, 'file', 'arch_file']),
             step=step, index=index)

    chip.add('tool', 'vpr', 'task', task, 'require',
             ",".join(['tool', 'vpr', 'task', task, 'var', 'route_chan_width']),
             step=step, index=index)


def assemble_options(chip, tool):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    options = []

    topmodule = chip.top()
    blif = f"inputs/{topmodule}.blif"

    for arch in chip.find_files('tool', 'vpr', 'task', task, 'file', 'arch_file',
                                step=step, index=index):
        options.append(arch)

    options.append(blif)

    if 'sdc' in chip.getkeys('input', 'constraint'):
        sdc_file = f"--sdc_file {chip.get('input', 'constraint', 'sdc', step=step, index=index)}"
        options.append(sdc_file)
    else:
        options.append("--timing_analysis off")

    # Routing graph XML:
    for rr_graph in chip.find_files('tool', 'vpr', 'task', task, 'file', 'rr_graph',
                                    step=step, index=index):

        options.append("--read_rr_graph " + rr_graph)

    # ***NOTE: For real FPGA chips you need to specify the routing channel
    #          width explicitly.  VPR requires an explicit routing channel
    #          with when --read_rr_graph is used (typically the case for
    #          real chips).  Otherwise VPR performs a binary search for
    #          the minimum routing channel width that the circuit fits in.
    # Given the above, it may be appropriate to couple these variables somehow,
    # but --route_chan_width CAN be used by itself.
    for num_routing_channels in chip.get('tool', 'vpr', 'task', task, 'var', 'route_chan_width',
                                         step=step, index=index):

        options.append(f'--route_chan_width {num_routing_channels}')

    # document parameters
    chip.set('tool', 'vpr', 'task', task, 'file', 'arch_file',
             'File name of XML architecture file for target FPGA part', field='help')
    chip.set('tool', 'vpr', 'task', task, 'var', 'route_chan_width',
             'FPGA part-specific number of routing channels in each array element', field='help')
    chip.set('tool', 'vpr', 'task', task, 'file', 'rr_graph',
             'File name of XML routing graph file for target FPGA part', field='help')

    return options


################################
# Version Check
################################


def parse_version(stdout):

    return stdout.split()[6]


def normalize_version(version):
    if '-' in version:
        return version.split('-')[0]
    else:
        return version


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("vpr.json")
