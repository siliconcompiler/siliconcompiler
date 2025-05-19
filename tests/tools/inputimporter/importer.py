import os

from tools.inputimporter import setup as tool_setup
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    '''
    Import (copy) files into the output folder.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    tool_setup(chip)

    # Get the paths to all of the input files.
    input_files = chip.get('tool', tool, 'task', task, 'var', 'input_files', step=step, index=index)
    if not input_files:
        return "no input files provided to copy"

    # For each input file, require that they appear in the output folder.
    for input_file in input_files:
        input_basename = os.path.basename(input_file)
        chip.add('tool', tool, 'task', task, 'output', input_basename, step=step, index=index)


def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # All files will be copied into the output directory.
    cmds = ['-t', 'outputs/']

    # Add all source files to be copied.
    input_files = chip.get('tool', tool, 'task', task, 'var', 'input_files', step=step, index=index)
    for input_file in input_files:
        cmds.append(input_file)

    return cmds
