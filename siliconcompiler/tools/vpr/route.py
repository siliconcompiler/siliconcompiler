import os
import re
import shutil

from siliconcompiler.tools.vpr import vpr


def setup(chip):
    '''
    Perform automated place and route with VPR
    '''

    tool = 'vpr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # TO-DO: PRIOROTIZE the post-routing packing results?
    design = chip.top()
    chip.add('tool', tool, 'task', task, 'output', design + '.route', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', 'vpr_stdout.log', step=step, index=index)

    options = vpr.assemble_options(chip, tool)
    # Confine VPR execution to routing step
    options.append('--route')
    # To run only the routing step we need to pass in the placement files
    options.append(f'--net_file inputs/{design}.net')
    options.append(f'--place_file inputs/{design}.place')

    threads = chip.get('tool', tool, 'task', task, 'threads', step=step, index=index)
    options.append(f"--num_workers {threads}")

    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)

#############################################
# Runtime pre processing
#############################################


def pre_process(chip):

    # have to rename the net connected to unhooked pins from $undef to unconn
    # as VPR uses unconn keywords to identify unconnected pins

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.top()
    blif_file = f"{chip._getworkdir()}/{step}/{index}/inputs/{design}.blif"
    print(blif_file)
    with open(blif_file, 'r+') as f:
        netlist = f.read()
        f.seek(0)
        netlist = re.sub(r'\$undef', 'unconn', netlist)
        f.write(netlist)
        f.truncate()

################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    for file in chip.get('tool', 'vpr', 'task', task, 'output', step=step, index=index):
        shutil.copy(file, 'outputs')
    design = chip.top()
    # Forward all of the prior step inputs forward for bitstream generation
    shutil.copy(f'inputs/{design}.blif', 'outputs')
    shutil.copy(f'inputs/{design}.net', 'outputs')
    shutil.copy(f'inputs/{design}.place', 'outputs')
    # TODO: return error code
    return 0
