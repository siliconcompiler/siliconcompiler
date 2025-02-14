import graphviz
import os

from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Generate a screenshot of a dot file
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', 1, step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.png', step=step, index=index)


def run(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    if os.path.exists(f'inputs/{chip.top()}.dot'):
        file = f'inputs/{chip.top()}.dot'
    elif os.path.exists(f'inputs/{chip.top()}.xdot'):
        file = f'inputs/{chip.top()}.xdot'
    elif chip.valid('tool', tool, 'task', task, 'var', 'show_filepath') and \
            chip.get('tool', tool, 'task', task, 'var', 'show_filepath', step=step, index=index):
        file = chip.get('tool', tool, 'task', task, 'var', 'show_filepath',
                        step=step, index=index)[0]
    else:
        file = chip.find_files('input', 'image', 'dot', step=step, index=index)[0]

    with sc_open(file) as dot:
        dot_content = dot.read()

    try:
        dot = graphviz.Source(dot_content, format="png")
        dot.render(filename=f"outputs/{chip.top()}", cleanup=True)
        pass
    except graphviz.ExecutableNotFound:
        return 1

    return 0
