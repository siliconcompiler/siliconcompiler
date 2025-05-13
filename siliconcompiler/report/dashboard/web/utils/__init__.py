from siliconcompiler import NodeStatus

from pathlib import Path


def get_chip_cwd(chip, manifest):
    build_dir = Path(chip.get('option', 'builddir'))

    manifest_path = Path(manifest)
    for path in manifest_path.parents:
        if build_dir.name == path.name:
            return str(path.parent)

    return None


def make_node_to_step_index_map(chip, metric_dataframe):
    '''
    Returns a map from the name of a node to the associated step, index pair.

    Args:
        metric_dataframe (pandas.DataFrame) : A dataframe full of all metrics and all
            nodes of the selected chip
    '''
    node_to_step_index_map = {}
    if chip.get('option', 'flow'):
        for step, index in chip.schema.get("flowgraph", chip.get('option', 'flow'),
                                           field="schema").get_nodes():
            node_to_step_index_map[f'{step}{index}'] = (step, index)

    # concatenate step and index
    metric_dataframe.columns = metric_dataframe.columns.map(lambda x: f'{x[0]}{x[1]}')
    return node_to_step_index_map, metric_dataframe


def make_metric_to_metric_unit_map(metric_dataframe):
    '''
    Returns a map from the name of a metric to the associated metric and unit in
    the form f'{x[0]} ({x[1]})'

    Args:
        metric_dataframe (pandas.DataFrame) : A dataframe full of all metrics and all
            nodes of the selected chip.
    '''
    metric_to_metric_unit_map = {}
    for metric, unit in metric_dataframe.index.tolist():
        if unit != '':
            metric_to_metric_unit_map[f'{metric} ({unit})'] = metric
        else:
            metric_to_metric_unit_map[metric] = metric
    # concatenate metric and unit
    metric_dataframe.index = metric_dataframe.index.map(lambda x: f'{x[0]} ({x[1]})'
                                                        if x[1] else x[0])
    return metric_to_metric_unit_map, metric_dataframe


def is_running(chip):
    if not chip.get('option', 'flow'):
        return False
    for step, index in chip.schema.get("flowgraph", chip.get('option', 'flow'),
                                       field="schema").get_nodes():
        state = chip.get('record', 'status', step=step, index=index)
        if not NodeStatus.is_done(state):
            return True
    return False


def generate_metric_dataframe(chip):
    from siliconcompiler.report import report

    metric_dataframe = report.make_metric_dataframe(chip)
    node_to_step_index_map, metric_dataframe = \
        make_node_to_step_index_map(chip, metric_dataframe)
    metric_to_metric_unit_map, metric_dataframe = \
        make_metric_to_metric_unit_map(metric_dataframe)

    return metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map
