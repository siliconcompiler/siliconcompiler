import streamlit
import pandas as pd
import siliconcompiler as sc
import units
from streamlit_agraph import agraph, Node, Edge, Config

################################

def makeList(self, steplist=None):
    #from siliconcompiler/siliconcompiler/core.py, "summary" function

    # display whole flowgraph if no steplist specified
    flow = self.get('option', 'flow')
    if not steplist: #might be redundant
        if self.get('option', 'steplist'):
            steplist = self.get('option', 'steplist')
        else:
            steplist = self.list_steps()

    # Find all tasks that are part of a "winning" path.
    selected_tasks = set()
    to_search = []

    # Successful tasks
    succesful_tasks = set()

    # Start search with any successful leaf tasks.
    leaf_tasks = self._get_flowgraph_exit_nodes(flow=flow, steplist=steplist)
    for task in leaf_tasks:
        # if self.get('flowgraph', flow, *task, 'status') == TaskStatus.SUCCESS: #need to find all tasks, not just succesful ones
        to_search.append(task)
        selected_tasks.add(task)

    # Search backwards, saving anything that was selected by leaf tasks.
    while len(to_search) > 0: #why do we search the succesful 
        task = to_search.pop(-1)
        for selected in self.get('flowgraph', flow, *task, 'select'):
            if selected not in selected_tasks:
                selected_tasks.add(selected)
                to_search.append(selected)

    # only report tool based steps functions
    for step in steplist.copy(): #will definitely need to keep
        tool, task = self._get_tool_task(step, '0', flow=flow)
        if self._is_builtin(tool, task):
            index = steplist.index(step)
            del steplist[index]

    # job directory
    jobdir = self._getworkdir() #what do I need this for?

    # Custom reporting modes
    paramlist = []
    for item in self.getkeys('option', 'param'):
        paramlist.append(item + "=" + self.get('option', 'param', item))

    if paramlist:
        paramstr = ', '.join(paramlist)
    else:
        paramstr = "None"

    info_list = ["SUMMARY:\n",
                "design : " + self.top(),
                "params : " + paramstr,
                "jobdir : " + jobdir,
                ]

    if self.get('option', 'mode') == 'asic':
        pdk = self.get('option', 'pdk')

        libraries = set()
        for val, step, _ in self.schema._getvals('asic', 'logiclib'):
            if not step or step in steplist:
                libraries.update(val)

        info_list.extend([f"foundry : {self.get('pdk', pdk, 'foundry')}",
                        f"process : {pdk}",
                        f"targetlibs : {' '.join(libraries)}"])
    elif self.get('option', 'mode') == 'fpga':
        info_list.extend([f"partname : {self.get('fpga','partname')}"])

    info = '\n'.join(info_list)

    print("-" * 135)
    print(info, "\n")

    # Collections for data
    nodes = []
    errors = {}
    metrics = {}
    metrics_unit = {}
    reports = {}

    # Build ordered list of nodes in flowgraph
    for step in steplist:
        for index in self.getkeys('flowgraph', flow, step):
            nodes.append((step, index))
            metrics[step+index] = {}
            reports[step, index] = {}

    # Gather data and determine which metrics to show
    # We show a metric if:
    # - it is not in ['option', 'metricoff'] -AND-
    # - at least one step in the steplist has a non-zero weight for the metric -OR -
    #   at least one step in the steplist set a value for it
    metrics_to_show = []
    for metric in self.getkeys('metric'):
        if metric in self.get('option', 'metricoff'):
            continue

        # Get the unit associated with the metric
        metric_unit = None
        if self.schema._has_field('metric', metric, 'unit'):
            metric_unit = self.get('metric', metric, field='unit')
        metric_type = self.get('metric', metric, field='type')

        show_metric = False
        for step, index in nodes:
            if metric in self.getkeys('flowgraph', flow, step, index, 'weight') and \
            self.get('flowgraph', flow, step, index, 'weight', metric):
                show_metric = True

            value = self.get('metric', metric, step=step, index=index)
            if value is not None:
                show_metric = True
            tool, task = self._get_tool_task(step, index, flow=flow)
            rpts = self.get('tool', tool, 'task', task, 'report', metric,
                            step=step, index=index)

            errors[step, index] = self.get('flowgraph', flow, step, index, 'status') == \
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

def get_flowgraph_tasks(self, nodeList, steplist=None):  
    # REQ : nodeList is in the form ['import0', 'syn0', ...]
    nodes = {}
    for task in nodeList:
        step, index = get_step_and_index(task)
        nodes[step+index] = {}
        nodes[step+index]["tool"] = self.get('flowgraph','asicflow',step,str(index),'tool') 
        nodes[step+index]["architecture"]= self.get('record', 'arch', step=step, index=index) 
        nodes[step+index]["distro"] = self.get('record', 'distro', step=step, index=index)
        nodes[step+index]["starttime"] = self.get('record', 'starttime', step=step, index=index)
        nodes[step+index]["endtime"]= self.get('record', 'endtime', step=step, index=index)
        nodes[step+index]["scversion"] = self.get('record', 'scversion', step=step, index=index)
        nodes[step+index]["toolargs"] = self.get('record', 'toolargs', step=step, index=index)
        nodes[step+index]["toolpath"] = self.get('record', 'toolpath', step=step, index=index)
        nodes[step+index]["toolversion"] = self.get('record', 'toolversion', step=step, index=index)
        nodes[step+index]["userid"] = self.get('record', 'userid', step=step, index=index)

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

def getAllPaths(self): #looks good
    allPaths = []
    allkeys = self.allkeys()
    for key in allkeys:
        for value, step, index in self.schema._getvals(*key):
            keyCopy = key.copy()
            if step is None and index is None:
                continue
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

def makeFileTreeRecHelper(currTree, currTreeNode, remainingTreeNodes):
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
        
def makeFileTree(self):
    manifestTree = {}
    allPaths = getAllPaths(self)
    for path in allPaths :
        makeFileTreeRecHelper(manifestTree, 
                              path[0], 
                              path[1:])
    return manifestTree

################################    

#gathering data
chip = sc.Chip(design="top")
chip.read_manifest('gcd.pkg.json')
metricDf = makeList(chip)
nodesRecordDf = get_flowgraph_tasks(chip, metricDf.columns.tolist()) 
manifestTree = makeFileTree(chip)
print(getAllPaths(chip))

################################

streamlit.set_page_config(layout="wide")

streamlit.title('Semi-Conductor Metrics')

col1, col2 = streamlit.columns([0.7, 0.3], gap="large")

with col1:
    streamlit.header('Current Report')

with col2:
    streamlit.header('History/Graphs')

col1, col2, col3 = streamlit.columns([0.3, 0.4, 0.3], gap="large")

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

    #colors data
    def color_success(val):
        color = 'green' if val in set(data.index.tolist()) else 'red' #will use to distinguish succesful vs. unsuccesful runs
        return f'background-color: {color}'

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

    container.dataframe(data.loc[options['rows'], options['cols']])

with col3:
    streamlit.header('Node Information')

    option = metricDf.columns.tolist()[0]

    col1, col2 = streamlit.columns(2, gap='small')

    with streamlit.expander("Select Node"):
        with streamlit.form("nodes"):
            option = streamlit.selectbox( 'Which Node would you like to inspect?', 
                                    metricDf.columns.tolist())

            params_submitted = streamlit.form_submit_button("Run")
    
    if return_value != None :
        option = return_value
    
    with col1:
        streamlit.dataframe((metricDf[option].T))

    with col2:
        streamlit.dataframe((nodesRecordDf.loc[option])) 

col1, col2, col3 = streamlit.columns([0.3, 0.4, 0.3], gap="large")

with col1:
    streamlit.header('Manifest Tree')

    streamlit.json(manifestTree, expanded=False)

################################