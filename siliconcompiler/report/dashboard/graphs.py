import altair
import pandas
import streamlit
import math

from siliconcompiler.report import report
from siliconcompiler.report.dashboard import state


def graphs_module(metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map):
    '''
    This displays the graph module.

    Args:
        metric_dataframe (pandas.DataFrame) : A dataframe full of all metrics and all
            nodes of the selected chip.
        node_to_step_index_map (dict) : Maps the node to the associated step, index pair.
        metric_to_metric_unit_map (dict) : Maps the metric to the associated metric unit.
    '''
    metrics = metric_dataframe.index.map(lambda x: metric_to_metric_unit_map[x])
    nodes = metric_dataframe.columns
    chips = []
    jobs = state.get_chips()
    for job in jobs:
        chips.append({'chip_object': state.get_chip(job), 'chip_name': job})
    job_selector_col, graph_adder_col = streamlit.columns(2, gap='large')
    with job_selector_col:
        with streamlit.popover('Select Jobs', use_container_width=True):
            selected_jobs = select_runs(jobs)
    with graph_adder_col:
        graphs = streamlit.slider('pick the number of graphs you want', 1, 10,
                                  1, label_visibility='collapsed')

    streamlit.divider()

    columns = 1 if graphs <= 1 else 2
    last_row_num = int(math.floor((graphs - 1) / columns)) * columns

    graph_number = 0
    graph_cols = streamlit.columns(columns, gap='large')
    while graph_number < graphs:
        with graph_cols[graph_number % columns]:
            metric, selected_nodes, log_scale = \
                show_metric_and_node_selection_for_graph(metrics, nodes, graph_number)
            nodes_as_step_and_index = []
            for selected_node in selected_nodes:
                step, index = node_to_step_index_map[selected_node]
                nodes_as_step_and_index.append((step, index))
            structure_graph_data(chips, metric, selected_jobs, nodes_as_step_and_index, log_scale)
            if graph_number < last_row_num:
                streamlit.divider()
        graph_number += 1


def show_metric_and_node_selection_for_graph(metrics, nodes, graph_number):
    """
    Displays selectbox for metrics and nodes which informs the graph on what
    to display.

    Args:
        metrics (list) : A list of metrics that are set for all chips given in chips.
        nodes (list) : A list of nodes given in the form f'{step}{index}'
        graph_number (int) : The number of graphs there are. Used to create
            keys to distinguish selectboxes from each other.
    """
    metric_selector_col, node_selector_col, log_scale_col = streamlit.columns(3, gap='small')
    with metric_selector_col:
        with streamlit.popover('Select a Metric', use_container_width=True):
            selected_metric = streamlit.selectbox(
                'Select a Metric',
                metrics,
                label_visibility='collapsed',
                key=f'metric-selection-{graph_number}')

    with node_selector_col:
        with streamlit.popover('Select Nodes', use_container_width=True):
            selected_nodes = streamlit.multiselect(
                'Select a Node',
                nodes,
                label_visibility='collapsed',
                key=f'node selection {graph_number}',
                default=nodes[0])

    with log_scale_col:
        log_scale = streamlit.checkbox(
            "Log scale",
            False,
            key=f'log-scale-selection-{graph_number}')

    return selected_metric, selected_nodes, log_scale


def show_graph(data, x_axis_label, y_axis_label, color_label, log_scale, height=500):
    """
    Displays a graph with the given "data" on the y-axis and "jobs" on the x-axis.

    Args:
        data (Pandas.DataFrame) : A dataframe containing all the graphing data.
        x_axis_label (string) : The name of the runs column.
        y_axis_label (string) : The name of the jobs column.
        color_label (string) : The name of the nodes column.
        height (int) : The height of one graph.
    """
    x_axis = altair.X(x_axis_label, axis=altair.Axis(labelAngle=-75))

    y_axis = y_axis_label
    if log_scale:
        y_axis = altair.Y(y_axis_label, scale=altair.Scale(type="log"))

    color = color_label
    chart = altair.Chart(data, height=height).mark_line(point=True).encode(
        x=x_axis,
        y=y_axis,
        color=color)

    streamlit.altair_chart(chart, use_container_width=True, theme='streamlit')


def select_runs(jobs):
    """
    Displays a dataframe that can be edited to select specific jobs to include
    in the analysis.

    Args:
        jobs (list) : A list of job names.
    """
    all_jobs = pandas.DataFrame({'job names': jobs, 'selected jobs': [True] * len(jobs)})
    configuration = {'selected jobs': streamlit.column_config.CheckboxColumn('Select runs',
                                                                             default=True)}
    filtered_jobs = streamlit.data_editor(all_jobs, disabled=['job names'],
                                          use_container_width=True, hide_index=True,
                                          column_config=configuration)
    return filtered_jobs


def structure_graph_data(chips, metric, selected_jobs, nodes, log_scale):
    """
    Displays a graph and it's corresponding metric and node selection.

    Args:
        chips (list) : A list of tuples in the form (chip, chip name) where
            the chip name is a string.
        metric (string) : The metric to be inspected.
        selected_jobs (pandas.DataFrame) : A dataframe with a column called
            'selected jobs' which identifies which jobs the user wants to see
            and a corresponding column called 'job names'.
        nodes (list) : A list of dictionaries with the form (step, index).
    """
    x_axis_label = 'runs'
    y_axis_label = metric
    color_label = 'nodes'
    if not nodes:
        show_graph(pandas.DataFrame({x_axis_label: [], y_axis_label: [], color_label: []}),
                   x_axis_label, y_axis_label, color_label, False)
        return
    data, metric_unit = report.get_chart_data(chips, metric, nodes)
    if metric_unit:
        y_axis_label = f'{metric}({metric_unit})'
    filtered_data = {x_axis_label: [], y_axis_label: [], color_label: []}
    # filtering through data
    for is_selected, job_name in zip(selected_jobs['selected jobs'].tolist(),
                                     selected_jobs['job names'].tolist()):
        if is_selected:
            for step, index in data:
                filtered_data[x_axis_label].append(job_name)
                filtered_data[color_label].append(step + index)
                if job_name not in data[(step, index)].keys():
                    filtered_data[y_axis_label].append(None)
                else:
                    filtered_data[y_axis_label].append(data[(step, index)][job_name])
    show_graph(pandas.DataFrame(filtered_data).dropna(), x_axis_label, y_axis_label, color_label, log_scale)
