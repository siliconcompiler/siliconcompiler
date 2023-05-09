import os
import re


def setup(chip):
    '''
    Generates a bitstream
    '''
    tool = 'genfasm'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    topmodule = chip.top()
    blif = f"inputs/{topmodule}.blif"

    options = []

    for arch in chip.get('fpga', 'arch'):
        options.append(arch)

    options.append(blif)

    if 'sdc' in chip.getkeys('input'):
        options.append(f"--sdc_file {chip.get('input', 'fpga', 'sdc', step=step, index=index)}")
    else :
        options.append(f"--timing_analysis off")
        
    #Routing graph XML:
    rr_graph_files = chip.get('tool', 'vpr', 'task', 'apr', 'var', 'rr_graph')
    #if (len(rr_graph_files) == 1) :
    options.append(f"--read_rr_graph "+rr_graph_files[0])

    #***NOTE:  For real FPGA chips you need to specify the routing channel
    #          width explicitly.  VPR requires an explicit routing channel
    #          with when --read_rr_graph is used (typically the case for
    #          real chips).  Otherwise VPR performs a binary search for
    #          the minimum routing channel width that the circuit fits in.
    #          -PG 1/13/2023
    #Given the above, it may be appropriate to couple these variables somehow,
    #but --route_chan_width CAN be used by itself.
    num_routing_channels = chip.get('tool', 'vpr', 'task', 'apr', 'var', 'route_chan_width')
    if (len(num_routing_channels) == 1) :
        options.append(f'--route_chan_width {num_routing_channels[0]}')
    
    options.extend([f"--net_file inputs/{topmodule}.net",
                    f"--place_file inputs/{topmodule}.place",
                    f"--route_file inputs/{topmodule}.route"])

    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)


#############################################
# Runtime pre processing
#############################################
def pre_process(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    tool = "genfasm"

