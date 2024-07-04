from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Generate a bitstream for the ICE40 FPGA
    '''
    tool = 'icepack'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    clobber = False
    design = chip.top()

    chip.set('tool', tool, 'exe', tool)

    chip.set('tool', tool, 'task', task, 'option', "", step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'input', f'{design}.asc', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{design}.bit', step=step, index=index)
