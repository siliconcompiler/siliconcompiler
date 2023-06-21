import pandas
import os
import sys
sys.path.append('..')
import units

################################

def makeList(chip, steplist=None):
    #from siliconcompiler/siliconcompiler/core.py, "summary" function
    flow = chip.get('option', 'flow')
    steplist = chip.list_steps()

    # only report tool based steps functions
    for step in steplist.copy(): #will definitely need to keep
        tool, task = chip._get_tool_task(step, '0', flow=flow)
        if chip._is_builtin(tool, task):
            index = steplist.index(step)
            del steplist[index]

    # Custom reporting modes
    paramlist = []
    for item in chip.getkeys('option', 'param'):
        paramlist.append(item + "=" + chip.get('option', 'param', item))

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
        metric_type = chip.get('metric', metric, field='type')

        show_metric = False
        for step, index in nodes:
            if metric in chip.getkeys('flowgraph', flow, step, index, 'weight') and \
            chip.get('flowgraph', flow, step, index, 'weight', metric):
                show_metric = True

            value = chip.get('metric', metric, step=step, index=index)
            print(step, index, value)
            if value is not None:
                show_metric = True
            tool, task = chip._get_tool_task(step, index, flow=flow)

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

def get_flowgraph_tasks(chip, nodeList):  
    nodes = {}
    for step, index in nodeList:
        nodes[step, index] = {}
        for key in chip.getkeys('record'):
            # if chip.get('record', key, step=step, index=index):  # check if there is a value to present, if None, then no
            nodes[step, index][key] = chip.get('record', key, step=step, index=index)
    return pandas.DataFrame.from_dict(nodes, orient='index')

################################

def makeDependencies(chip):
    dependenciesDict = {}
    flow = chip.get('option', 'flow')
    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            dependenciesDict[step, index] = []
            # get inputs
            all_inputs = []
            for in_step, in_index in chip.get('flowgraph', flow, step, index, 'input'):
                all_inputs.append((in_step, in_index))
            for item in all_inputs:
                dependenciesDict[step, index].append(item)
    return dependenciesDict

################################

def eliminateRepeatFolderNames(keyCopy, str):
    for index in range(1, len(keyCopy)): 
        if keyCopy[index-1] == str and keyCopy[index] == str:
            return keyCopy[:index] + keyCopy[index+1:]
    return keyCopy

################################

def getAllPaths(chip): 
    allPaths = []
    allkeys = chip.allkeys()
    for key in allkeys:
        for value, step, index in chip.schema._getvals(*key):
            keyCopy = key.copy()
            keyCopy = eliminateRepeatFolderNames(keyCopy, 'default')
            if step is None and index is None:
                pass #should I be passing?
            elif index is None: #isn't getting used
                keyCopy += [step, 'default']
            else:
                keyCopy += [step + index]

            if isinstance(value, list): 
                for item in value:
                    keyCopyCopy = keyCopy.copy()
                    keyCopyCopy.append(item)
                    allPaths.append(keyCopyCopy)
            else:
                keyCopy.append(value)
                allPaths.append(keyCopy)
    return allPaths


################################

def makeManifestHelper(currTree, currTreeNode, remainingTreeNodes): 
    if len(remainingTreeNodes) == 1:
        currTree[currTreeNode] = remainingTreeNodes[0]
        return currTree
    else:
        if currTreeNode in currTree :
            currTree[currTreeNode] = makeManifestHelper(currTree[currTreeNode],
                                                        remainingTreeNodes[0], 
                                                        remainingTreeNodes[1:])
        else:
            currTree[currTreeNode] = makeManifestHelper({},
                                                        remainingTreeNodes[0], 
                                                        remainingTreeNodes[1:])
        return currTree
    
################################

def makeManifest(chip): 
    manifestTree = {}
    allPaths = getAllPaths(chip)
    for path in allPaths :
        makeManifestHelper(manifestTree, 
                              path[0], 
                              path[1:])
    return manifestTree

################################

def getLogsAndReportsRecHelper(pathName, filter=None):
    files = os.listdir(pathName)
    logsReportsTree = []
    nonFolders = []
    for file in files :
        if filter != None and file not in filter:
            continue
        if os.path.isfile(f'{pathName}/{file}'):
            nonFolders.append(file)
        else:
            node = {}
            node["label"] = file
            node["value"] = f'{pathName}/{file}'
            node["children"] = getLogsAndReportsRecHelper(f'{pathName}/{file}')
            logsReportsTree.append(node)
    for file in nonFolders :
        node = {}
        node["label"] = file
        node["value"] = f'{pathName}/{file}'
        logsReportsTree.append(node)
    return logsReportsTree

################################

def getLogsAndReports(chip, tasks):
    logsReportsTree ={}
    for step, index in tasks:
        print(chip._getworkdir(step=step, index=index))
        if os.path.isdir(chip._getworkdir(step=step, index=index)):
            logsReportsTree[step, index] = getLogsAndReportsRecHelper(chip._getworkdir(step=step, index=index), 
                                                                        filter={"inputs",
                                                                                "reports",
                                                                                "outputs", 
                                                                                f'{step}.log',
                                                                                f'{step}.errors',
                                                                                f'{step}.warnings'})
    return logsReportsTree

################################

def getPath(chip):
    steplist = chip.list_steps()
    flow = chip.get('option', 'flow')
    selected_tasks = {}
    to_search = []
    # Start search with any successful leaf tasks.
    leaf_tasks = chip._get_flowgraph_exit_nodes(flow=flow, steplist=steplist)
    for task in leaf_tasks:
        selected_tasks[task] = "End Node"
        to_search.append(task)
    # Search backwards, saving anything that was selected by leaf tasks.
    while len(to_search) > 0: #why do we search the succesful 
        task = to_search.pop(-1)
        inputNodes = chip.get('flowgraph', flow, *task, 'select')
        for selected in inputNodes:
            if selected not in selected_tasks:
                selected_tasks[selected] = None
                to_search.append(selected)
        if inputNodes == []:
            selected_tasks[selected] = "Start Node"
    return selected_tasks

################################

def searchManifestKeys(jsonDict, key):
    filteredDict = {}
    for dictKey in jsonDict:
        if key in dictKey:
            filteredDict[dictKey] = jsonDict[dictKey]
        elif isinstance(jsonDict[dictKey], dict):
            result = searchManifestKeys(jsonDict[dictKey], key)
            if result: #result is non-empty
                filteredDict[dictKey] = result
    return filteredDict

################################

def searchManifestValues(jsonDict, value):
    filteredDict={}
    for dictKey in jsonDict:
        if isinstance(jsonDict[dictKey], dict):
            result = searchManifestValues(jsonDict[dictKey], value)
            if result: #result is non-empty
                filteredDict[dictKey] = result
        elif isinstance(jsonDict[dictKey], str) and value in jsonDict[dictKey] :
            filteredDict[dictKey] = jsonDict[dictKey]
    return filteredDict

################################

#partial matches
def searchManifest(jsonDict, keySearch=None, valueSearch=None):
    #return type is dictionary of dictionary
    if keySearch == None and valueSearch == None:
        return jsonDict
    if valueSearch == None:
        # then user is searching keys
        return searchManifestKeys(jsonDict, keySearch) # may have to encase in dictionary
    # user is searching values
    return searchManifestValues(jsonDict, valueSearch)

################################

def manifestKeyCounter(jsonDict, acc=0):
    acc += len(jsonDict)
    for dictKeys in jsonDict:
        if isinstance(jsonDict[dictKeys], dict):
            acc = manifestKeyCounter(jsonDict[dictKeys], acc)
    return acc

################################