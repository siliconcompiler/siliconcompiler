from siliconcompiler.tools._common import input_provides, input_file_node_name, get_tool_task

from siliconcompiler.tools.klayout.klayout import setup as setup_tool
from siliconcompiler.tools.klayout.klayout import runtime_options as tool_runtime_options


def make_docs(chip):
    from siliconcompiler.tools.klayout import klayout
    klayout.make_docs(chip)


def setup(chip):
    '''
    Convert a DRC db from .lyrdb or .ascii to an openroad json marker file
    '''

    # Generic tool setup.
    setup_tool(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    design = chip.top()

    clobber = False

    chip.set('tool', tool, 'task', task, 'threads', 1,
             step=step, index=index, clobber=clobber)

    script = 'klayout_convert_drc_db.py'
    option = ['-z', '-nc', '-rx', '-r']
    chip.set('tool', tool, 'task', task, 'script', script,
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', option,
             step=step, index=index, clobber=clobber)

    input_nodes = set()
    for nodes in input_provides(chip, step, index).values():
        input_nodes.update(nodes)

    chip.set('tool', tool, 'task', task, 'input', [], step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', [], step=step, index=index)
    for file, nodes in input_provides(chip, step, index).items():
        if file not in (f'{design}.lyrdb', f'{design}.ascii'):
            continue

        if len(input_nodes) == 1:
            chip.add('tool', tool, 'task', task, 'input',
                     file,
                     step=step, index=index)
        else:
            for in_step, in_index in nodes:
                chip.add('tool', tool, 'task', task, 'input',
                         input_file_node_name(file, in_step, in_index),
                         step=step, index=index)
    if not chip.get('tool', tool, 'task', task, 'input', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'input', f'{design}.lyrdb',
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', f'{design}.json',
             step=step, index=index)


def runtime_options(chip):
    return tool_runtime_options(chip)
