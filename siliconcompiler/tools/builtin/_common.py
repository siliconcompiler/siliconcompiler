
from siliconcompiler import NodeStatus, SiliconCompilerError
from siliconcompiler import utils
import shutil
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.flowgraph import _get_pruned_node_inputs


###########################################################################
def _mux(chip, *nodes, operations=None):
    '''
    Shared function used for min and max calculation.
    '''

    nodelist = list(nodes)

    # Keeping track of the steps/indexes that have goals met
    failed = {}
    for step, index in nodelist:
        if step not in failed:
            failed[step] = {}
        failed[step][index] = False

        if chip.get('record', 'status', step=step, index=index) == NodeStatus.ERROR:
            failed[step][index] = True
        else:
            failed[step][index] = False

    candidates = [(step, index) for step, index in nodelist if not failed[step][index]]
    best_score = 0
    for metric, op in operations:
        if op not in ('minimum', 'maximum'):
            raise ValueError('Invalid op')

        values = [chip.get('metric', metric, step=step, index=index) for step, index in candidates]

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

    return (best_score, candidates[0])


###########################################################################
def _minmax(chip, *nodes, op=None):
    '''
    Shared function used for min and max calculation.
    '''

    if op not in ('minimum', 'maximum'):
        raise ValueError('Invalid op')

    flow = chip.get('option', 'flow')
    nodelist = list(nodes)

    # Keeping track of the steps/indexes that have goals met
    failed = {}
    for step, index in nodelist:
        if step not in failed:
            failed[step] = {}
        failed[step][index] = False

        if chip.get('record', 'status', step=step, index=index) == NodeStatus.ERROR:
            failed[step][index] = True
        else:
            for metric in chip.getkeys('metric'):
                if chip.valid('flowgraph', flow, step, index, 'goal', metric):
                    goal = chip.get('flowgraph', flow, step, index, 'goal', metric)
                    real = chip.get('metric', metric, step=step, index=index)
                    if real is None:
                        raise SiliconCompilerError(
                            f'Metric {metric} has goal for {step}{index} '
                            'but it has not been set.', chip=chip)
                    if abs(real) > goal:
                        chip.logger.warning(f"Step {step}{index} failed "
                                            f"because it didn't meet goals for '{metric}' "
                                            "metric.")
                        failed[step][index] = True

    # Calculate max/min values for each metric
    max_val = {}
    min_val = {}
    for metric in chip.getkeys('metric'):
        max_val[metric] = 0
        min_val[metric] = float("inf")
        for step, index in nodelist:
            if not failed[step][index]:
                real = chip.get('metric', metric, step=step, index=index)
                if real is None:
                    continue
                max_val[metric] = max(max_val[metric], real)
                min_val[metric] = min(min_val[metric], real)

    # Select the minimum index
    best_score = float('inf') if op == 'minimum' else float('-inf')
    winner = None
    for step, index in nodelist:
        if failed[step][index]:
            continue

        score = 0.0
        for metric in chip.getkeys('flowgraph', flow, step, index, 'weight'):
            weight = chip.get('flowgraph', flow, step, index, 'weight', metric)
            if not weight:
                # skip if weight is 0 or None
                continue

            real = chip.get('metric', metric, step=step, index=index)
            if real is None:
                raise SiliconCompilerError(
                    f'Metric {metric} has weight for {step}{index} '
                    'but it has not been set.', chip=chip)

            if not (max_val[metric] - min_val[metric]) == 0:
                scaled = (real - min_val[metric]) / (max_val[metric] - min_val[metric])
            else:
                scaled = max_val[metric]
            score = score + scaled * weight

        if ((op == 'minimum' and score < best_score) or (op == 'maximum' and score > best_score)):
            best_score = score
            winner = (step, index)

    return (best_score, winner)


def run(chip):
    return 0


def post_process(chip):
    shutil.copytree('inputs', 'outputs', dirs_exist_ok=True, copy_function=utils.link_symlink_copy)


def _select_inputs(chip, step, index):
    _, task = get_tool_task(chip, step, index)

    chip.logger.info(f"Running builtin task '{task}'")

    flow = chip.get('option', 'flow')
    return _get_pruned_node_inputs(chip, flow, (step, index))
