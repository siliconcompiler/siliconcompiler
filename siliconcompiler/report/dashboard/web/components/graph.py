"""
A collection of functions for creating and managing interactive metric graphs
in the web dashboard using Streamlit and Altair.
"""
import altair
import streamlit

from siliconcompiler.report import report

from siliconcompiler.report.dashboard.web import state


def _get_report_projects():
    """
    Gathers all loaded project objects and their names for reporting.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains
                    'project_object' and 'project_name'.
    """
    projects = []
    for job in state.get_projects():
        projects.append({'project_object': state.get_project(job), 'project_name': job})
    return projects


def job_selector():
    """
    Displays a data editor in a popover for selecting which jobs to include
    in the graphs.

    The selection is stored in the session state.
    """
    from pandas import DataFrame

    jobs = state.get_projects()

    all_jobs_df = DataFrame({
        'job names': jobs,
        'selected jobs': [job in state.get_key(state.GRAPH_JOBS) for job in jobs]
    })

    configuration = {
        'selected jobs': streamlit.column_config.CheckboxColumn(
            'Select runs',
            default=True)
    }

    with streamlit.popover('Select Jobs', use_container_width=True):
        selected_jobs_df = streamlit.data_editor(
            all_jobs_df,
            disabled=['job names'],
            use_container_width=True,
            hide_index=True,
            column_config=configuration)

        selected_jobs_list = [
            job_name for is_selected, job_name in zip(
                selected_jobs_df['selected jobs'], selected_jobs_df['job names']
            ) if is_selected
        ]

        state.set_key(state.GRAPH_JOBS, selected_jobs_list)


def graph_count_selector():
    """
    Displays a slider to control the number of graphs shown on the page.

    Returns:
        int: The number of graphs selected by the user.
    """
    return streamlit.slider(
        'pick the number of graphs you want',
        1, 10, 1,
        label_visibility='collapsed')


def settings(metrics, nodes, graph_number):
    """
    Displays settings controls for a single graph instance.

    This includes popovers for selecting a metric, nodes, and other graph
    options like log scale, transpose, and chart type.

    Args:
        metrics (list): A list of available metric names.
        nodes (list): A list of available node names in 'step/index' format.
        graph_number (int): The unique identifier for the graph, used to create
            distinct keys for the UI widgets.

    Returns:
        tuple: A tuple containing the selected metric, nodes, log_scale flag,
               transpose flag, and chart type.
    """
    metric_selector_col, node_selector_col, settings_col = \
        streamlit.columns(3, gap='small')

    with metric_selector_col:
        with streamlit.popover('Select a Metric', use_container_width=True):
            selected_metric = streamlit.selectbox(
                'Select a Metric', metrics,
                label_visibility='collapsed',
                key=f'graph-{graph_number}-metric-selection')

    with node_selector_col:
        with streamlit.popover('Select Nodes', use_container_width=True):
            selected_nodes = streamlit.multiselect(
                'Select a Node', nodes,
                label_visibility='collapsed',
                key=f'graph-{graph_number}-node-selection',
                default=nodes)

    with settings_col:
        with streamlit.popover('Settings', use_container_width=True):
            log_scale = streamlit.checkbox(
                "Log scale", False,
                help="Make the y-axis log scale",
                key=f'graph-{graph_number}-log-scale')

            transpose = streamlit.checkbox(
                "Transpose", False,
                help="Use nodes instead of jobs as the x-axis",
                key=f'graph-{graph_number}-transpose')

            chart_type = streamlit.selectbox(
                'Chart type', ['line', 'bar', 'point', 'tick'],
                label_visibility='collapsed',
                key=f'graph-{graph_number}-chart-selection')

    return selected_metric, selected_nodes, log_scale, transpose, chart_type


def graph(metrics, nodes, node_to_step_index_map, graph_number):
    """
    Renders a single, configurable metric graph using Altair.

    This function gets the user's settings, fetches the corresponding data,
    and constructs and displays an Altair chart.

    Args:
        metrics (list): A list of all available metrics.
        nodes (list): A list of all available nodes.
        node_to_step_index_map (dict): A mapping from node names to
            (step, index) tuples.
        graph_number (int): The unique identifier for this graph instance.
    """
    from pandas import DataFrame

    metric, selected_nodes, log_scale, transpose, chart_type = \
        settings(metrics, nodes, graph_number)

    nodes_as_step_and_index = [
        node_to_step_index_map[node] for node in selected_nodes
    ]

    # --- Data Fetching and Preparation ---
    if transpose:
        x_axis_label, color_label = 'nodes', 'runs'
    else:
        x_axis_label, color_label = 'runs', 'nodes'

    y_axis_label = metric
    data, metric_unit = report.get_chart_data(
        _get_report_projects(), metric, nodes_as_step_and_index)
    if metric_unit:
        y_axis_label = f'{metric} ({metric_unit})'

    # Reshape data into a long-form DataFrame suitable for Altair
    plot_data = []
    if data:
        for (step, index), job_data in data.items():
            for job_name, value in job_data.items():
                if job_name in state.get_key(state.GRAPH_JOBS):
                    plot_data.append({
                        'runs': job_name,
                        'nodes': f'{step}/{index}',
                        y_axis_label: value
                    })
    filtered_df = DataFrame(plot_data).dropna()

    # --- Chart Configuration and Rendering ---
    if not filtered_df.empty:
        sort_order = {
            "runs": state.get_key(state.GRAPH_JOBS),
            "nodes": selected_nodes
        }

        x_axis = altair.X(x_axis_label,
                          axis=altair.Axis(labelAngle=-75),
                          sort=sort_order[x_axis_label])

        y_axis = altair.Y(y_axis_label)
        if log_scale and chart_type != 'bar':
            y_axis = altair.Y(y_axis_label, scale=altair.Scale(type="log"))

        color = color_label

        alt_chart = altair.Chart(filtered_df, height=500)

        if chart_type == 'line':
            chart_mark = alt_chart.mark_line(point=True)
        elif chart_type == 'bar':
            chart_mark = alt_chart.mark_bar()
        elif chart_type == 'point':
            chart_mark = alt_chart.mark_circle()
        elif chart_type == 'tick':
            chart_mark = alt_chart.mark_tick()
        else:
            raise ValueError(f'{chart_type} not supported')

        chart = chart_mark.encode(x=x_axis, y=y_axis, color=color)
        streamlit.altair_chart(chart, use_container_width=True, theme='streamlit')
    else:
        streamlit.warning("No data available for the selected metric and nodes.")


def viewer(node_to_step_index_map):
    """
    The main container component for the graphing page.

    It lays out the job selector, the graph count selector, and the
    individual graph components in a grid.

    Args:
        node_to_step_index_map (dict): A mapping from node names to
            (step, index) tuples, passed down to the graph components.
    """
    nodes, metrics = report.get_chart_selection_options(_get_report_projects())
    metrics = sorted(metrics)

    # Initialize selected jobs if not already set
    if state.get_key(state.GRAPH_JOBS) is None:
        state.set_key(state.GRAPH_JOBS, state.get_projects())

    # --- UI Layout ---
    job_selector_col, graph_adder_col = streamlit.columns(2, gap='large')
    with job_selector_col:
        job_selector()
    with graph_adder_col:
        graphs = graph_count_selector()

    streamlit.divider()

    # Create a responsive grid for the graphs
    columns = 1 if graphs <= 1 else 2
    for i in range(graphs):
        if i % columns == 0:
            # Start a new row of columns
            graph_cols = streamlit.columns(columns, gap='large')
        with graph_cols[i % columns]:
            graph(metrics, nodes, node_to_step_index_map, i)
            # Add a divider between rows
            if i < graphs - columns:
                streamlit.divider()
