from siliconcompiler.tools.builtin import _common
import re
from siliconcompiler.tools.builtin.builtin import set_io_files
from siliconcompiler import SiliconCompilerError
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.builtin import BuiltinTask
from siliconcompiler import NodeStatus


class MuxTask(BuiltinTask):
    '''
    Selects a task from a list of inputs.

    The selector criteria provided is used to create a custom function
    for selecting the best step/index pair from the inputs. Metrics and
    weights are passed in and used to select the step/index based on
    the minimum or maximum score depending on the 'op' argument from
    ['flowgraph', flow, step, index, 'args'] in the form 'minimum(metric)' or
    'maximum(metric)'.

    The function can be used to bypass the flows weight functions for
    the purpose of conditional flow execution and verification.
    '''

    def task(self):
        return "mux"

    def __mux(self, nodes, operations):
        nodelist = list(nodes)

        # Keeping track of the steps/indexes that have goals met
        failed = {}
        for step, index in nodelist:
            if step not in failed:
                failed[step] = {}
            failed[step][index] = False

            failed[step][index] = NodeStatus.is_error(
                self.schema("record").get('status', step=step, index=index))

        candidates = [(step, index) for step, index in nodelist if not failed[step][index]]
        if candidates:
            for metric, op in operations:
                print(metric, op)
                if op not in ('minimum', 'maximum'):
                    raise ValueError(f'Invalid operation: {op}')

                values = [self.schema("metric").get(metric, step=step, index=index)
                          for step, index in candidates]

                if op == 'minimum':
                    target = min(values)
                else:
                    target = max(values)

                winners = []
                for value, node in zip(values, candidates):
                    if value == target:
                        winners.append(node)
                candidates = winners

                if len(candidates) == 1:
                    break

        if len(candidates) == 0:
            # Restore step list and pick first step
            candidates = nodelist

        return candidates[0]

    def select_input_nodes(self):
        nodes = super().select_input_nodes()
        arguments = self.schema("flow").get(self.step, self.index, 'args')

        operations = []
        for criteria in arguments:
            m = re.match(r'(minimum|maximum)\((\w+)\)', criteria)
            if not m:
                raise ValueError(f"Illegal mux criteria: {criteria}")

            op = m.group(1)
            metric = m.group(2)
            if metric not in self.schema("metric").getkeys():
                raise ValueError(
                    f"Criteria must use legal metrics only: {criteria}")

            operations.append((metric, op))
        return [self.__mux(nodes, operations)]


def setup(chip):
    '''
    Selects a task from a list of inputs.

    The selector criteria provided is used to create a custom function
    for selecting the best step/index pair from the inputs. Metrics and
    weights are passed in and used to select the step/index based on
    the minimum or maximum score depending on the 'op' argument from
    ['flowgraph', flow, step, index, 'args'] in the form 'minimum(metric)' or
    'maximum(metric)'.

    The function can be used to bypass the flows weight functions for
    the purpose of conditional flow execution and verification.
    '''

    set_io_files(chip)


def _select_inputs(chip, step, index):
    chip.logger.info("Running builtin task 'mux'")

    flow = chip.get('option', 'flow')
    inputs = chip.get('flowgraph', flow, step, index, 'input')
    arguments = chip.get('flowgraph', flow, step, index, 'args')

    operations = []
    for criteria in arguments:
        m = re.match(r'(minimum|maximum)\((\w+)\)', criteria)
        if not m:
            raise SiliconCompilerError(f"Illegal mux criteria: {criteria}", chip=chip)

        op = m.group(1)
        metric = m.group(2)
        if metric not in chip.getkeys('metric'):
            raise SiliconCompilerError(
                f"Criteria must use legal metrics only: {criteria}", chip=chip)

        operations.append((metric, op))
    score, sel_inputs = _common._mux(chip, *inputs, operations=operations)

    if sel_inputs:
        chip.logger.info(f"Selected '{sel_inputs[0]}{sel_inputs[1]}' with score {score:.3f}")

    return sel_inputs


def _gather_outputs(chip, step, index):
    flow = chip.get('option', 'flow')

    in_nodes = chip.get('flowgraph', flow, step, index, 'input')
    in_task_outputs = []
    for in_step, in_index in in_nodes:
        in_tool, in_task = get_tool_task(chip, in_step, in_index, flow=flow)
        task_class = chip.get("tool", in_tool, "task", in_task, field="schema")
        with task_class.runtime(SchedulerNode(chip, in_step, in_index)) as task:
            in_task_outputs.append(task.get_output_files())

    if len(in_task_outputs) > 0:
        return in_task_outputs[0].intersection(*in_task_outputs[1:])

    return []


def run(chip):
    return _common.run(chip)


def post_process(chip):
    _common.post_process(chip)
