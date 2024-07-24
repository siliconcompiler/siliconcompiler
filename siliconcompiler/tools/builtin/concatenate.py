from siliconcompiler.tools.builtin import _common
import os
from siliconcompiler import sc_open, SiliconCompilerError
from siliconcompiler import utils
from siliconcompiler.tools._common import input_provides, input_file_node_name, get_tool_task
from siliconcompiler import flowgraph


def setup(chip):
    '''
    A file concatenation pass that merges input files into a single set of outputs.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    input_nodes = set()
    for nodes in input_provides(chip, step, index).values():
        input_nodes.update(nodes)

    if not input_nodes:
        raise SiliconCompilerError("Concatenate will not receive anything")
    if len(input_nodes) == 1:
        # nothing to concate to so remove
        return "no need to concatenate file"

    chip.set('tool', tool, 'task', task, 'input', [], step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', [], step=step, index=index)
    for file, nodes in input_provides(chip, step, index).items():
        chip.add('tool', tool, 'task', task, 'output', file,
                 step=step, index=index)
        for in_step, in_index in nodes:
            chip.add('tool', tool, 'task', task, 'input',
                     input_file_node_name(file, in_step, in_index),
                     step=step, index=index)


def _select_inputs(chip, step, index):
    return _common._select_inputs(chip, step, index)


def _gather_outputs(chip, step, index):
    '''Return set of filenames that are guaranteed to be in outputs
    directory after a successful run of step/index.'''

    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = [flowgraph._gather_outputs(chip, *node) for node in in_nodes]

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].union(*in_task_outputs[1:])

    return []


def run(chip):
    return _common.run(chip)


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    def comment_flag(ext):
        if ext.startswith('tcl'):
            return '#'
        if ext.startswith('v'):
            return '//'
        return None

    for file, nodes in input_provides(chip, step, index).items():
        comment = comment_flag(utils.get_file_ext(file))
        with open(f'outputs/{file}', 'w') as out:
            for in_step, in_index in nodes:
                ifile = f'inputs/{input_file_node_name(file, in_step, in_index)}'
                if not os.path.isfile(ifile):
                    continue
                with sc_open(ifile) as in_file:
                    if comment:
                        out.write(f'{comment} Start of SiliconCompiler input: {ifile}\n')
                    out.write(in_file.read())
                    if comment:
                        out.write(f'{comment} End of SiliconCompiler input: {ifile}\n\n')
