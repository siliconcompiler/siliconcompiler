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
    chip.set('fpga', 'partname', 'example_arch_X005Y005')
    chip.load_target("fpgaflow_demo")
    setup_tool(chip)
    return chip


def setup_tool(chip, clobber=True):

    chip.set('tool', 'vpr', 'exe', 'vpr', clobber=clobber)
    chip.set('tool', 'vpr', 'vswitch', '--version')
    chip.set('tool', 'vpr', 'version', '>=8.1.0', clobber=clobber)


def runtime_options(chip, tool='vpr'):

    part_name = chip.get('fpga', 'partname')
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    design = chip.top()

    options = []

    topmodule = chip.top()
    blif = f"inputs/{topmodule}.blif"

    if chip.valid('fpga', part_name, 'file', 'archfile') and \
       chip.get('fpga', part_name, 'file', 'archfile'):

        archs = chip.find_files('fpga', part_name, 'file', 'archfile')

    else:
        archs = []

    if (len(archs) == 1):
        options.append(archs[0])
    elif (len(archs) == 0):
        chip.error("VPR requires an architecture file as one of its command line arguments",
                   fatal=True)
    else:
        chip.error("Only one architecture XML file can be passed to VPR", fatal=True)

    options.append(blif)

    threads = chip.get('tool', tool, 'task', task, 'threads', step=step, index=index)
    options.append(f"--num_workers {threads}")

    if (task == 'place'):
        # Confine VPR execution to packing and placement steps
        options.append('--pack')
        options.append('--place')
    elif (task == 'route'):
        options.append('--route')
        # To run only the routing step we need to pass in the placement files
        options.append(f'--net_file inputs/{design}.net')
        options.append(f'--place_file inputs/{design}.place')
    elif (task == 'bitstream'):
        options.append(f'--net_file inputs/{design}.net')
        options.append(f'--place_file inputs/{design}.place')
        options.append(f'--route_file inputs/{design}.route')
    else:
        chip.error(f"Specified task {task} doesn't map to a VPR operation", fatal=True)

    if 'sdc' in chip.getkeys('input', 'constraint'):
        sdc_file = f"--sdc_file {chip.get('input', 'constraint', 'sdc', step=step, index=index)}"
        options.append(sdc_file)
    else:
        options.append("--timing_analysis off")

    # Routing graph XML:
    if chip.valid('fpga', part_name, 'file', 'graphfile') and \
       chip.get('fpga', part_name, 'file', 'graphfile'):

        rr_graphs = chip.find_files('fpga', part_name, 'file', 'graphfile')

    else:
        rr_graphs = []

    if (len(rr_graphs) == 0):
        chip.logger.info("No VPR RR graph file specifed")
        chip.logger.info("Routing architecture will come from architecture XML file")
    elif (len(rr_graphs) == 1):
        options.append("--read_rr_graph " + rr_graphs[0])
    elif (len(rr_graphs) > 1):
        chip.error("Only one rr graph argument can be passed to VPR", fatal=True)

    # ***NOTE: For real FPGA chips you need to specify the routing channel
    #          width explicitly.  VPR requires an explicit routing channel
    #          with when --read_rr_graph is used (typically the case for
    #          real chips).  Otherwise VPR performs a binary search for
    #          the minimum routing channel width that the circuit fits in.
    # Given the above, it may be appropriate to couple these variables somehow,
    # but --route_chan_width CAN be used by itself.
    num_routing_channels = chip.get('fpga', part_name, 'var', 'channelwidth')

    if (len(num_routing_channels) == 0):
        chip.error("Number of routing channels not specified", fatal=True)
    elif (len(num_routing_channels) == 1):
        options.append("--route_chan_width " + num_routing_channels[0])
    elif (len(num_routing_channels) > 1):
        chip.error("Only one routing channel width argument can be passed to VPR", fatal=True)

    return options


################################
# Version Check
################################


def parse_version(stdout):

    # Example output of vpr --version:
    # Note that blank comment lines in this example
    # represent newlines printed by vpr --version

    # VPR FPGA Placement and Routing.
    # Version: 8.1.0-dev+c4156f225
    # Revision: v8.0.0-7887-gc4156f225
    # Compiled: 2023-06-14T17:32:05
    # Compiler: GNU 9.4.0 on Linux-5.14.0-1059-oem x86_64
    # Build Info: release IPO VTR_ASSERT_LEVEL=2
    #
    # University of Toronto
    # verilogtorouting.org
    # vtr-users@googlegroups.com
    # This is free open source code under MIT license.
    #
    #
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
