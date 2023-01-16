import os

import siliconcompiler
import re
import shutil

######################################################################
# Make Docs
######################################################################

def make_docs():
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

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', 'apr')
    chip.set('arg','index', '<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################
def setup(chip):

    tool = 'vpr'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)
    chip.set('tool', tool, 'threads', step, index, os.cpu_count(), clobber=False)

    #TO-DO: PRIOROTIZE the post-routing packing results?
    design = chip.top()
    chip.set('tool', tool, 'output', step, index, design + '.net')
    chip.add('tool', tool, 'output', step, index, design + '.place')
    chip.add('tool', tool, 'output', step, index, design + '.route')
    chip.add('tool', tool, 'output', step, index, 'vpr_stdout.log')

    topmodule = chip.top()
    blif = "inputs/" + topmodule + ".blif"

    options = []
    for arch in chip.get('fpga','arch'):
        options.append(arch)

    options.append(blif)

    if 'sdc' in chip.getkeys('input'):
        options.append(f"--sdc_file {chip.get('input', 'sdc')}")
    else :
        options.append(f"--timing_analysis off")

    #***NOTE:  Eventually, I think we want this:
    #for rr_graph in chip.get('fpga','rr_graph'):
    #    options.append(f"--read_rr_graph "+rr_graph)
    #
    #But for now, implement this to avoid schema changes
    rr_graph_files = chip.get('tool', 'vpr', 'var', 'apr', '0', 'rr_graph')
    if (len(rr_graph_files) == 1) :
        options.append(f"--read_rr_graph "+rr_graph_files[0])

    #***NOTE:  For real FPGA chips you need to specify the routing channel
    #          width explicitly.  VPR requires an explicit routing channel
    #          with when --read_rr_graph is used (typically the case for
    #          real chips).  Otherwise VPR performs a binary search for
    #          the minimum routing channel width that the circuit fits in.
    #          -PG 1/13/2023
    #Given the above, it may be appropriate to couple these variables somehow,
    #but --route_chan_width CAN be used by itself.
    num_routing_channels = chip.get('tool', 'vpr', 'var', 'apr', '0', 'route_chan_width')
    if (len(num_routing_channels) == 1) :
        options.append(f"--route_chan_width "+num_routing_channels[0])
    
    threads = chip.get('tool', tool, 'threads', step, index)
    options.append(f"--num_workers {threads}")

    chip.add('tool', tool, 'option', step, index,  options)



#############################################
# Runtime pre processing
#############################################
def pre_process(chip):

    #have to rename the net connected to unhooked pins from $undef to unconn
    # as VPR uses unconn keywords to identify unconnected pins

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    design = chip.top()
    blif_file = f"{chip._getworkdir()}/{step}/{index}/inputs/{design}.blif"
    print(blif_file)
    with open(blif_file,'r+') as f:
        netlist = f.read()
        f.seek(0)
        netlist = re.sub('\$undef', 'unconn', netlist)
        f.write(netlist)
        f.truncate()

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    for file in chip.get('tool', 'vpr', 'output', step, index):
        shutil.copy(file, 'outputs')
    design = chip.top()
    shutil.copy(f'inputs/{design}.blif', 'outputs')
    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":


    chip = make_docs()
    chip.write_manifest("vpr.json")
