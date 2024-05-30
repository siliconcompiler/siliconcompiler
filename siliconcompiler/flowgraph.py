import os
from siliconcompiler import SiliconCompilerError
from siliconcompiler import NodeStatus
from siliconcompiler.schema import Schema


def _check_execution_nodes_inputs(chip, flow):
    for node in chip.nodes_to_execute(flow):
        if node in _get_execution_entry_nodes(chip, flow):
            continue
        pruned_node_inputs = set(_get_pruned_node_inputs(chip, flow, node))
        node_inputs = set(_get_flowgraph_node_inputs(chip, flow, node))
        tool, task = chip._get_tool_task(node[0], node[1], flow=flow)
        if chip._is_builtin(tool, task) and not pruned_node_inputs or \
           not chip._is_builtin(tool, task) and pruned_node_inputs != node_inputs:
            chip.logger.warning(
                f'Flowgraph connection from {node_inputs.difference(pruned_node_inputs)} '
                f'to {node} is missing. '
                f'Double check your flowgraph and from/to/prune options.')
            return False
    return True


def _nodes_to_execute(chip, flow, from_nodes, to_nodes, prune_nodes):
    '''
    Assumes a flowgraph with valid edges for the inputs
    '''
    nodes_to_execute = []
    for from_node in from_nodes:
        for node in _nodes_to_execute_recursive(chip, flow, from_node, to_nodes, prune_nodes):
            if node not in nodes_to_execute:
                nodes_to_execute.append(node)
    return nodes_to_execute


def _nodes_to_execute_recursive(chip, flow, from_node, to_nodes, prune_nodes, path=[]):
    path = path.copy()
    nodes_to_execute = []

    if from_node in prune_nodes:
        return []
    if from_node in path:
        raise SiliconCompilerError(f'Path {path} would form a circle with {from_node}')
    path.append(from_node)

    if from_node in to_nodes:
        for node in path:
            nodes_to_execute.append(node)
    for output_node in _get_flowgraph_node_outputs(chip, flow, from_node):
        for node in _nodes_to_execute_recursive(chip, flow, output_node, to_nodes,
                                                prune_nodes, path=path):
            if node not in nodes_to_execute:
                nodes_to_execute.append(node)

    return nodes_to_execute


def _unreachable_steps_to_execute(chip, flow, cond=lambda _: True):
    from_nodes = set(_get_execution_entry_nodes(chip, flow))
    to_nodes = set(_get_execution_exit_nodes(chip, flow))
    prune_nodes = chip.get('option', 'prune')
    reachable_nodes = set(_reachable_flowgraph_nodes(chip, flow, from_nodes, cond=cond,
                                                     prune_nodes=prune_nodes))
    unreachable_nodes = to_nodes.difference(reachable_nodes)
    unreachable_steps = set()
    for unreachable_node in unreachable_nodes:
        if not any(filter(lambda node: node[0] == unreachable_node[0], reachable_nodes)):
            unreachable_steps.add(unreachable_node[0])
    return unreachable_steps


def _reachable_flowgraph_nodes(chip, flow, from_nodes, cond=lambda _: True, prune_nodes=[]):
    visited_nodes = set()
    current_nodes = from_nodes.copy()
    while current_nodes:
        current_nodes_copy = current_nodes.copy()
        for current_node in current_nodes_copy:
            if current_node in prune_nodes:
                current_nodes.remove(current_node)
                continue
            if cond(current_node):
                visited_nodes.add(current_node)
                current_nodes.remove(current_node)
                outputs = _get_flowgraph_node_outputs(chip, flow, current_node)
                current_nodes.update(outputs)
        if current_nodes == current_nodes_copy:
            break
    return visited_nodes


def _get_flowgraph_node_inputs(chip, flow, node):
    step, index = node
    return chip.get('flowgraph', flow, step, index, 'input')


def _get_pruned_flowgraph_nodes(chip, flow, prune_nodes):
    # Ignore option from/to, we want reachable nodes of the whole flowgraph
    from_nodes = set(_get_flowgraph_entry_nodes(chip, flow))
    return _reachable_flowgraph_nodes(chip, flow, from_nodes, prune_nodes=prune_nodes)


def _get_pruned_node_inputs(chip, flow, node):
    prune_nodes = chip.get('option', 'prune')
    pruned_flowgraph_nodes = _get_pruned_flowgraph_nodes(chip, flow, prune_nodes)
    return list(filter(lambda node: node in pruned_flowgraph_nodes,
                       _get_flowgraph_node_inputs(chip, flow, node)))


def _get_flowgraph_node_outputs(chip, flow, node):
    node_outputs = []

    iter_nodes = _get_flowgraph_nodes(chip, flow)
    for iter_node in iter_nodes:
        iter_node_inputs = _get_flowgraph_node_inputs(chip, flow, iter_node)
        if node in iter_node_inputs:
            node_outputs.append(iter_node)

    return node_outputs


def _get_flowgraph_nodes(chip, flow, steps=None, indices=None):
    nodes = []
    for step in chip.getkeys('flowgraph', flow):
        if steps and step not in steps:
            continue
        for index in chip.getkeys('flowgraph', flow, step):
            if indices and index not in indices:
                continue
            nodes.append((step, index))
    return nodes


def gather_resume_failed_nodes(chip, flow, nodes_to_execute):
    if not chip.get('option', 'resume'):
        return []

    failed_nodes = []
    for step, index in nodes_to_execute:
        stepdir = chip._getworkdir(step=step, index=index)
        cfg = f"{stepdir}/outputs/{chip.get('design')}.pkg.json"

        if not os.path.isdir(stepdir):
            failed_nodes.append((step, index))
        elif os.path.isfile(cfg):
            try:
                node_status = Schema(manifest=cfg).get('flowgraph', flow, step, index, 'status')
                if node_status != NodeStatus.SUCCESS:
                    failed_nodes.append((step, index))
            except:  # noqa E722
                # If failure to load manifest fail
                failed_nodes.append((step, index))
        else:
            failed_nodes.append((step, index))

    nodes_to_keep = set(_get_pruned_flowgraph_nodes(chip, flow, failed_nodes))
    nodes_to_remove = set(nodes_to_execute).difference(nodes_to_keep)

    return nodes_to_remove


#######################################
def _get_execution_entry_nodes(chip, flow):
    if chip.get('arg', 'step') and chip.get('arg', 'index'):
        return [(chip.get('arg', 'step'), chip.get('arg', 'index'))]
    if chip.get('arg', 'step'):
        return _get_flowgraph_nodes(chip, flow, steps=[chip.get('arg', 'step')])
    # If we explicitly get the nodes for a flow other than the current one,
    # Ignore the 'option' 'from'
    if chip.get('option', 'flow') == flow and chip.get('option', 'from'):
        return _get_flowgraph_nodes(chip, flow, steps=chip.get('option', 'from'))
    return _get_flowgraph_entry_nodes(chip, flow)


def _get_flowgraph_entry_nodes(chip, flow, steps=None):
    '''
    Collect all step/indices that represent the entry
    nodes for the flowgraph
    '''
    nodes = []
    for (step, index) in _get_flowgraph_nodes(chip, flow, steps=steps):
        if not _get_flowgraph_node_inputs(chip, flow, (step, index)):
            nodes.append((step, index))
    return nodes


def _get_execution_exit_nodes(chip, flow):
    if chip.get('arg', 'step') and chip.get('arg', 'index'):
        return [(chip.get('arg', 'step'), chip.get('arg', 'index'))]
    if chip.get('arg', 'step'):
        return _get_flowgraph_nodes(chip, flow, steps=[chip.get('arg', 'step')])
    # If we explicitly get the nodes for a flow other than the current one,
    # Ignore the 'option' 'to'
    if chip.get('option', 'flow') == flow and chip.get('option', 'to'):
        return _get_flowgraph_nodes(chip, flow, steps=chip.get('option', 'to'))
    return _get_flowgraph_exit_nodes(chip, flow)


#######################################
def _get_flowgraph_exit_nodes(chip, flow, steps=None):
    '''
    Collect all step/indices that represent the exit
    nodes for the flowgraph
    '''
    inputnodes = []
    for (step, index) in _get_flowgraph_nodes(chip, flow, steps=steps):
        inputnodes.extend(_get_flowgraph_node_inputs(chip, flow, (step, index)))
    nodes = []
    for (step, index) in _get_flowgraph_nodes(chip, flow, steps=steps):
        if (step, index) not in inputnodes:
            nodes.append((step, index))
    return nodes


#######################################
def _get_flowgraph_execution_order(chip, flow, reverse=False):
    '''
    Generates a list of nodes in the order they will be executed.
    '''

    # Generate execution edges lookup map
    ex_map = {}
    for step, index in _get_flowgraph_nodes(chip, flow):
        for istep, iindex in _get_flowgraph_node_inputs(chip, flow, (step, index)):
            if reverse:
                ex_map.setdefault((step, index), set()).add((istep, iindex))
            else:
                ex_map.setdefault((istep, iindex), set()).add((step, index))

    # Collect execution order of nodes
    if reverse:
        order = [set(_get_flowgraph_exit_nodes(chip, flow))]
    else:
        order = [set(_get_flowgraph_entry_nodes(chip, flow))]

    while True:
        next_level = set()
        for step, index in order[-1]:
            if (step, index) in ex_map:
                next_level.update(ex_map.pop((step, index)))

        if not next_level:
            break

        order.append(next_level)

    # Filter duplicates from flow
    used_nodes = set()
    exec_order = []
    order.reverse()
    for n, level_nodes in enumerate(order):
        exec_order.append(list(level_nodes.difference(used_nodes)))
        used_nodes.update(level_nodes)

    exec_order.reverse()

    return exec_order


def get_executed_nodes(chip, flow):
    from_nodes = _get_flowgraph_entry_nodes(chip, flow)
    return get_nodes_from(chip, flow, from_nodes)


def get_nodes_from(chip, flow, nodes):
    to_nodes = _get_execution_exit_nodes(chip, flow)
    return _nodes_to_execute(chip,
                             flow,
                             set(nodes),
                             set(to_nodes),
                             set(chip.get('option', 'prune')))
