from siliconcompiler import NodeStatus
from siliconcompiler.utils import units
from siliconcompiler.tools._common import get_tool_task

from siliconcompiler.flowgraph import RuntimeFlowgraph


def _find_summary_image(chip, ext='png'):
    for nodes in reversed(chip.schema.get(
            "flowgraph", chip.get('option', 'flow'), field="schema").get_execution_order()):
        for step, index in nodes:
            layout_img = chip.find_result(ext, step=step, index=index)
            if layout_img:
                return layout_img
    return None


def _find_summary_metrics(chip, metrics_map):
    metrics = {}
    for nodes in reversed(chip.schema.get(
            "flowgraph", chip.get('option', 'flow'), field="schema").get_execution_order()):
        for step, index in nodes:
            for name, metric_info in metrics_map.items():
                if name in metrics:
                    continue

                metric, formatter = metric_info

                data = chip.get('metric', metric, step=step, index=index)
                if data is not None:
                    unit = chip.get('metric', metric, field='unit')
                    if formatter:
                        metrics[name] = formatter(data, unit)
                    else:
                        metrics[name] = str(data)

    return metrics


def _collect_data(chip, flow=None, flowgraph_nodes=None, format_as_string=True):
    if not flow:
        flow = chip.get('option', 'flow')
    if not flow:
        return [], {}, {}, {}, [], {}

    if not flowgraph_nodes:
        runtime = RuntimeFlowgraph(
            chip.schema.get("flowgraph", flow, field='schema'),
            from_steps=chip.get('option', 'from'),
            to_steps=chip.get('option', 'to'),
            prune_nodes=chip.get('option', 'prune'))

        flowgraph_nodes = list(runtime.get_nodes())
        # only report tool based steps functions
        for (step, index) in list(flowgraph_nodes):
            tool, task = get_tool_task(chip, step, '0', flow=flow)
            if tool == 'builtin':
                index = flowgraph_nodes.index((step, index))
                del flowgraph_nodes[index]
    flowgraph_nodes = [
        node for node in flowgraph_nodes
        if chip.get('record', 'status', step=node[0], index=node[1]) != NodeStatus.SKIPPED
    ]

    # Collections for data
    nodes = []
    errors = {}
    metrics = {}
    metrics_unit = {}
    reports = {}

    # Build ordered list of nodes in flowgraph
    for level_nodes in chip.schema.get("flowgraph", flow, field="schema").get_execution_order():
        nodes.extend(sorted(level_nodes))
    nodes = [node for node in nodes if node in flowgraph_nodes]
    for (step, index) in nodes:
        metrics[step, index] = {}
        reports[step, index] = {}

    # Gather data and determine which metrics to show
    # We show a metric if:
    # - at least one step in the steps has a non-zero weight for the metric -OR -
    #   at least one step in the steps set a value for it
    metrics_to_show = []
    for metric in chip.getkeys('metric'):

        # Get the unit associated with the metric
        metric_unit = chip.get('metric', metric, field='unit')
        metric_type = chip.get('metric', metric, field='type')

        show_metric = False
        for step, index in nodes:
            if metric in chip.getkeys('flowgraph', flow,
                                      step, index, 'weight') and \
               chip.get('flowgraph', flow, step, index, 'weight', metric):
                show_metric = True

            value = chip.get('metric', metric, step=step, index=index)
            if value is not None:
                show_metric = True
            tool, task = get_tool_task(chip, step, index, flow=flow)
            rpts = chip.get('tool', tool, 'task', task, 'report', metric,
                            step=step, index=index)

            errors[step, index] = chip.get('record', 'status', step=step, index=index) == \
                NodeStatus.ERROR

            if value is not None:
                value = _format_value(metric, value, metric_unit, metric_type, format_as_string)

            metrics[step, index][metric] = value
            reports[step, index][metric] = rpts

        if show_metric:
            metrics_to_show.append(metric)
            metrics_unit[metric] = metric_unit if metric_unit else ''

    if 'totaltime' in metrics_to_show:
        if not any([chip.get('metric', 'totaltime', step=node[0], index=node[1]) is None
                    for node in nodes]):
            nodes.sort(
                key=lambda node: chip.get('metric', 'totaltime', step=node[0], index=node[1]))

    return nodes, errors, metrics, metrics_unit, metrics_to_show, reports


def _format_value(metric, value, metric_unit, metric_type, format_as_string):
    if metric == 'memory':
        if format_as_string:
            return units.format_binary(value, metric_unit)
        value, metric = units.scale_binary(value, metric_unit)
    elif metric in ['exetime', 'tasktime', 'totaltime']:
        if format_as_string:
            return units.format_time(value)
    elif metric_type == 'int':
        if format_as_string:
            return str(value)
    else:
        if format_as_string:
            return units.format_si(value, metric_unit)
        value, metric = units.scale_si(value, metric_unit)
    return value


def _get_flowgraph_path(chip, flow, nodes_to_execute, only_include_successful=False):
    selected_nodes = set()
    to_search = []
    # Start search with any successful leaf nodes.
    flowgraph_steps = list(map(lambda node: node[0], nodes_to_execute))
    runtime = RuntimeFlowgraph(chip.schema.get("flowgraph", flow, field='schema'),
                               from_steps=flowgraph_steps,
                               to_steps=flowgraph_steps)
    end_nodes = runtime.get_exit_nodes()
    for node in end_nodes:
        if only_include_successful:
            if NodeStatus.is_success(chip.get('record', 'status', step=node[0], index=node[1])):
                selected_nodes.add(node)
                to_search.append(node)
        else:
            selected_nodes.add(node)
            to_search.append(node)
    # Search backwards, saving anything that was selected by leaf nodes.
    while len(to_search) > 0:
        node = to_search.pop(-1)
        input_nodes = chip.get('record', 'inputnode', step=node[0], index=node[1])
        for selected in input_nodes:
            if selected not in selected_nodes:
                selected_nodes.add(selected)
                to_search.append(selected)

    return [node for node in selected_nodes
            if chip.get('record', 'status', step=node[0], index=node[1]) != NodeStatus.SKIPPED]
