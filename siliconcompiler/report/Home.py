#>> streamlit run Home.py

import streamlit
import pandas as pd
import os
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select
from PIL import Image

import sys
sys.path.append('..')
import units
import core


streamlit.set_page_config(page_title="Semi-Conductor Metrics",
                          page_icon=Image.open("zeroASIC.jpeg"),
                          layout="wide")

################################

@streamlit.cache_data
def makeList(_self, steplist=None):
    #from siliconcompiler/siliconcompiler/core.py, "summary" function

    flow = _self.get('option', 'flow')
    if not steplist: #might be redundant
        if _self.get('option', 'steplist'):
            steplist = _self.get('option', 'steplist')
        else:
            steplist = _self.list_steps()

    # Find all tasks that are part of a "winning" path.
    selected_tasks = set()
    to_search = []

    # Successful tasks
    color_of_tasks = {}

    # Start search with any successful leaf tasks.
    leaf_tasks = _self._get_flowgraph_exit_nodes(flow=flow, steplist=steplist)
    for task in leaf_tasks:
        to_search.append(task)
        selected_tasks.add(task)

    # Search backwards, saving anything that was selected by leaf tasks.
    while len(to_search) > 0: #why do we search the succesful 
        task = to_search.pop(-1)
        for selected in _self.get('flowgraph', flow, *task, 'select'):
            if selected not in selected_tasks:
                selected_tasks.add(selected)
                to_search.append(selected)

    # only report tool based steps functions
    for step in steplist.copy(): #will definitely need to keep
        tool, task = _self._get_tool_task(step, '0', flow=flow)
        if _self._is_builtin(tool, task):
            index = steplist.index(step)
            del steplist[index]

    # job directory
    jobdir = _self._getworkdir() #what do I need this for?

    # Custom reporting modes
    paramlist = []
    for item in _self.getkeys('option', 'param'):
        paramlist.append(item + "=" + _self.get('option', 'param', item))

    if paramlist:
        paramstr = ', '.join(paramlist)
    else:
        paramstr = "None"

    info_list = ["SUMMARY:\n",
                "design : " + _self.top(),
                "params : " + paramstr,
                "jobdir : " + jobdir,
                ]

    if _self.get('option', 'mode') == 'asic':
        pdk = _self.get('option', 'pdk')

        libraries = set()
        for val, step, _ in _self.schema._getvals('asic', 'logiclib'):
            if not step or step in steplist:
                libraries.update(val)

        info_list.extend([f"foundry : {_self.get('pdk', pdk, 'foundry')}",
                        f"process : {pdk}",
                        f"targetlibs : {' '.join(libraries)}"])
    elif _self.get('option', 'mode') == 'fpga':
        info_list.extend([f"partname : {_self.get('fpga','partname')}"])

    # Collections for data
    nodes = []
    errors = {}
    metrics = {}
    metrics_unit = {}
    reports = {}

    # Build ordered list of nodes in flowgraph
    for step in steplist:
        for index in _self.getkeys('flowgraph', flow, step):
            nodes.append((step, index))
            metrics[step+index] = {}
            reports[step, index] = {}

    # Gather data and determine which metrics to show
    # We show a metric if:
    # - it is not in ['option', 'metricoff'] -AND-
    # - at least one step in the steplist has a non-zero weight for the metric -OR -
    #   at least one step in the steplist set a value for it
    metrics_to_show = []
    for metric in _self.getkeys('metric'):
        if metric in _self.get('option', 'metricoff'):
            continue

        # Get the unit associated with the metric
        metric_unit = None
        if _self.schema._has_field('metric', metric, 'unit'):
            metric_unit = _self.get('metric', metric, field='unit')
        metric_type = _self.get('metric', metric, field='type')

        show_metric = False
        for step, index in nodes:
            if metric in _self.getkeys('flowgraph', flow, step, index, 'weight') and \
            _self.get('flowgraph', flow, step, index, 'weight', metric):
                show_metric = True

            value = _self.get('metric', metric, step=step, index=index)
            if value is not None:
                show_metric = True
            tool, task = _self._get_tool_task(step, index, flow=flow)
            rpts = _self.get('tool', tool, 'task', task, 'report', metric,
                            step=step, index=index)

            errors[step, index] = _self.get('flowgraph', flow, step, index, 'status') == \
                core.TaskStatus.ERROR

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
        
            metrics[step+index][metric] = value
            reports[step, index][metric] = rpts

        if show_metric:
            metrics_to_show.append(metric)
            metrics_unit[metric] = metric_unit if metric_unit else ''

    return pd.DataFrame.from_dict(metrics, orient='index').transpose()

################################

def get_step_and_index(string):  
    index = 0
    while string[index].isalpha() :
        index += 1
    return (string[0:index], string[index:])

################################

@streamlit.cache_data
def get_flowgraph_tasks(_self, nodeList, steplist=None):  
    # REQ : nodeList is in the form ['import0', 'syn0', ...]
    nodes = {}
    for task in nodeList:
        step, index = get_step_and_index(task)
        nodes[step+index] = {}
        nodes[step+index]["tool"] = _self.get('flowgraph','asicflow',step,str(index),'tool') 
        nodes[step+index]["architecture"]= _self.get('record', 'arch', step=step, index=index) 
        nodes[step+index]["distro"] = _self.get('record', 'distro', step=step, index=index)
        nodes[step+index]["starttime"] = _self.get('record', 'starttime', step=step, index=index)
        nodes[step+index]["endtime"]= _self.get('record', 'endtime', step=step, index=index)
        nodes[step+index]["scversion"] = _self.get('record', 'scversion', step=step, index=index)
        nodes[step+index]["toolargs"] = _self.get('record', 'toolargs', step=step, index=index)
        nodes[step+index]["toolpath"] = _self.get('record', 'toolpath', step=step, index=index)
        nodes[step+index]["toolversion"] = _self.get('record', 'toolversion', step=step, index=index)
        nodes[step+index]["userid"] = _self.get('record', 'userid', step=step, index=index)

    return pd.DataFrame.from_dict(nodes, orient='index')

################################

def makeDependencies(self):

    dependenciesDict = {}

    flow = self.get('option', 'flow')

    for step in self.getkeys('flowgraph', flow):
        for index in self.getkeys('flowgraph', flow, step):
            node = f'{step}{index}'
            dependenciesDict[node] = []
            # get inputs
            all_inputs = []
            for in_step, in_index in self.get('flowgraph', flow, step, index, 'input'):
                all_inputs.append(in_step + in_index)
            for item in all_inputs:
                dependenciesDict[node].append(item)
    return dependenciesDict

################################

def get_nodes_and_edges(nodeDependencies):
    nodes = []
    edges = []
    for key in nodeDependencies :
        nodes.append( 
                Node(id=key,
                    label=key
                    )
                )
        for node in nodeDependencies[key] :
            edges.append( 
                    Edge(source=node, 
                    dir='back', 
                    target=key, ) 
                    )
    return nodes[::-1], edges

################################

def getAllPaths(self): 
    allPaths = []
    allkeys = self.allkeys()
    for key in allkeys:
        for value, step, index in self.schema._getvals(*key):
            keyCopy = key.copy()
            if step is None and index is None:
                pass
            elif index is None:
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

def makeFileTreeRecHelper(currTree, currTreeNode, remainingTreeNodes): #good
    if len(remainingTreeNodes) == 1:
        currTree[currTreeNode] = remainingTreeNodes[0]
        return currTree
    else:
        if currTreeNode in currTree :
            currTree[currTreeNode] = makeFileTreeRecHelper(currTree[currTreeNode],
                                                        remainingTreeNodes[0], 
                                                        remainingTreeNodes[1:])
        else:
            currTree[currTreeNode] = makeFileTreeRecHelper({},
                                                        remainingTreeNodes[0], 
                                                        remainingTreeNodes[1:])
        return currTree
    
################################

@streamlit.cache_data 
def makeFileTree(_self): 
    manifestTree = {}
    allPaths = getAllPaths(_self)
    for path in allPaths :
        makeFileTreeRecHelper(manifestTree, 
                              path[0], 
                              path[1:])
    return manifestTree

################################

def getLogsAndReportsRecHelper(pathName, duplicateFiles):
    files = os.listdir(pathName)
    logsReportsTree = []
    nonFolders = []
    for file in files :
        if file in duplicateFiles :
            continue
        else:
            duplicateFiles.add(file)
        if os.path.isfile(f'{pathName}/{file}'):
            nonFolders.append(file)
        else:
            node = {}
            node["label"] = file
            node["value"] = file
            node["children"] = getLogsAndReportsRecHelper(f'{pathName}/{file}', duplicateFiles)
            logsReportsTree.append(node)
    for file in nonFolders :
        node = {}
        node["label"] = file
        node["value"] = file
        logsReportsTree.append(node)
    return logsReportsTree

################################

@streamlit.cache_data
def getLogsAndReports(pathName):
    fileNames = os.listdir(pathName)
    logsReportsTree = {}
    for step in fileNames :
        if os.path.isdir(f'{pathName}/{step}'):
            runs = os.listdir(f'{pathName}/{step}')
            for index in runs :
                if os.path.isdir(f'{pathName}/{step}/{index}'):
                    logsReportsTree[step+index] = getLogsAndReportsRecHelper(f'{pathName}/{step}/{index}', set())
    return logsReportsTree

################################

#gathering data
design = 'zerosoc'
pathName = f'build/{design}/job0'
logsAndReportsDict = getLogsAndReports(pathName) # does not allow duplicate files
chip = core.Chip(design=design)
chip.read_manifest(f'build/{design}/job0/{design}.pkg.json')
metricDf = makeList(chip)
nodesRecordDf = get_flowgraph_tasks(chip, metricDf.columns.tolist()) 
manifestTree = makeFileTree(chip)

################################

streamlit.title('Semi-Conductor Metrics')

col1, col2 = streamlit.columns([0.4, 0.6], gap="large")

with col1:
    streamlit.header('Flowgraph')

    config = Config(width=200,
                height=400,
                directed=True, 
                physics=True, 
                hierarchical=True,
                )

    nodes, edges = get_nodes_and_edges(makeDependencies(chip))

    return_value = agraph(
        nodes=nodes,
        edges=edges,
        config=config
    )

with col2:
    streamlit.header('Data Metrics')

    data = metricDf

    options = {'cols' : data.columns.tolist(), 'rows' : data.index.tolist()}

    container = streamlit.container()
    # streamlit.dataframe(data.loc[options['rows'], options['cols']].style.applymap(color_success, subset=data.index.tolist()))

    with streamlit.expander("Select Parameters"):
        with streamlit.form("params"):
            options['cols'] = streamlit.multiselect(
            'Which columns to include?',
            data.columns.tolist(),
            [])

            options['rows'] = streamlit.multiselect(
            'Which rows to include?',
            data.index.tolist(),
            [])

            params_submitted = streamlit.form_submit_button("Run")

    if options['cols'] == [] or options ['rows'] == []:
        options = {'cols' : data.columns.tolist(), 'rows' : data.index.tolist()}

    container.dataframe((data.loc[options['rows'], options['cols']]), use_container_width=True)

    # .style.apply(backgroundColor, axis=1)

col1, col2 = streamlit.columns([0.3, 0.7], gap="large")

with col1:
    streamlit.header('Manifest Tree')

    streamlit.json(manifestTree, expanded=False)

with col2:
    streamlit.header('Node Information')

    option = metricDf.columns.tolist()[0]

    col1, col2, col3 = streamlit.columns(3, gap='small')

    with streamlit.expander("Select Node"):
        with streamlit.form("nodes"):
            option = streamlit.selectbox( 'Which Node would you like to inspect?', 
                                    metricDf.columns.tolist())

            params_submitted = streamlit.form_submit_button("Run")
    
    if return_value != None :
        option = return_value
    
    with col1:
        streamlit.dataframe((metricDf[option].T), use_container_width=True)

    with col2:
        streamlit.dataframe((nodesRecordDf.loc[option]), use_container_width=True) 

    with col3:
        streamlit.caption(option)
        tree_select(logsAndReportsDict[option], expand_on_click=True)

################################