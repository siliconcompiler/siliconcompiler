from siliconcompiler.tools.builtin import _common
import os
from siliconcompiler import sc_open, SiliconCompilerError
from siliconcompiler import utils
from siliconcompiler.tools._common import input_provides, input_file_node_name, get_tool_task
from siliconcompiler import scheduler


def make_docs(chip):
    from siliconcompiler.flows._common import _make_docs
    _make_docs(chip)
    chip.set('option', 'flow', 'asicflow')

    for step, index in chip.schema.get("flowgraph", "asicflow", field="schema").get_entry_nodes():
        scheduler._setup_node(chip, step, index)

    chip.set('arg', 'step', 'import.combine')
    chip.set('arg', 'index', '0')
    setup(chip)

    return chip


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
    in_task_outputs = []
    for in_step, in_index in in_nodes:
        in_tool, _ = get_tool_task(chip, in_step, in_index, flow=flow)
        task_class = chip.get("tool", in_tool, field="schema")
        task_class.set_runtime(chip, step=in_step, index=in_index)
        in_task_outputs.append(task_class.get_output_files())

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
