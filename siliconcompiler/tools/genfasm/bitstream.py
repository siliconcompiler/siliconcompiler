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

    chip.add('tool', tool, 'task', task, 'option', [f"--route_chan_width {find_chann_width()}"],
             step=step, index=index)


################################
# Find the final channel width from the VPR report
################################
def find_chann_width():
    vpr_std_out = "inputs/vpr_stdout.log"
    with open(vpr_std_out, 'r') as vpr_report:
        search_line = r"Circuit successfully routed with a channel width factor of (\d+)"
        for line in vpr_report:
            match = re.search(search_line, line)
            if match:
                return match.group(1)
    return -1
