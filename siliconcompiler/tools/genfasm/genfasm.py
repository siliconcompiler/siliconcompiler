import os
import siliconcompiler
import re

######################################################################
# Make Docs
######################################################################

def make_docs():
    '''
    To-Do: Add details here
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

    tool = 'genfasm'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)
    chip.set('tool', tool, 'threads', step, index, os.cpu_count(), clobber=False)


    topmodule = chip.get_entrypoint()
    blif = f"inputs/{topmodule}.blif"

    options = []

    for arch in chip.get('fpga','arch'):
        options.append(arch)

    options.append(blif)

    options.extend( [ f"--net_file inputs/{topmodule}.net",
                f"--place_file inputs/{topmodule}.place",
                f"--route_file inputs/{topmodule}.route"])

    chip.add('tool', tool, 'option', step, index,  options)



#############################################
# Runtime pre processing
#############################################
def pre_process(chip):

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    tool = "genfasm"

    chip.add('tool', tool, 'option', step, index,  [f"--route_chan_width {find_chann_width()}" ])



################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    return 0

################################
# Find the final channel width from the VPR report
##########################;######
def find_chann_width():
    vpr_std_out = f"inputs/vpr_stdout.log"
    with open(vpr_std_out, 'r') as vpr_report:
        for line in vpr_report:
            match = re.search("Circuit successfully routed with a channel width factor of (\d+)", line)
            if match:
                return match.group(1)

    return -1
##################################################
if __name__ == "__main__":


    chip = make_docs()
    chip.write_manifest("genfasm.json")
