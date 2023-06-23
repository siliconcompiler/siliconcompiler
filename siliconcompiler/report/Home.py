import streamlit
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select
from streamlit_toggle import st_toggle_switch
from PIL import Image
import report
import os
import sys
sys.path.append('..')
import core

successColor = '#8EA604' #green
pendingColor = '#F5BB00' #yellow, could use: #EC9F05
failureColor = '#FF4E00' #red

streamlit.set_page_config(page_title="SiliconCompiler",
                          page_icon=Image.open("SCLogo.png"),
                          layout="wide")

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
chip = core.Chip(design='')
# chip.read_manifest('build/heartbeat/job0/heartbeat.pkg.json')
chip.read_manifest('build/zerosoc/job0/zerosoc.pkg.json')


@streamlit.cache_data
def gatherData():
    dataDf = report.make_list(chip)
    nodesRecordDf = report.get_flowgraph_tasks(chip, dataDf.columns.tolist()) 
    logsAndReportsDict = report.get_logs_and_reports(chip, dataDf.columns.tolist()) 
    dataDf.columns = dataDf.columns.map(lambda x: f'{x[0]}{x[1]}')
    nodesRecordDf.index = nodesRecordDf.index.map(lambda x: f'{x[0]}{x[1]}')
    nodes, edges = get_nodes_and_edges(report.make_dependencies(chip), report.get_path(chip))
    manifest = report.make_manifest(chip)
    return dataDf, nodesRecordDf, logsAndReportsDict, nodes, edges, manifest

dataDf, nodesRecordDf, logsAndReportsDict, nodes, edges, manifest = gatherData()
################################

if 'flowgraph' not in streamlit.session_state:
    streamlit.session_state['flowgraph'] = True

col1, col2 = streamlit.columns([0.7, 0.3], gap="large")

with col1:
    streamlit.title(f'{chip.design} Metrics')

with col2:
    job = streamlit.selectbox('', chip.schema.cfg['history']) 

#these need to be global variables since they are being accessed in different panels
displayFileContent = False
fileContent = ''

if os.path.isfile(f'{chip._getworkdir()}/{chip.design}.png'):
    tab1, tab2, tab3, tab4 = streamlit.tabs(["Metrics", "Manifest", "File Preview", "Design Preview"])
    with tab4:
        streamlit.header('Design Preview')

        streamlit.image(f'{chip._getworkdir()}/{chip.design}.png')
else:
     tab1, tab2, tab3 = streamlit.tabs(["Metrics", "Manifest", "File Preview"])

with tab1:
    if streamlit.session_state['flowgraph']:
        col1, col2 = streamlit.columns([0.4, 0.6], gap="large")

        with col1:
            headerCol, toggleCol = streamlit.columns([0.7, 0.3], gap="large")
            with headerCol:
                streamlit.header('Flowgraph')
            
            with toggleCol:
                streamlit.markdown("\n")
                streamlit.session_state['flowgraph'] = st_toggle_switch(label="",
                                                                            key="switch_2",
                                                                            default_value=True,
                                                                            label_after=False,
                                                                            inactive_color="#D3D3D3",  # optional
                                                                            active_color="#11567f",  # optional
                                                                            track_color="#29B5E8",  # optional
                                                                        )
                if not streamlit.session_state['flowgraph']:
                    streamlit.experimental_rerun()

            config = Config(width='100%', #need to update dynamically, could use number of attributes displayed + offset
                            directed=True, 
                            physics=False, 
                            hierarchical=True,
                            clickToUse=True,
                            nodeSpacing =175,
                            levelSeparation=250,
                            sortMethod='directed'
                            )

            

            return_value = agraph(
                nodes=nodes,
                edges=edges,
                config=config
            )
            
    else:
        col1, col2 = streamlit.columns([0.1, 0.9], gap="large")
        
        with col1:
            streamlit.markdown("\n")
            streamlit.session_state['flowgraph'] = st_toggle_switch(label="",
                                                                        key="switch_2",
                                                                        default_value=False,
                                                                        label_after=False,
                                                                        inactive_color="#D3D3D3",  # optional
                                                                        active_color="#11567f",  # optional
                                                                        track_color="#29B5E8",  # optional
                                                                    )
            if streamlit.session_state['flowgraph']:
                streamlit.experimental_rerun()
            
            return_value = None

    with col2:
        headerCol, transposeCol = streamlit.columns([0.7, 0.3], gap="large")

        transpose = False

        with headerCol:
            streamlit.header('Data Metrics')

        with transposeCol:
            streamlit.markdown("\n")
            transpose = st_toggle_switch(label="Transpose",
                                            key="switch_1",
                                            default_value=False,
                                            label_after=False,
                                            inactive_color="#D3D3D3",  # optional
                                            active_color="#11567f",  # optional
                                            track_color="#29B5E8",  # optional
                                        )

        if transpose:
            dataDf = dataDf.transpose()
        
        #data manipulation
        displayToData = {}
        displayOptions = []

        if transpose:
            for metric, unit in dataDf.columns.tolist():
                displayToData[metric] = (metric, unit)
                displayOptions.append(metric)
        else:
            for metric, unit in dataDf.index.tolist():
                displayToData[metric] = (metric, unit)
                displayOptions.append(metric)

        options = {'cols' : dataDf.columns.tolist(), 'rows' : dataDf.index.tolist()}

        container = streamlit.container()

        with streamlit.expander("Select Parameters"):
            with streamlit.form("params"):
                if transpose:
                    options['rows'] = streamlit.multiselect(
                    'Which nodes to include?',
                    dataDf.index.tolist(),
                    [])

                    metrics = streamlit.multiselect(
                    'Which metrics to include?',
                    displayOptions,
                    [])
                    options['cols'] = []
                    for metric in metrics:
                        options['cols'].append(displayToData[metric])
                else:
                    options['cols'] = streamlit.multiselect(
                    'Which nodes to include?',
                    dataDf.columns.tolist(),
                    [])

                    metrics = streamlit.multiselect(
                    'Which metrics to include?',
                    displayOptions,
                    [])
                    options['rows'] = []
                    for metric in metrics:
                        options['rows'].append(displayToData[metric])

                params_submitted = streamlit.form_submit_button("Run")

        if options['cols'] == [] or options ['rows'] == []:
            options = {'cols' : dataDf.columns.tolist(), 'rows' : dataDf.index.tolist()}

        if transpose:
            to_show = (dataDf.loc[options['rows'], options['cols']]).copy(deep=True)
            to_show.columns = to_show.columns.map(lambda x: x[0] + "    " + x[1] if x[1] else x[0])
            container.dataframe(to_show, use_container_width=True)
        else:
            container.dataframe((dataDf.loc[options['rows'], options['cols']]), 
                                use_container_width=True)

        ############################################################################

        streamlit.header('Node Information')

        if transpose: # if data is tranposed, tranpose data back
            dataDf = dataDf.transpose()

        option = dataDf.columns.tolist()[0] 

        col1, col2, col3 = streamlit.columns(3, gap='small')

        with streamlit.expander("Select Node"):
            with streamlit.form("nodes"):
                option = streamlit.selectbox('Which Node would you like to inspect?', 
                                                dataDf.columns.tolist()) 

                params_submitted = streamlit.form_submit_button("Run")
                if not params_submitted and return_value != None:
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


with tab2:
    streamlit.header('Manifest Tree')

    col1A, col2A = streamlit.columns([0.5, 0.5], gap="large")

    with col1A:
        key = streamlit.text_input('Search Keys', '', placeholder="Keys")
        if key != '':
            manifest = report.search_manifest(manifest, key_search=key)

    with col2A:
        value = streamlit.text_input('Search Values', '', placeholder="Values")
        if value != '':
            manifest = report.search_manifest(manifest, value_search=value)
    
    numOfKeys = report.manifest_key_counter(manifest)

    streamlit.json(manifest, expanded=numOfKeys<20)

with tab3:
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
    else:
        streamlit.error('Select a file in the metrics tab first!')
    
################################