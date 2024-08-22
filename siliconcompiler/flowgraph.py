import os
import math
from siliconcompiler import SiliconCompilerError, NodeStatus
from siliconcompiler.tools._common import input_file_node_name, get_tool_task


def _check_execution_nodes_inputs(chip, flow):
    for node in nodes_to_execute(chip, flow):
        if node in _get_execution_entry_nodes(chip, flow):
            continue
        pruned_node_inputs = set(_get_pruned_node_inputs(chip, flow, node))
        node_inputs = set(_get_flowgraph_node_inputs(chip, flow, node))
        tool, task = get_tool_task(chip, node[0], node[1], flow=flow)
        if tool == 'builtin' and not pruned_node_inputs or \
           tool != 'builtin' and pruned_node_inputs != node_inputs:
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
    inputs = set()
    for in_node in chip.get('flowgraph', flow, step, index, 'input'):
        if chip.get('record', 'status', step=in_node[0], index=in_node[1]) == \
                NodeStatus.SKIPPED:
            inputs.update(_get_flowgraph_node_inputs(chip, flow, in_node))
        else:
            inputs.add(in_node)
    return list(inputs)


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
        iter_node_inputs = chip.get('flowgraph', flow, *iter_node, 'input')
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
        if not chip.get('flowgraph', flow, step, index, 'input'):
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
        inputnodes.extend(chip.get('flowgraph', flow, step, index, 'input'))
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
        for istep, iindex in chip.get('flowgraph', flow, step, index, 'input'):
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
            if (step, index) in ex_map and \
               not any([(step, index) in v for v in ex_map.values()]):
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


###########################################################################
def nodes_to_execute(chip, flow=None):
    '''
    Returns an ordered list of flowgraph nodes which will be executed.
    This takes the from/to options into account if flow is the current flow or None.

    Returns:
        A list of nodes that will get executed during run() (or a specific flow).

    Example:
        >>> nodes = nodes_to_execute()
    '''
    if flow is None:
        flow = chip.get('option', 'flow')

    from_nodes = _get_execution_entry_nodes(chip, flow)
    to_nodes = _get_execution_exit_nodes(chip, flow)
    prune_nodes = chip.get('option', 'prune')
    if from_nodes == to_nodes:
        return list(filter(lambda node: node not in prune_nodes, from_nodes))
    return _nodes_to_execute(chip, flow, set(from_nodes), set(to_nodes), set(prune_nodes))


###########################################################################
def _check_flowgraph(chip, flow=None):
    '''
    Check if flowgraph is valid.

    * Checks if all edges have valid nodes
    * Checks that there are no duplicate edges
    * Checks if from/to is valid

    Returns True if valid, False otherwise.
    '''

    if not flow:
        flow = chip.get('option', 'flow')

    error = False

    nodes = set()
    for (step, index) in _get_flowgraph_nodes(chip, flow):
        nodes.add((step, index))
        input_nodes = chip.get('flowgraph', flow, step, index, 'input')
        nodes.update(input_nodes)

        for node in set(input_nodes):
            if input_nodes.count(node) > 1:
                in_step, in_index = node
                chip.logger.error(f'Duplicate edge from {in_step}{in_index} to '
                                  f'{step}{index} in the {flow} flowgraph')
                error = True

    for step, index in nodes:
        # For each task, check input requirements.
        tool, task = get_tool_task(chip, step, index, flow=flow)

        if not tool:
            chip.logger.error(f'{step}{index} is missing a tool definition in the {flow} '
                              'flowgraph')
            error = True

        if not task:
            chip.logger.error(f'{step}{index} is missing a task definition in the {flow} '
                              'flowgraph')
            error = True

    for step in chip.get('option', 'from'):
        if step not in chip.getkeys('flowgraph', flow):
            chip.logger.error(f'{step} is not defined in the {flow} flowgraph')
            error = True

    for step in chip.get('option', 'to'):
        if step not in chip.getkeys('flowgraph', flow):
            chip.logger.error(f'{step} is not defined in the {flow} flowgraph')
            error = True

    if not _check_execution_nodes_inputs(chip, flow):
        error = True

    unreachable_steps = _unreachable_steps_to_execute(chip, flow)
    if unreachable_steps:
        chip.logger.error(f'These final steps in {flow} can not be reached: '
                          f'{list(unreachable_steps)}')
        error = True

    return not error


###########################################################################
def _check_flowgraph_io(chip, nodes=None):
    '''Check if flowgraph is valid in terms of input and output files.

    Returns True if valid, False otherwise.
    '''
    flow = chip.get('option', 'flow')
    if not nodes:
        nodes = nodes_to_execute(chip)
    for (step, index) in nodes:
        # For each task, check input requirements.
        tool, task = get_tool_task(chip, step, index, flow=flow)

        if tool == 'builtin':
            # We can skip builtins since they don't have any particular
            # input requirements -- they just pass through what they
            # receive.
            continue

        # Get files we receive from input nodes.
        in_nodes = _get_flowgraph_node_inputs(chip, flow, (step, index))
        all_inputs = set()
        requirements = chip.get('tool', tool, 'task', task, 'input', step=step, index=index)
        for in_step, in_index in in_nodes:
            if (in_step, in_index) not in nodes:
                # If we're not running the input step, the required
                # inputs need to already be copied into the build
                # directory.
                workdir = chip.getworkdir(step=in_step, index=in_index)
                in_step_out_dir = os.path.join(workdir, 'outputs')

                if not os.path.isdir(in_step_out_dir):
                    # This means this step hasn't been run, but that
                    # will be flagged by a different check. No error
                    # message here since it would be redundant.
                    inputs = []
                    continue

                design = chip.get('design')
                manifest = f'{design}.pkg.json'
                inputs = [inp for inp in os.listdir(in_step_out_dir) if inp != manifest]
            else:
                inputs = _gather_outputs(chip, in_step, in_index)

            for inp in inputs:
                node_inp = input_file_node_name(inp, in_step, in_index)
                if node_inp in requirements:
                    inp = node_inp
                if inp in all_inputs:
                    chip.logger.error(f'Invalid flow: {step}{index} '
                                      f'receives {inp} from multiple input tasks')
                    return False
                all_inputs.add(inp)

        for requirement in requirements:
            if requirement not in all_inputs:
                chip.logger.error(f'Invalid flow: {step}{index} will '
                                  f'not receive required input {requirement}.')
                return False

    return True


###########################################################################
def _gather_outputs(chip, step, index):
    '''Return set of filenames that are guaranteed to be in outputs
    directory after a successful run of step/index.'''

    flow = chip.get('option', 'flow')
    task_gather = getattr(chip._get_task_module(step, index, flow=flow, error=False),
                          '_gather_outputs',
                          None)
    if task_gather:
        return set(task_gather(chip, step, index))

    tool, task = get_tool_task(chip, step, index, flow=flow)
    return set(chip.get('tool', tool, 'task', task, 'output', step=step, index=index))


def _get_flowgraph_information(chip, flow, io=True):
    from siliconcompiler.scheduler import _setup_node
    from siliconcompiler.tools._common import input_provides, input_file_node_name

    # Save schema to avoid making permanent changes
    org_schema = chip.schema
    chip.schema = chip.schema.copy()

    # Setup nodes
    node_exec_order = _get_flowgraph_execution_order(chip, flow)
    if io:
        # try:
        for layer_nodes in node_exec_order:
            for step, index in layer_nodes:
                _setup_node(chip, step, index, flow=flow)
        # except:  # noqa E722
        #     io = False

    node_rank = {}
    for rank, rank_nodes in enumerate(node_exec_order):
        for step, index in rank_nodes:
            node_rank[f'{step}{index}'] = rank

    graph_inputs = {}
    all_graph_inputs = set()
    if io:
        for step, index in _get_flowgraph_nodes(chip, flow):
            tool, task = get_tool_task(chip, step, index, flow=flow)
            for keypath in chip.get('tool', tool, 'task', task, 'require', step=step, index=index):
                key = tuple(keypath.split(','))
                if key[0] == 'input':
                    graph_inputs.setdefault((step, index), set()).add(keypath)

        for inputs in graph_inputs.values():
            all_graph_inputs.update(inputs)

    exit_nodes = [f'{step}{index}' for step, index in _get_flowgraph_exit_nodes(chip, flow)]

    nodes = {}
    edges = []

    def clean_label(label):
        return label.replace("<", "").replace(">", "")

    def clean_text(label):
        return label.replace("<", r"\<").replace(">", r"\>")

    all_nodes = [(step, index) for step, index in sorted(_get_flowgraph_nodes(chip, flow))
                 if chip.get('record', 'status', step=step, index=index) != NodeStatus.SKIPPED]
    for step, index in all_nodes:
        tool, task = get_tool_task(chip, step, index, flow=flow)

        if io:
            inputs = chip.get('tool', tool, 'task', task, 'input', step=step, index=index)
            outputs = chip.get('tool', tool, 'task', task, 'output', step=step, index=index)
            if chip.get('record', 'status', step=step, index=index) == NodeStatus.SKIPPED:
                continue
        else:
            inputs = []
            outputs = []

        node = f'{step}{index}'
        if io and (step, index) in graph_inputs:
            inputs.extend(graph_inputs[(step, index)])

        nodes[node] = {
            "node": (step, index),
            "file_inputs": inputs,
            "inputs": {clean_text(f): f'input-{clean_label(f)}' for f in sorted(inputs)},
            "outputs": {clean_text(f): f'output-{clean_label(f)}' for f in sorted(outputs)},
            "task": f'{tool}/{task}' if tool != 'builtin' else task,
            "is_input": node_rank[node] == 0,
            "rank": node_rank[node]
        }
        nodes[node]["width"] = max(len(nodes[node]["inputs"]), len(nodes[node]["outputs"]))

        if tool is None or task is None:
            nodes[node]["task"] = None

        rank_diff = {}
        for in_step, in_index in _get_flowgraph_node_inputs(chip, flow, (step, index)):
            rank_diff[f'{in_step}{in_index}'] = node_rank[node] - node_rank[f'{in_step}{in_index}']
        nodes[node]["rank_diff"] = rank_diff

    for step, index in all_nodes:
        node = f'{step}{index}'
        if io:
            # get inputs
            edge_stats = {}
            for infile, in_nodes in input_provides(chip, step, index, flow=flow).items():
                outfile = infile
                for in_step, in_index in in_nodes:
                    infile = outfile
                    if infile not in nodes[node]["file_inputs"]:
                        infile = input_file_node_name(infile, in_step, in_index)
                        if infile not in nodes[node]["file_inputs"]:
                            continue
                    in_node_name = f"{in_step}{in_index}"
                    outlabel = f"{in_node_name}:output-{clean_label(outfile)}"
                    inlabel = f"{step}{index}:input-{clean_label(infile)}"

                    if in_node_name not in edge_stats:
                        edge_stats[in_node_name] = {
                            "count": 0,
                            "pairs": [],
                            "weight": min(nodes[node]["width"], nodes[in_node_name]["width"])
                        }
                    edge_stats[in_node_name]["count"] += 1
                    edge_stats[in_node_name]["pairs"].append((outlabel, inlabel))

            # assign edge weights

            # scale multiple weights
            for edge_data in edge_stats.values():
                edge_data["weight"] = int(
                    math.floor(max(1, edge_data["weight"] / edge_data["count"])))

            # lower exit nodes weights
            if node in exit_nodes:
                for edge_data in edge_stats.values():
                    edge_data["weight"] = 1
            else:
                for edge_data in edge_stats.values():
                    edge_data["weight"] *= 2

            # adjust for rank differences, lower weight if rankdiff is greater than 1
            for in_node, edge_data in edge_stats.items():
                if nodes[node]["rank_diff"][in_node] > 1:
                    edge_data["weight"] = 1

            # create edges
            for edge_data in edge_stats.values():
                for outlabel, inlabel in edge_data["pairs"]:
                    edges.append([outlabel, inlabel, edge_data["weight"]])

            if (step, index) in graph_inputs:
                for key in graph_inputs[(step, index)]:
                    inlabel = f"{step}{index}:input-{clean_label(key)}"
                    edges.append((key, inlabel, 1))
        else:
            all_inputs = []
            for in_step, in_index in chip.get('flowgraph', flow, step, index, 'input'):
                all_inputs.append(f'{in_step}{in_index}')
            for item in all_inputs:
                edges.append((item, node, 1 if node in exit_nodes else 2))

    # Restore schema
    chip.schema = org_schema

    return all_graph_inputs, nodes, edges, io
