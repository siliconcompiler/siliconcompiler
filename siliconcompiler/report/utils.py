from siliconcompiler import NodeStatus
from siliconcompiler import units


def _find_summary_image(chip, ext='png'):
    for step, index in chip._get_flowgraph_exit_nodes(chip.get('option', 'flow')):
        layout_img = chip.find_result(ext, step=step, index=index)
        if layout_img:
            return layout_img
    return None


def _collect_data(chip, flow=None, flowgraph_nodes=None, format_as_string=True):
    if not flow:
        flow = chip.get('option', 'flow')
    if not flowgraph_nodes:
        flowgraph_nodes = chip.nodes_to_execute()
        # only report tool based steps functions
        for (step, index) in flowgraph_nodes.copy():
            tool, task = chip._get_tool_task(step, '0', flow=flow)
            if chip._is_builtin(tool, task):
                index = flowgraph_nodes.index((step, index))
                del flowgraph_nodes[index]

    # Collections for data
    nodes = []
    errors = {}
    metrics = {}
    metrics_unit = {}
    reports = {}

    # Build ordered list of nodes in flowgraph
    for (step, index) in flowgraph_nodes:
        nodes.append((step, index))
        metrics[step, index] = {}
        reports[step, index] = {}

    # Gather data and determine which metrics to show
    # We show a metric if:
    # - it is not in ['option', 'metricoff'] -AND-
    # - at least one step in the steps has a non-zero weight for the metric -OR -
    #   at least one step in the steps set a value for it
    metrics_to_show = []
    for metric in chip.getkeys('metric'):
        if metric in chip.get('option', 'metricoff'):
            continue

        # Get the unit associated with the metric
        metric_unit = None
        if chip.schema._has_field('metric', metric, 'unit'):
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
            tool, task = chip._get_tool_task(step, index, flow=flow)
            rpts = chip.get('tool', tool, 'task', task, 'report', metric,
                            step=step, index=index)

            errors[step, index] = chip.get('flowgraph', flow,
                                           step, index, 'status') == \
                NodeStatus.ERROR

            if value is not None:
                value = _format_value(metric, value, metric_unit, metric_type, format_as_string)

            metrics[step, index][metric] = value
            reports[step, index][metric] = rpts

        if show_metric:
            metrics_to_show.append(metric)
            metrics_unit[metric] = metric_unit if metric_unit else ''

    return nodes, errors, metrics, metrics_unit, metrics_to_show, reports


def _format_value(metric, value, metric_unit, metric_type, format_as_string):
    if metric == 'memory':
        if format_as_string:
            return units.format_binary(value, metric_unit)
        value, metric = units.scale_binary(value, metric_unit)
    elif metric in ['exetime', 'tasktime']:
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
    end_nodes = chip._get_flowgraph_exit_nodes(flow, steps=flowgraph_steps)
    for node in end_nodes:
        if only_include_successful:
            if chip.get('flowgraph', flow, *node, 'status') == \
               NodeStatus.SUCCESS:
                selected_nodes.add(node)
                to_search.append(node)
        else:
            selected_nodes.add(node)
            to_search.append(node)
    # Search backwards, saving anything that was selected by leaf nodes.
    while len(to_search) > 0:
        node = to_search.pop(-1)
        input_nodes = chip.get('flowgraph', flow, *node, 'select')
        for selected in input_nodes:
            if selected not in selected_nodes:
                selected_nodes.add(selected)
                to_search.append(selected)
    return selected_nodes
