import os
import math
from siliconcompiler import NodeStatus
from siliconcompiler.tools._common import input_file_node_name, get_tool_task

from siliconcompiler.flowgraph import RuntimeFlowgraph


###########################################################################
def _check_flowgraph_io(chip, nodes=None):
    '''Check if flowgraph is valid in terms of input and output files.

    Returns True if valid, False otherwise.
    '''
    flow = chip.get('option', 'flow')

    runtime_full = RuntimeFlowgraph(
        chip.schema.get("flowgraph", flow, field='schema'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))
    runtime_flow = RuntimeFlowgraph(
        chip.schema.get("flowgraph", flow, field='schema'),
        args=(chip.get('arg', 'step'), chip.get('arg', 'index')),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))
    record = chip.schema.get("record", field='schema')

    if not nodes:
        nodes = runtime_flow.get_nodes()
    for (step, index) in nodes:
        # For each task, check input requirements.
        tool, task = get_tool_task(chip, step, index, flow=flow)

        if tool == 'builtin':
            # We can skip builtins since they don't have any particular
            # input requirements -- they just pass through what they
            # receive.
            continue

        # Get files we receive from input nodes.
        in_nodes = runtime_full.get_node_inputs(step, index, record=record)
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
                in_tool, _ = get_tool_task(chip, in_step, in_index, flow=flow)
                task_class = chip.get("tool", in_tool, field="schema")
                task_class.set_runtime(chip, step=in_step, index=in_index)

                inputs = task_class.get_output_files()

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


def _get_flowgraph_information(chip, flow, io=True):
    from siliconcompiler.scheduler import _setup_node
    from siliconcompiler.tools._common import input_provides, input_file_node_name

    # Save schema to avoid making permanent changes
    org_schema = chip.schema
    chip.schema = chip.schema.copy()

    # Setup nodes
    node_exec_order = chip.schema.get("flowgraph", flow, field="schema").get_execution_order()
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
        for step, index in chip.schema.get("flowgraph", flow, field="schema").get_nodes():
            tool, task = get_tool_task(chip, step, index, flow=flow)
            for keypath in chip.get('tool', tool, 'task', task, 'require', step=step, index=index):
                key = tuple(keypath.split(','))
                if key[0] == 'input':
                    graph_inputs.setdefault((step, index), set()).add(keypath)

        for inputs in graph_inputs.values():
            all_graph_inputs.update(inputs)

    exit_nodes = [f'{step}{index}' for step, index in chip.schema.get(
        "flowgraph", flow, field="schema").get_exit_nodes()]

    nodes = {}
    edges = []

    def clean_label(label):
        return label.replace("<", "").replace(">", "")

    def clean_text(label):
        return label.replace("<", r"\<").replace(">", r"\>")

    all_nodes = [(step, index) for step, index in sorted(
                    chip.schema.get("flowgraph", flow, field="schema").get_nodes())
                 if chip.get('record', 'status', step=step, index=index) != NodeStatus.SKIPPED]

    runtime_flow = RuntimeFlowgraph(chip.schema.get("flowgraph", flow, field='schema'))
    record = chip.schema.get("record", field='schema')

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
        for in_step, in_index in runtime_flow.get_node_inputs(step, index, record=record):
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
