"""
Utility functions for the SiliconCompiler web dashboard.

This module provides helper functions for processing project data, formatting it
for display, and checking the status of a run. These functions are used by
the main dashboard application to interact with the project object and prepare
data for UI components.
"""
from siliconcompiler import NodeStatus
from pathlib import Path


def get_project_cwd(project, manifest):
    """
    Determines the original project working directory from a manifest path.

    This function is useful for resolving relative paths when the dashboard
    is run from a different location than the original compilation. It traverses
    up from the manifest's location to find the parent of the build directory.

    Args:
        project (Project): The project object.
        manifest (str): The absolute path to the project's manifest file.

    Returns:
        str or None: The absolute path to the project's original working
                     directory, or None if it cannot be determined.
    """
    build_dir = Path(project.get('option', 'builddir'))

    manifest_path = Path(manifest)
    for path in manifest_path.parents:
        if build_dir.name == path.name:
            return str(path.parent)

    return None


def make_node_to_step_index_map(project, metric_dataframe):
    """
    Creates a mapping from a node's string representation to its (step, index) tuple.

    It also renames the columns of the metric dataframe to the 'step/index' format.

    Args:
        project (Project): The project object.
        metric_dataframe (pandas.DataFrame): The dataframe of metrics, with
            multi-level columns of (step, index).

    Returns:
        tuple: A tuple containing:
            - dict: A dictionary mapping 'step/index' strings to (step, index) tuples.
            - pandas.DataFrame: The modified metric dataframe.
    """
    node_to_step_index_map = {}
    if project.get('option', 'flow'):
        for step, index in project.get("flowgraph", project.get('option', 'flow'),
                                       field="schema").get_nodes():
            node_to_step_index_map[f'{step}/{index}'] = (step, index)

    # Concatenate step and index in the DataFrame columns
    metric_dataframe.columns = metric_dataframe.columns.map(lambda x: f'{x[0]}/{x[1]}')
    return node_to_step_index_map, metric_dataframe


def make_metric_to_metric_unit_map(metric_dataframe):
    """
    Creates a mapping from a formatted metric string to the raw metric name.

    It also renames the index of the metric dataframe to include units,
    e.g., 'cells (count)'.

    Args:
        metric_dataframe (pandas.DataFrame): The dataframe of metrics, with
            a multi-level index of (metric, unit).

    Returns:
        tuple: A tuple containing:
            - dict: A dictionary mapping formatted metric strings to raw metric names.
            - pandas.DataFrame: The modified metric dataframe.
    """
    metric_to_metric_unit_map = {}
    for metric, unit in metric_dataframe.index.tolist():
        if unit:
            metric_to_metric_unit_map[f'{metric} ({unit})'] = metric
        else:
            metric_to_metric_unit_map[metric] = metric

    # Concatenate metric and unit in the DataFrame index
    metric_dataframe.index = metric_dataframe.index.map(lambda x: f'{x[0]} ({x[1]})'
                                                        if x[1] else x[0])
    return metric_to_metric_unit_map, metric_dataframe


def is_running(project):
    """
    Checks if any node in the project's flowgraph is still running.

    Args:
        project (Project): The project object to check.

    Returns:
        bool: True if any node is not in a 'done' state, False otherwise.
    """
    if not project.get('option', 'flow'):
        return False

    for step, index in project.get("flowgraph", project.get('option', 'flow'),
                                   field="schema").get_nodes():
        state = project.get('record', 'status', step=step, index=index)
        if not NodeStatus.is_done(state):
            return True
    return False


def generate_metric_dataframe(project):
    """
    Generates a fully processed metric dataframe and associated mappings.

    This function orchestrates the creation of the metric dataframe and the
    helper dictionaries needed to easily look up nodes and metrics in the UI.

    Args:
        project (Project): The project object from which to generate the report.

    Returns:
        tuple: A tuple containing:
            - pandas.DataFrame: The processed metric dataframe.
            - dict: The node-to-(step, index) mapping.
            - dict: The formatted-metric-to-raw-metric mapping.
    """
    from siliconcompiler.report import report

    metric_dataframe = report.make_metric_dataframe(project)
    node_to_step_index_map, metric_dataframe = \
        make_node_to_step_index_map(project, metric_dataframe)
    metric_to_metric_unit_map, metric_dataframe = \
        make_metric_to_metric_unit_map(metric_dataframe)

    return metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map
