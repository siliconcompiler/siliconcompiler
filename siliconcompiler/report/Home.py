#>> streamlit run Home.py

import streamlit
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select
from PIL import Image
import report
import os
import sys
sys.path.append('..')
import core

successColor = '#8EA604' #green
pendingColor = '#F5BB00' #yellow, could use: #EC9F05
failureColor = '#FF4E00' #red

################################

def get_nodes_and_edges(nodeDependencies, successfulPath):
    nodes = []
    edges = []
    for step, index in nodeDependencies :
        opacity = 0.2
        width = 1
        if (step, index) in successfulPath :
            opacity = 1
            if successfulPath[step, index] != None :
                width = 3

        flow = chip.get("option", "flow")
        taskStatus = chip.get('flowgraph', flow, step, index, 'status')
        if  taskStatus == core.TaskStatus.SUCCESS :
            nodeColor = successColor
        elif taskStatus == core.TaskStatus.ERROR :
            nodeColor = failureColor
        else:
            nodeColor = pendingColor

        tool, task = chip._get_tool_task(step, index)
        label = step+index+"\n"+tool+"/"+task
        if chip._is_builtin(tool, task):
            label=step+index+"\n"+tool
        
        nodes.append( 
                Node(id=step+index,
                    label=label,
                    color=nodeColor,
                    opacity=opacity,
                    borderWidth=width,
                    shape='oval'
                    )
                )

        for sourceStep, sourceIndex in nodeDependencies[step, index] :
            width = 3
            if (sourceStep, sourceIndex) in successfulPath and (sourceStep, sourceIndex) in successfulPath:
                width = 5
            edges.append( 
                    Edge(source=sourceStep+sourceIndex,
                    dir='up', 
                    target=step+index, 
                    width=width,
                    color='black',
                    curve=True
                    ) 
                    )

    return nodes, edges 
################################

#gathering data
# manifest = '../..//.././.json'
# chip = core.Chip(design='<design>')
# chip.read_manifest(manifest)
chip = core.Chip(design='')
# chip.read_manifest('build/heartbeat/job0/heartbeat.pkg.json')
# chip.read_manifest('build/zerosoc/job0/zerosoc.pkg.json')
chip.read_manifest('build/gcd/job0/gcd.pkg.json')
dataDf = report.makeList(chip)
manifestTree = report.makeManifest(chip)
nodesRecordDf = report.get_flowgraph_tasks(chip, dataDf.columns.tolist()) 
logsAndReportsDict = report.getLogsAndReports(chip, dataDf.columns.tolist()) 
dataDf.columns = dataDf.columns.map(lambda x: f'{x[0]}{x[1]}')
nodesRecordDf.index = nodesRecordDf.index.map(lambda x: f'{x[0]}{x[1]}')

################################

streamlit.set_page_config(page_title="SiliconCompiler",
                          page_icon=Image.open("SCLogo.png"),
                          layout="wide")

streamlit.title(f'{chip.design} Metrics')

#these need to be global variables since they are being accessed in different panels
displayFileContent = False
fileContent = ''

col1, col2 = streamlit.columns([0.4, 0.6], gap="large")

with col1:
    streamlit.header('Flowgraph')

    config = Config(width='100%', #need to update dynamically, could use number of attributes displayed + offset
                    directed=True, 
                    physics=False, 
                    hierarchical=True,
                    clickToUse=True,
                    nodeSpacing =175,
                    levelSeparation=250,
                    sortMethod='directed'
                    )

    nodes, edges = get_nodes_and_edges(report.makeDependencies(chip), report.getPath(chip))

    return_value = agraph(
        nodes=nodes,
        edges=edges,
        config=config
    )

with col2:
    #data manipulation
    displayToData = {}
    displayOptions = []
    for metric, unit in dataDf.index.tolist():
        displayToData[metric] = (metric, unit)
        displayOptions.append(metric)
    
    streamlit.header('Data Metrics')

    options = {'cols' : dataDf.columns.tolist(), 'rows' : dataDf.index.tolist()}

    container = streamlit.container()

    with streamlit.expander("Select Parameters"):
        with streamlit.form("params"):
            options['cols'] = streamlit.multiselect(
            'Which columns to include?',
            dataDf.columns.tolist(),
            [])

            metrics = streamlit.multiselect(
            'Which rows to include?',
            displayOptions,
            [])
            options['rows'] = []
            for metric in metrics:
                options['rows'].append(displayToData[metric])

            params_submitted = streamlit.form_submit_button("Run")

    if options['cols'] == [] or options ['rows'] == []:
        options = {'cols' : dataDf.columns.tolist(), 'rows' : dataDf.index.tolist()}
    

    

    container.dataframe((dataDf.loc[options['rows'], options['cols']]), 
                        use_container_width=True)

    ############################################################################

    streamlit.header('Node Information')

    option = dataDf.columns.tolist()[0]

    col1, col2, col3 = streamlit.columns(3, gap='small')

    with streamlit.expander("Select Node"):
        with streamlit.form("nodes"):
            option = streamlit.selectbox( 'Which Node would you like to inspect?', 
                                    dataDf.columns.tolist())

            params_submitted = streamlit.form_submit_button("Run")
    
    if return_value != None :
        option = return_value
    
    with col1:
        streamlit.dataframe(dataDf[option].T.dropna(), use_container_width=True)

    with col2:
        streamlit.dataframe(nodesRecordDf.loc[option].dropna(), use_container_width=True) 

    with col3:
        streamlit.caption(option)

        #converts from data formatting to display format
        displayLogsAndReports = {}
        for step, index in logsAndReportsDict:
            displayLogsAndReports[step+index] = logsAndReportsDict[step, index]

        selected = tree_select(displayLogsAndReports[option], 
                               expand_on_click=True, 
                               only_leaf_checkboxes=True)

        if selected["checked"] != [] :
            displayFileContent = True
            index = 0

            #searches for the first file selected in order of tree
            while os.path.isdir(selected["checked"][index]):
                index += 1
            path = selected["checked"][index]
            file_name, file_extension = os.path.splitext(path)
            streamlit.download_button(label=f"Download file",
                                    data=path,
                                    file_name=path[path.rfind("/"):])
            

col1, col2, col3 = streamlit.columns([0.4, 0.3, 0.3], gap="large")

with col1:
    streamlit.header('Manifest Tree')

    col1A, col2A = streamlit.columns([0.5, 0.5], gap="large")

    manifest = report.makeManifest(chip)

    with col1A:
        key = streamlit.text_input('Search Keys', '', placeholder="Keys")
        if key != '':
            manifest = report.searchManifest(manifest, keySearch=key)

    with col2A:
        value = streamlit.text_input('Search Values', '', placeholder="Values")
        if value != '':
            manifest = report.searchManifest(manifest, valueSearch=value)
    
    numOfKeys = report.manifestKeyCounter(manifest)

    streamlit.json(manifest, expanded=numOfKeys<20)

with col2:
    if os.path.isfile(f'{chip._getworkdir()}/{chip.design}.png'):
        streamlit.header('Design Preview')

        streamlit.image(f'{chip._getworkdir()}/{chip.design}.png')

with col3:
    if displayFileContent:
        streamlit.header('File Preview')
        
        if file_extension == ".png":
            streamlit.image(path)
        else:
            with open(path, 'r') as file:
                content = file.read()
            if file_extension == ".json":
                streamlit.json(content)
            else:
                streamlit.code(content, language='markdwon', line_numbers=True)
    
################################