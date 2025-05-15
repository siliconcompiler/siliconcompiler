from siliconcompiler.tools._common import input_provides, get_tool_task
from siliconcompiler.tools.xyce import setup as tool_setup
import os


def setup(chip):
    tool_setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    if f'{design}.xyce' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.xyce',
                 step=step, index=index)
    elif f'{design}.cir' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.cir',
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require', 'input,netlist,spice',
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'trace', 'false',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'trace', 'true/false, enable dumping all signals',
             field='help')

    allowed_traced = ['ASCII', 'binary']
    chip.set('tool', tool, 'task', task, 'var', 'trace_format', 'ASCII',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'trace_format', 'Format to use for traces. '
             f'Allowed values are {allowed_traced}',
             field='help')

    if chip.get('tool', tool, 'task', task, 'var', 'trace_format', step=step, index=index)[0] \
            not in allowed_traced:
        raise ValueError(f"{chip.get('tool', tool, 'task', task, 'var', 'trace_format')[0]} "
                         "is not an accepted value")

    if chip.get('tool', tool, 'task', task, 'var', 'trace_format', step=step, index=index) == \
            ['ASCII']:
        chip.add('tool', tool, 'task', task, 'option', '-a',
                 step=step, index=index)

    if chip.get('tool', tool, 'task', task, 'var', 'trace',
                step=step, index=index) == ['true']:
        chip.add('tool', tool, 'task', task, 'output', f'{design}.raw',
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'option', ['-r', f'outputs/{design}.raw'],
                 step=step, index=index)


def runtime_options(chip):
    design = chip.top()
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if f'{design}.xyce' in input_provides(chip, step, index):
        if os.path.isfile(f'inputs/{design}.xyce'):
            return [f'inputs/{design}.xyce']
        elif os.path.isfile(f'inputs/{design}.xyce/{design}.cir'):
            return [f'inputs/{design}.xyce/{design}.cir']
        else:
            return [f'inputs/{design}.xyce']
    elif f'{design}.cir' in input_provides(chip, step, index):
        return [f'inputs/{design}.cir']

    return chip.find_files('input', 'netlist', 'spice', step=step, index=index)
