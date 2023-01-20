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

#############################################
# Runtime pre processing
#############################################
def pre_process(chip):

    step = chip.get('arg','step')
    index = chip.get('arg','index')
    #TODO: fix below
    task = step
    tool = "genfasm"

    chip.add('tool', tool, 'task', task, 'option', step, index,  [f"--route_chan_width {find_chann_width()}" ])



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
            match = re.search(r"Circuit successfully routed with a channel width factor of (\d+)", line)
            if match:
                return match.group(1)

    return -1
##################################################
if __name__ == "__main__":


    chip = make_docs()
    chip.write_manifest("genfasm.json")
