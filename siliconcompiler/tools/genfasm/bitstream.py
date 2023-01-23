import os

def setup(chip):

    tool = 'genfasm'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    #TODO: fix below
    task = step

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)

    chip.set('tool', tool,  'task', task, 'threads', step, index, os.cpu_count(), clobber=False)

    topmodule = chip.top()
    blif = f"inputs/{topmodule}.blif"

    options = []

    for arch in chip.get('fpga','arch'):
        options.append(arch)

    options.append(blif)

    options.extend( [ f"--net_file inputs/{topmodule}.net",
                f"--place_file inputs/{topmodule}.place",
                f"--route_file inputs/{topmodule}.route"])

    chip.add('tool', tool, 'task', task, 'option', step, index,  options)

