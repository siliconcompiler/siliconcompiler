import os

from siliconcompiler.tools.vpr import vpr


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

    options = vpr.assemble_options(chip, tool)

    topmodule = chip.top()
    options.extend([f"--net_file inputs/{topmodule}.net",
                    f"--place_file inputs/{topmodule}.place",
                    f"--route_file inputs/{topmodule}.route"])

    chip.add('tool', tool, 'task', task, 'option', options, step=step, index=index)


#############################################
# Runtime pre processing
#############################################
# def pre_process(chip):

    # step = chip.get('arg', 'step')
    # index = chip.get('arg', 'index')
    # task = chip._get_task(step, index)
    # tool = "genfasm"
