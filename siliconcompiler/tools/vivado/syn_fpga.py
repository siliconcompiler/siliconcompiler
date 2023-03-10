from siliconcompiler.tools import vivado

def setup(chip):
    '''Performs FPGA synthesis.'''
    tool = vivado.tool
    task = 'syn_fpga'

    vivado.setup_task(chip, task)

    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'step')
    chip.set('tool', tool, 'task', task, 'input', f'{design}.v', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{design}_checkpoint.dcp', step=step, index=index)

def post_process(chip):
    vivado.post_process(chip)
