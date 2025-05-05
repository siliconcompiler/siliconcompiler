import altair
import math
import streamlit

from siliconcompiler.report import report

from siliconcompiler.report.dashboard.web import state


def _get_report_chips():
    chips = []
    for job in state.get_chips():
        chips.append({'chip_object': state.get_chip(job), 'chip_name': job})
    return chips


def job_selector():
    """
    Displays a dataframe that can be edited to select specific jobs to include
    in the analysis.
    """
    from pandas import DataFrame

    jobs = state.get_chips()

    all_jobs = DataFrame({
        'job names': jobs,
        'selected jobs': [True] * len(jobs)
    })

    configuration = {
        'selected jobs': streamlit.column_config.CheckboxColumn(
            'Select runs',
            default=True)
    }

    with streamlit.popover('Select Jobs', use_container_width=True):
        selected_jobs = streamlit.data_editor(
            all_jobs,
            disabled=['job names'],
            use_container_width=True,
            hide_index=True,
            column_config=configuration)

        jobs = []
        for is_selected, job_name in zip(selected_jobs['selected jobs'].tolist(),
                                         selected_jobs['job names'].tolist()):
            if is_selected:
                jobs.append(job_name)

        state.set_key(state.GRAPH_JOBS, jobs)


def graph_count_selector():
    return streamlit.slider(
        'pick the number of graphs you want',
        1,
        10,
        1,
        label_visibility='collapsed')


def settings(metrics, nodes, graph_number):
    """
    Displays selectbox for metrics and nodes which informs the graph on what
    to display.

    Args:
        metrics (list) : A list of metrics that are set for all chips given in chips.
        nodes (list) : A list of nodes given in the form f'{step}{index}'
        graph_number (int) : The number of graphs there are. Used to create
            keys to distinguish selectboxes from each other.
    """
    metric_selector_col, node_selector_col, settings_col = \
        streamlit.columns(3, gap='small')

    with metric_selector_col:
        with streamlit.popover('Select a Metric', use_container_width=True):
            selected_metric = streamlit.selectbox(
                'Select a Metric',
                metrics,
                label_visibility='collapsed',
                key=f'graph-{graph_number}-metric-selection')

    with node_selector_col:
        with streamlit.popover('Select Nodes', use_container_width=True):
            selected_nodes = streamlit.multiselect(
                'Select a Node',
                nodes,
                label_visibility='collapsed',
                key=f'graph-{graph_number}-node-selection',
                default=nodes)

    with settings_col:
        with streamlit.popover('Settings', use_container_width=True):
            log_scale = streamlit.checkbox(
                "Log scale",
                False,
                help="Make the y-axis log scale",
                key=f'graph-{graph_number}-log-scale')

            transpose = streamlit.checkbox(
                "Transpose",
                False,
                help="Use nodes instead of jobs as the x-axis",
                key=f'graph-{graph_number}-transpose')

            chart_type = streamlit.selectbox(
                'Chart type',
                ['line', 'bar', 'point', 'tick'],
                label_visibility='collapsed',
                key=f'graph-{graph_number}-chart-selection')

    return selected_metric, selected_nodes, log_scale, transpose, chart_type


def graph(metrics, nodes, node_to_step_index_map, graph_number):
    from pandas import DataFrame

    metric, selected_nodes, log_scale, transpose, chart_type = \
        settings(metrics, nodes, graph_number)

    nodes_as_step_and_index = []
    for selected_node in selected_nodes:
        step, index = node_to_step_index_map[selected_node]
        nodes_as_step_and_index.append((step, index))

    if transpose:
        x_axis_label = 'nodes'
        color_label = 'runs'
    else:
        x_axis_label = 'runs'
        color_label = 'nodes'

    y_axis_label = metric

    data, metric_unit = report.get_chart_data(_get_report_chips(), metric, nodes_as_step_and_index)
    if metric_unit:
        y_axis_label = f'{metric} ({metric_unit})'

    # Prepare plot data
    filtered_data = {
        x_axis_label: [],
        y_axis_label: [],
        color_label: []
    }

    labels = {
        "runs": state.get_key(state.GRAPH_JOBS),
        "nodes": [f'{step}{index}' for step, index in data]
    }

    if nodes:
        # filtering through data
        for job_name in state.get_key(state.GRAPH_JOBS):
            for step, index in data:
                filtered_data['runs'].append(job_name)
                filtered_data['nodes'].append(step + index)
                if job_name not in data[(step, index)].keys():
                    filtered_data[y_axis_label].append(None)
                else:
                    filtered_data[y_axis_label].append(data[(step, index)][job_name])

    # Setup chart
    x_axis = altair.X(x_axis_label, axis=altair.Axis(labelAngle=-75), sort=labels[x_axis_label])

    y_axis = y_axis_label
    if log_scale and chart_type != 'bar':
        y_axis = altair.Y(y_axis_label, scale=altair.Scale(type="log"))

    color = color_label

    alt_chart = altair.Chart(DataFrame(filtered_data).dropna(), height=500)

    if chart_type == 'line':
        chart_mark = alt_chart.mark_line(point=True)
    elif chart_type == 'bar':
        chart_mark = alt_chart.mark_bar(point=True)
    elif chart_type == 'point':
        chart_mark = alt_chart.mark_circle(point=True)
    elif chart_type == 'tick':
        chart_mark = alt_chart.mark_tick(point=True)
    else:
        raise ValueError(f'{chart_type} not supported')

    chart = chart_mark.encode(
        x=x_axis,
        y=y_axis,
        color=color)

    streamlit.altair_chart(chart, use_container_width=True, theme='streamlit')


def viewer(node_to_step_index_map):
    nodes, metrics = report.get_chart_selection_options(_get_report_chips())
    metrics = sorted(metrics)

    job_selector_col, graph_adder_col = streamlit.columns(2, gap='large')
    with job_selector_col:
        job_selector()
    with graph_adder_col:
        graphs = graph_count_selector()

    streamlit.divider()

    columns = 1 if graphs <= 1 else 2
    last_row_num = int(math.floor((graphs - 1) / columns)) * columns

    graph_number = 0
    graph_cols = streamlit.columns(columns, gap='large')
    while graph_number < graphs:
        with graph_cols[graph_number % columns]:
            graph(metrics, nodes, node_to_step_index_map, graph_number)
            if graph_number < last_row_num:
                streamlit.divider()
        graph_number += 1
