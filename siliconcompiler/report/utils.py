from siliconcompiler import TaskStatus
from siliconcompiler import units


def _find_summary_image(chip, ext='png'):
    for step, index in chip._get_flowgraph_exit_nodes():
        layout_img = chip.find_result(ext, step=step, index=index)
        if layout_img:
            return layout_img
    return None


def _collect_data(chip, flow, steplist):
    # Collections for data
    nodes = []
    errors = {}
    metrics = {}
    metrics_unit = {}
    reports = {}

    # Build ordered list of nodes in flowgraph
    for step in steplist:
        for index in chip.getkeys('flowgraph', flow, step):
            nodes.append((step, index))
            metrics[step, index] = {}
            reports[step, index] = {}

    # Gather data and determine which metrics to show
    # We show a metric if:
    # - it is not in ['option', 'metricoff'] -AND-
    # - at least one step in the steplist has a non-zero weight for the metric -OR -
    #   at least one step in the steplist set a value for it
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
                TaskStatus.ERROR

            if value is not None:
                if metric == 'memory':
                    value = units.format_binary(value, metric_unit)
                elif metric in ['exetime', 'tasktime']:
                    metric_unit = None
                    value = units.format_time(value)
                elif metric_type == 'int':
                    value = str(value)
                else:
                    value = units.format_si(value, metric_unit)

            metrics[step, index][metric] = value
            reports[step, index][metric] = rpts

        if show_metric:
            metrics_to_show.append(metric)
            metrics_unit[metric] = metric_unit if metric_unit else ''

    return nodes, errors, metrics, metrics_unit, metrics_to_show, reports


def _get_flowgraph_path(chip, flow, steplist, only_include_successful=False):
    selected_nodes = set()
    to_search = []
    # Start search with any successful leaf nodes.
    end_nodes = chip._get_flowgraph_exit_nodes(flow=flow, steplist=steplist)
    for node in end_nodes:
        if only_include_successful:
            if chip.get('flowgraph', flow, *node, 'status') == \
               TaskStatus.SUCCESS:
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
