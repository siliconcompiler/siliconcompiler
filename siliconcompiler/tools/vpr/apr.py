import os

def setup(chip):

    tool = 'vpr'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = 'apr'

    chip.set('tool', tool, 'exe', tool, clobber=False)
    chip.set('tool', tool, 'version', '0.0', clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', step, index, os.cpu_count(), clobber=False)

    #TO-DO: PRIOROTIZE the post-routing packing results?
    design = chip.top()
    chip.set('tool', tool, 'task', task, 'output', step, index, design + '.net')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.place')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.route')
    chip.add('tool', tool, 'task', task, 'output', step, index, 'vpr_stdout.log')

    topmodule = chip.top()
    blif = "inputs/" + topmodule + ".blif"

    options = []
    for arch in chip.get('fpga','arch'):
        options.append(arch)

    options.append(blif)

    if 'sdc' in chip.getkeys('input'):
        options.append(f"--sdc_file {chip.get('input', 'fpga', 'sdc')}")

    threads = chip.get('tool', tool, 'task', task, 'threads', step, index)
    options.append(f"--num_workers {threads}")

    chip.add('tool', tool, 'task', task, 'option', step, index,  options)
