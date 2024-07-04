from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Perform automated place and route on FPGAs
    '''

    tool = 'nextpnr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    topmodule = chip.top()

    clobber = False
    chip.set('tool', tool, 'exe', 'nextpnr-ice40')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.2', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'option', "", step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'input', f'{topmodule}.netlist.json',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{topmodule}.asc', step=step, index=index)
