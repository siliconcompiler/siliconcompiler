import pandas
import os
from siliconcompiler import Schema
from siliconcompiler.report import utils


def make_metric_dataframe(chip):
    '''
    Returns a pandas dataframe to display in the data metrics table. All nodes
    (steps and indices) are included on the x-axis while the metrics tracked
    are on the y-axis. The y-axis row headers are in the form of a tuple where
    the first element is the metric tracked and the second element is the unit.

    Args:
        chip (Chip) : The chip object that contains the schema read from.

    Example:
        >>> make_metric_dataframe(chip)
        Returns pandas dataframe of tracked metrics.
    '''
    nodes, errors, metrics, metrics_unit, metrics_to_show, reports = utils._collect_data(chip)
    # converts from 2d dictionary to pandas DataFrame, transposes so
    # orientation is correct, and filters based on the metrics we track
    data = (pandas.DataFrame.from_dict(metrics, orient='index').transpose())
    data = data.loc[metrics_to_show]
    # include metrics_unit
    data.index = data.index.map(lambda x: (x, metrics_unit[x]))
    return data


def get_flowgraph_nodes(chip, step, index):
    '''
    Returns a dictionary to display in the data metrics table. One node
    (step and index) is included on the x-axis while all the metrics tracked
    are on the y-axis. Removes all key value pairs where the value is None.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
        step (string) : Step of node.
        index (string) : Index of node.

    Example:
        >>> get_flowgraph_nodes(chip, [(import, 0), (syn, 0)])
        Returns pandas dataframe of tracked metrics.
    '''
    nodes = {}
    tool, task = chip._get_tool_task(step, index)
    if tool is not None:
        nodes['tool'] = tool
    if task is not None:
        nodes['task'] = task
    for key in chip.getkeys('record'):
        if chip.get('record', key, field='pernode') == 'never':
            value = chip.get('record', key)
        else:
            value = chip.get('record', key, step=step, index=index)
        if value is not None:
            nodes[key] = value
    return nodes


def get_flowgraph_edges(chip):
    '''
    Returns a dicitionary where each key is one node, a tuple in the form
    (step, index) and the value of each key is a set of tuples in the form
    (step, index). The value of each key represents all the nodes that are
    inputs to the key node.

    Args:
        chip (Chip) : The chip object that contains the schema read from.

    Example:
        >>> get_flowgraph_edges(chip)
        Returns dictionary where the values of the keys are the edges.
    '''
    flowgraph_edges = {}
    flow = chip.get('option', 'flow')
    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            flowgraph_edges[step, index] = set()
            for in_step, in_index in chip.get('flowgraph', flow, step, index, 'input'):
                flowgraph_edges[step, index].add((in_step, in_index))
    return flowgraph_edges


def make_manifest_helper(manifest_subsect, modified_manifest_subsect):
    '''
    Function is a helper function to make_manifest. It mutates the input json.

    Args:
        manifest_subsect (dict) : Represents a subset of the original manifest.
        modified_manifest_subsect (dict) : Represents a subset of the original
            manifest, modified for readability.

    Example:
        >>> make_manifest_helper(manifest_subsection, {})
        Mutates second paramaeter to remove simplify leaf nodes and remove
        'default' nodes.
    '''

    def build_leaf(manifest_subsect):
        if manifest_subsect['pernode'] == 'never':
            if 'global' in manifest_subsect['node']:
                value = manifest_subsect['node']['global']['global']['value']
            else:
                value = manifest_subsect['node']['default']['default']['value']
            return value
        else:
            nodes = manifest_subsect['node']
            node_values = {}
            for step in nodes:
                if step == 'default' or step == 'global':
                    value = nodes[step][step]['value']
                    node_values[step] = value
                else:
                    for index in nodes[step]:
                        value = nodes[step][index]['value']
                        if value is None:
                            continue
                        if index == 'default' or index == 'global':
                            node_values[step] = value
                        else:
                            node_values[step + index] = value
            return node_values

    if Schema._is_leaf(manifest_subsect):
        if manifest_subsect['pernode'] == 'never':
            if 'global' in manifest_subsect['node']:
                value = manifest_subsect['node']['global']['global']['value']
            else:
                value = manifest_subsect['node']['default']['default']['value']
            modified_manifest_subsect['value'] = value
        else:
            nodes = manifest_subsect['node']
            for step in nodes:
                if step == 'default' or step == 'global':
                    value = nodes[step][step]['value']
                    modified_manifest_subsect[step] = value
                else:
                    for index in nodes[step]:
                        value = nodes[step][index]['value']
                        if value is None:
                            continue
                        if index == 'default' or index == 'global':
                            modified_manifest_subsect[step] = value
                        else:
                            modified_manifest_subsect[step + index] = value

    for key, key_dict in manifest_subsect.items():
        if key != 'default':
            if Schema._is_leaf(key_dict):
                modified_manifest_subsect[key] = build_leaf(key_dict)
            else:
                modified_manifest_subsect[key] = {}
                make_manifest_helper(key_dict, modified_manifest_subsect[key])


def make_manifest(chip):
    '''
    Returns a dictionary of dictionaries/json

    Args:
        chip (Chip) : The chip object that contains the schema read from.

    Example:
        >>> make_manifest(chip)
        Returns tree/json of manifest.
    '''
    manifest = chip.schema.cfg
    modified_manifest = {}
    make_manifest_helper(manifest, modified_manifest)
    return modified_manifest


def get_flowgraph_path(chip):
    '''
    Returns a set of all the nodes in the 'winning' path.

    Args:
        chip (Chip) : The chip object that contains the schema read from.

    Example:
        >>> get_flowgraph_path(chip)
        Returns the "winning" path for that job.
    '''
    flow = chip.get('option', 'flow')
    return utils._get_flowgraph_path(chip, flow, chip.nodes_to_execute())


def search_manifest_keys(manifest, key):
    '''
    Function is a recursive helper to search_manifest, more info there.

    Args:
        manifest (dictionary) : A dictionary representing the manifest.
        key (string) : Searches all keys for partial matches on this string.
    '''
    filtered_manifest = {}
    for dict_key in manifest:
        if key in dict_key:
            filtered_manifest[dict_key] = manifest[dict_key]
        elif isinstance(manifest[dict_key], dict):
            result = search_manifest_keys(manifest[dict_key], key)
            if result:  # result is non-empty
                filtered_manifest[dict_key] = result
    return filtered_manifest


def search_manifest_values(manifest, value):
    '''
    Function is a recursive helper to search_manifest, more info there.

    Args:
        manifest (dictionary) : A dicitionary representing the manifest.
        value (string) : Searches all values for partial matches on this
            string.
    '''
    filtered_manifest = {}
    for key in manifest:
        if isinstance(manifest[key], dict):
            result = search_manifest_values(manifest[key], value)
            if result:  # result is non-empty
                filtered_manifest[key] = result
        elif isinstance(manifest[key], str) and value in manifest[key]:
            filtered_manifest[key] = manifest[key]
    return filtered_manifest


def search_manifest(manifest, key_search=None, value_search=None):
    '''
    Returns the same structure as make_manifest, but it is filtered by partial
    matches by keys or values. If both key_search and value_search are None,
    the original manifest is returned.

    Args:
        manifest (dictionary) : A dicitionary representing the manifest.
        key_search (string) : Searches all keys for partial matches on this
            string
        value_search(string) : Searches all values for partial matches
            on this string.

    Example:
        >>> search_manifest(jsonDict, key_search='input', value_search='v')
        Returns a filtered version of jsonDict where each path contains at
        least one key that contains the substring input and has values that
        contain v.
    '''
    return_manifest = manifest
    if key_search:
        return_manifest = search_manifest_keys(return_manifest, key_search)
    if value_search:
        return_manifest = search_manifest_values(return_manifest, value_search)
    return return_manifest


def get_total_manifest_key_count(manifest):
    '''
    Returns (int) the number of keys

    Args:
        manifest (dictionary) : A dicitionary representing the manifest.
        acc (int) : An accumulator of the current number of folders and files.
    '''
    acc = len(manifest)
    for dictKeys in manifest:
        if isinstance(manifest[dictKeys], dict):
            acc += get_total_manifest_key_count(manifest[dictKeys])
    return acc


def get_metrics_source(chip, step, index):
    '''
    Returns a dictionary where the keys are files in the logs and reports for
    a given step and index. The values are a list of the metrics that come from
    that file. If a file is not in the dictionary, that implies that no metrics
    come from it.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
        step (string) : Step of node.
        index (string) : Index of node.
    '''
    file_to_metric = {}
    tool, task = chip._get_tool_task(step, index)
    metrics = chip.getkeys('tool', tool, 'task', task, 'report')
    for metric in metrics:
        sources = chip.get('tool', tool, 'task', task, 'report', metric, step=step, index=index)
        for source in sources:
            if source in file_to_metric:
                file_to_metric[source].append(metric)
            else:
                file_to_metric[source] = [metric]
    return file_to_metric


def get_files(chip, step, index):
    '''
    Returns a list of 3-tuple that contain the path name of how to get to that
    folder, the subfolders of that directory, and it's files. The list is
    ordered by layer of directory.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
        step (string) : Step of node.
        index (string) : Index of node.
    '''
    # could combine filters, but slightly more efficient to separate them
    # Is remaking the list with sets instead of list worth it?
    logs_and_reports = []
    all_paths = os.walk(chip._getworkdir(step=step, index=index))
    for path_name, folders, files in all_paths:
        logs_and_reports.append((path_name, set(folders), set(files)))
    return logs_and_reports


def get_chart_data(chips, metric, nodes):
    '''
    Returns returns a a tuple where the first element is a 2d dictionary of
    data points, following the forms {step+index: {chip_name: value}} where
    each dictionary can have many keys. The second element is a string that represents the unit.

    Args:
        chips (list) : A list of dictionaries with the form
            {'chip_object': chip, 'chip_name': name}.
        metric (string) : The metric that the user is searching.
        nodes (list) : A list of dictionaries with the form (step, index).
    '''
    metric_units = set()  # the set of all units for this metric (hopefully, it's length is 0 or 1)
    metric_datapoints = {}
    metric_unit = ''
    for chip_and_chip_name in chips:
        chip = chip_and_chip_name['chip_object']
        chip_name = chip_and_chip_name['chip_name']
        nodes_list, errors, metrics, metrics_unit, metrics_to_show, reports = \
            utils._collect_data(chip, format_as_string=False)
        if metric in metrics_unit:
            metric_unit = metrics_unit[metric]
            metric_units.add(metric_unit)
        for node in nodes:
            if node not in metrics:
                continue
            value = metrics[node][metric]
            if value is None:
                continue
            if node in metric_datapoints:
                metric_datapoints[node][chip_name] = value
            else:
                metric_datapoints[node] = {chip_name: value}
    if len(metric_units) > 1:
        raise ValueError('Not all measurements were made with the same units')
    return metric_datapoints, metric_unit
