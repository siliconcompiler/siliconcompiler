#>> streamlit run Home.py

import streamlit
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select
from PIL import Image
import report
import sys
sys.path.append('..')
import core

################################

def get_nodes_and_edges(nodeDependencies, successfulPath):
    nodes = []
    edges = []
    for step, index in nodeDependencies :
        style = 'solid'
        nodeColor = 'blue'
        if (step, index) in successfulPath :
            style = 'bold'
            if successfulPath[step, index] != None :
                nodeColor = 'green'
        nodes.append( 
                Node(id=f"({step}, {index})", #must be string, identification is string of tuple
                    label=step+index,
                    color=nodeColor,
                    style=style
                    )
                )
        for sourceStep, sourceIndex in nodeDependencies[step, index] :
            style='solid'
            if (sourceStep, sourceIndex) in successfulPath and (sourceStep, sourceIndex) in successfulPath:
                style='bold'
            edges.append( 
                    Edge(source=f"({sourceStep}, {sourceIndex})", 
                    dir='back', 
                    target=f"({step}, {index})", 
                    style=style
                    ) 
                    )
    return nodes[::-1], edges #reversed() doesn't work, breaks code

################################

#gathering data
chip = core.Chip(design='zerosoc')
streamlit.set_page_config(page_title="SiliconCompiler",
                          page_icon=Image.open("SCLogo.png"),
                          layout="wide")
chip.read_manifest(chip._getworkdir() + f'/{chip.design}.pkg.json')
dataDf = report.makeList(chip)
manifestTree = report.makeManifest(chip)
nodesRecordDf = report.get_flowgraph_tasks(chip, dataDf.columns.tolist()) 
logsAndReportsDict = report.getLogsAndReports(chip, dataDf.columns.tolist()) 
dataDf.columns = dataDf.columns.map(lambda x: f'{x[0]}{x[1]}')
nodesRecordDf.index = nodesRecordDf.index.map(lambda x: f'{x[0]}{x[1]}')

################################

streamlit.title(f'{chip.design} Metrics')

col1, col2 = streamlit.columns([0.4, 0.6], gap="large")

with col1:
    streamlit.header('Flowgraph')

    config = Config(width=200,
                height=400,
                directed=True, 
                physics=True, 
                hierarchical=True,
                )

    nodes, edges = get_nodes_and_edges(report.makeDependencies(chip), report.getPath(chip))

    return_value = agraph(
        nodes=nodes,
        edges=edges,
        config=config
    )

with col2:
    streamlit.header('Data Metrics')

    options = {'cols' : dataDf.columns.tolist(), 'rows' : dataDf.index.tolist()}

    container = streamlit.container()

    with streamlit.expander("Select Parameters"):
        with streamlit.form("params"):
            options['cols'] = streamlit.multiselect(
            'Which columns to include?',
            dataDf.columns.tolist(),
            [])

            options['rows'] = streamlit.multiselect(
            'Which rows to include?',
            dataDf .index.tolist(),
            [])

            params_submitted = streamlit.form_submit_button("Run")

    if options['cols'] == [] or options ['rows'] == []:
        options = {'cols' : dataDf .columns.tolist(), 'rows' : dataDf .index.tolist()}

    container.dataframe((dataDf.loc[options['rows'], options['cols']]), use_container_width=True)

col1, col2 = streamlit.columns([0.3, 0.7], gap="large")

with col1:
    streamlit.header('Manifest Tree')

    streamlit.json(manifestTree, expanded=False)

with col2:
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
        streamlit.dataframe((nodesRecordDf.loc[option]), use_container_width=True) 

    with col3:
        streamlit.caption(option)

        #not working yet
        displayLogsAndReports = {}
        # displayToDataDict = {}
        for step, index in logsAndReportsDict:
            # displayToDataDict[step+index] = (step, index)
            displayLogsAndReports[step+index] = logsAndReportsDict[step, index]
        selected = tree_select(displayLogsAndReports[option], 
                               expand_on_click=True, 
                               only_leaf_checkboxes=True)
        # step, index = displayToDataDict[option]
        if selected["checked"] != [] :
            with open(selected["checked"][0], 'r') as file:
                content = file.read() 
            streamlit.download_button( label="Download file",
                                        data=content,
                                        mime='text')

################################