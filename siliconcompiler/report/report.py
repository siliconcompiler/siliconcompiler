import pandas
import os
import sys
sys.path.append('..')
import units

################################

def make_list(chip): 
    """
    Returns a pandas dataframe
    
    Returns data to display in the data metrics table. All nodes(steps and indices)
    are included on the x-axis while all the metrics tracked are on the y-axis.
    The y-axis row headers are in the form of a tuple where the first element is
    the metric tracked and the second element is the unit.
    
    Args:
        chip(Chip) : the chip object that contains the schema read from
    
    Example:
        >>> make_list(chip)
        returns pandas dataframe of tracked metrics
    """

    #from siliconcompiler/siliconcompiler/core.py, "summary" function
    flow = chip.get('option', 'flow')
    steplist = chip.list_steps()

    # only report tool based steps functions
    for step in steplist.copy(): #will definitely need to keep
        tool, task = chip._get_tool_task(step, '0', flow=flow)
        if chip._is_builtin(tool, task):
            index = steplist.index(step)
            del steplist[index]

    # Collections for data
    nodes = []
    metrics = {}
    metrics_unit = {}

    # Build ordered list of nodes in flowgraph
    for step in steplist:
        for index in chip.getkeys('flowgraph', flow, step):
            nodes.append((step, index))
            metrics[step, index] = {}

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

        show_metric = False
        for step, index in nodes:
            if metric in chip.getkeys('flowgraph', flow, step, index, 'weight') and \
            chip.get('flowgraph', flow, step, index, 'weight', metric):
                show_metric = True

            value = chip.get('metric', metric, step=step, index=index)
            if value is not None:
                show_metric = True
            tool, task = chip._get_tool_task(step, index, flow=flow)

            if value is not None:
                if metric == 'memory':
                    value = units.format_binary(value, metric_unit)
                elif metric in ['exetime', 'tasktime']:
                    metric_unit = None
                    value = units.format_time(value)
                else:
                    value = units.format_si(value, metric_unit)
                try:
                    value = float(value)
                except ValueError:
                    pass

            metrics[step, index][metric] = value

        if show_metric:
            metrics_to_show.append(metric)
            metrics_unit[metric] = metric_unit if metric_unit else ''

    # converts from 2d dictionary to pandas DataFrame, transposes so orientation 
    # is correct, and filters based on the metrics we track
    data = (pandas.DataFrame.from_dict(metrics, orient='index').transpose()).loc[metrics_to_show]
    # include metrics_unit
    data.index = data.index.map(lambda x: (x, metrics_unit[x]))
    return data

################################

def get_flowgraph_nodes(chip, nodeList):
    """
    Returns a pandas dataframe
    
    Returns data to display in the data metrics table. One node(step and index)
    is included on the x-axis while all the metrics tracked are on the y-axis.
    
    Args:
        chip(Chip) : the chip object that contains the schema read from
        nodeList(list) : list containing tuples of steps and indicies
    
    Example:
        >>> get_flowgraph_nodes(chip, [(import, 0), (syn, 0)])
        returns pandas dataframe of tracked metrics
    """
    nodes = {}
    for step, index in nodeList:
        nodes[step, index] = {}
        for key in chip.getkeys('record'):
            nodes[step, index][key] = chip.get('record', key, step=step, index=index)
    return pandas.DataFrame.from_dict(nodes, orient='index')

################################

def make_dependencies(chip):
    """
    Returns a dictionary
    
    Returns a dicitionary where each key is one node, a tuple in the form (step, index) 
    and the value of each key is a list of tuples in the form (step, index).
    The value of each key represents all the nodes that is a prerequisite to the 
    key node.
    
    Args:
        chip(Chip) : the chip object that contains the schema read from
    
    Example:
        >>> make_dependencies(chip)
        returns dictionary of where the values of the keys are the dependencies
    """
    dependencies_dict = {}
    flow = chip.get('option', 'flow')
    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            dependencies_dict[step, index] = []
            for in_step, in_index in chip.get('flowgraph', flow, step, index, 'input'):
                dependencies_dict[step, index].append((in_step, in_index))
    return dependencies_dict

################################

def eliminate_repeat_folder_names(key_copy, str):
    """
    function is a helper for get_all_paths

    Returns a list

    Returns a list where elemenents represent folders. Each successive element/folder
    is a subfolder to the previous element/folder. The list contains strings. When 
    a folder's name is the exact same as the subfolder, this function removes that 
    step. 

    Args:
        key_copy : the string list that represents a directory
        str : the name of the folder to remove if there is a duplicate
    
    Example:
        >>> key = eliminate_repeat_folder_names(['default', 'default', 'str', 'default', 'default'], "default")
        key = ['default', 'str', 'default', 'default'],
    """
    for index in range(1, len(key_copy)): 
        if key_copy[index-1] == str and key_copy[index] == str:
            return key_copy[:index] + key_copy[index+1:]
    return key_copy

################################

def get_all_paths(chip): 
    """
    function is a helper function to make_manifest

    Returns a list

    Returns a list where elemenents are lists. These inner lists contains strings 
    where each successive element/folder is a subfolder to the previous element/folder. 

    Args:
        chip(Chip) : the chip object that contains the schema read from
    
    Example:
        >>> all_paths = get_all_paths(chip)
        all_paths is a 2d list of strings containing all possible directory paths 
        in the manifest
    """
    all_paths = []
    all_keys = chip.allkeys()
    for key in all_keys:
        for value, step, index in chip.schema._getvals(*key):
            key_copy = key.copy()
            key_copy = eliminate_repeat_folder_names(key_copy, 'default')
            if step is None and index is None:
                pass 
            elif index is None: 
                key_copy += [step, 'default']
            else:
                key_copy += [step + index]

            if isinstance(value, list): 
                for item in value:
                    key_copy_copy = key_copy.copy()
                    key_copy_copy.append(item)
                    all_paths.append(key_copy_copy)
            else:
                key_copy.append(value)
                all_paths.append(key_copy)
    return all_paths


################################

def make_manifest_helper(curr_tree, curr_tree_node, remaining_tree_nodes): 
    """
    function is a recursive helper function to make_manifest, more info there

    Args:
        curr_tree(dictionary) : the current tree/json
        curr_tree_node(string) : string of the current node/folder name
        remaining_tree_nodes(list) : list of strings of keys left in the key path
    """
    if len(remaining_tree_nodes) == 1:
        curr_tree[curr_tree_node] = remaining_tree_nodes[0]
        return curr_tree
    else:
        if curr_tree_node in curr_tree: 
           # the tree were creating is already partially made, so add on to that
           # branch
           curr_tree[curr_tree_node] = make_manifest_helper(curr_tree[curr_tree_node],
                                                        remaining_tree_nodes[0], 
                                                        remaining_tree_nodes[1:])
        else:
            # the tree were creating is needs to be created from nothing, so 
            # instantiate a new dictionary
            curr_tree[curr_tree_node] = make_manifest_helper({},
                                                        remaining_tree_nodes[0], 
                                                        remaining_tree_nodes[1:])
        return curr_tree
    
################################

def make_manifest(chip): 
    """
    Returns a dictionary

    Returns a dictionary of dictionaries ... of dictionaries, but it's more helpful
    to think of it as a tree(or json) where each dictionary is a parent node with 
    limitless children nodes. The key to each dicitonary is the name of that node.
    Leaves are key value pairs where the value is not a dictionary but a string. 

    Args:
        chip(Chip) : the chip object that contains the schema read from
    
    Example:
        >>> make_manifest(chip)
        returns tree/json of manifest
    """
    manifest_tree = {}
    all_paths = get_all_paths(chip)
    for path in all_paths:
        make_manifest_helper(manifest_tree, 
                              path[0], 
                              path[1:])
    return manifest_tree

################################

def get_logs_and_reports_helper(path_name, filter=None):
    """
    function is a recursive helper function to get_logs_and_report, more info there

    Args:
        path_name(string) : string of the pathname to the file/folder accessed
        filter(set) : set of desired files/folders, None implies all files or 
                      folders are wanted
    """
    files = os.listdir(path_name)
    logs_reports_tree = []
    non_folders = []
    for file in files :
        if filter != None and file not in filter:
            continue
        if os.path.isfile(f'{path_name}/{file}'):
            non_folders.append(file)
        else:
            node = {}
            # these keys are specific to streamlit_tree_select
            node["label"] = file
            node["value"] = f'{path_name}/{file}'
            node["children"] = get_logs_and_reports_helper(f'{path_name}/{file}')
            logs_reports_tree.append(node)
    for file in non_folders:
        node = {}
        # these keys are specific to streamlit_tree_select
        node["label"] = file
        node["value"] = f'{path_name}/{file}'
        logs_reports_tree.append(node)
    return logs_reports_tree

################################

def get_logs_and_reports(chip, nodes):
    """
    Returns a dictionary

    Returns a dictionary of lists ... of dictionaries of lists, but it's more helpful
    to think of it as a tree where each dictionary is a parent node with 
    limitless children nodes. The key to each dicitonary is the name of that node.
    Leaves are key value pairs where the value is not a dictionary but a string. 

    Args:
        chip(Chip) : the chip object that contains the schema read from
        nodes(list) : list of tuples following the form (step, index)
    
    Example:
        >>> get_logs_and_reports(chip, [('import', '0'), ('syn', '0')])
        returns dictionary that has keys ('import', '0'), ('syn', '0') where the
        values of those keys are the logs and reports of that node
    """
    logs_reports_tree ={}
    for step, index in nodes:
        if os.path.isdir(chip._getworkdir(step=step, index=index)):
            logs_reports_tree[step, index] = get_logs_and_reports_helper(chip._getworkdir(step=step, index=index), 
                                                                        filter={"inputs",
                                                                                "reports",
                                                                                "outputs", 
                                                                                f'{step}.log',
                                                                                f'{step}.errors',
                                                                                f'{step}.warnings'})
    return logs_reports_tree

################################

def get_path(chip):
    """
    Returns a dictionary

    Returns a dictionary where each key is a node that is part of the "winning"
    path. The value of each key is either None, "End Node", or "Start Node". None
    implies that that node is neither and end node nor a start node.

    Args:
        chip(Chip) : the chip object that contains the schema read from
    
    Example:
        >>> get_path(chip)
        returns the "winning" path for that job
    """
    steplist = chip.list_steps()
    flow = chip.get('option', 'flow')
    selected_nodes = {}
    to_search = []
    # Start search with any successful leaf nodes.
    leaf_nodes = chip._get_flowgraph_exit_nodes(flow=flow, steplist=steplist)
    for node in leaf_nodes:
        selected_nodes[node] = "End Node"
        to_search.append(node)
    # Search backwards, saving anything that was selected by leaf nodes.
    while len(to_search) > 0:
        node = to_search.pop(-1)
        input_nodes = chip.get('flowgraph', flow, *node, 'select')
        for selected in input_nodes:
            if selected not in selected_nodes:
                selected_nodes[selected] = None
                to_search.append(selected)
        if input_nodes == []:
            selected_nodes[selected] = "Start Node"
    return selected_nodes

################################

def search_manifest_keys(manifest, key):
    """
    function is a recursive helper to search_manifest, more info there

    Args:
        manifest(dictionary) : a dicitionary representing the manifest
        key(string) : searches all keys for partial matches on this string
    """
    filtered_manifest = {}
    for dictKey in manifest:
        if key in dictKey:
            filtered_manifest[dictKey] = manifest[dictKey]
        elif isinstance(manifest[dictKey], dict):
            result = search_manifest_keys(manifest[dictKey], key)
            if result: #result is non-empty
                filtered_manifest[dictKey] = result
    return filtered_manifest

################################

def search_manifest_values(manifest, value):
    """
    function is a recursive helper to search_manifest, more info there

    Args:
        manifest(dictionary) : a dicitionary representing the manifest
        value(string) : searches all values for partial matches on this string
    """
    filtered_manifest={}
    for dictKey in manifest:
        if isinstance(manifest[dictKey], dict):
            result = search_manifest_values(manifest[dictKey], value)
            if result: #result is non-empty
                filtered_manifest[dictKey] = result
        elif isinstance(manifest[dictKey], str) and value in manifest[dictKey] :
            filtered_manifest[dictKey] = manifest[dictKey]
    return filtered_manifest

################################

#partial matches
def search_manifest(manifest, key_search=None, value_search=None):
    """
    Returns a dictionary

    Returns the same structure as make_manifest, but it is filtered by partial 
    matches by keys or values. If both key_search and value_search are None, the 
    original manifest is returned.

    Args:
        manifest(dictionary) : a dicitionary representing the manifest
        key_search(string) : searches all keys for partial matches on this string
        value_search(string) : searches all values for partial matches on this string
    
    Example:
        >>> search_manifest(jsonDict, key_search='input', value_search='v')
        returns a filtered version of jsonDict where each path contains at least 
        one key that contains the substring input and has values that contain v.
    """
    if key_search == None and value_search == None:
        return manifest
    if value_search == None:
        # then user is searching keys
        return search_manifest_keys(manifest, key_search) # may have to encase in dictionary
    # user is searching values
    return search_manifest_values(manifest, value_search)

################################

def manifest_key_counter(manifest, acc=0):
    """
    Returns an int

    Returns the number of folders and files

    Args:
        manifest(dictionary) : a dicitionary representing the manifest
        acc(int) : an accumulator of the current number of folders and files
    """
    acc += len(manifest)
    for dictKeys in manifest:
        if isinstance(manifest[dictKeys], dict):
            acc = manifest_key_counter(manifest[dictKeys], acc)
    return acc

################################