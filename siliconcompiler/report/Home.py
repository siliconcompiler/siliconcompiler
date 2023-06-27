import streamlit
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select
from streamlit_toggle import st_toggle_switch
from PIL import Image
import report
import os
import pandas
from siliconcompiler import core


successColor = '#8EA604'  # green
pendingColor = '#F5BB00'  # yellow, could use: #EC9F05
failureColor = '#FF4E00'  # red

streamlit.set_page_config(page_title="SiliconCompiler",
                          page_icon=Image.open("SCLogo.png"),
                          layout="wide")


def get_nodes_and_edges(node_dependencies, successful_path):
    """
    Returns the nodes and edges required to make a streamlit_agraph.

    Args:
        node_dependencies (dict) : dictionary where the values of the keys are
                                   the edges
        successful_path (set) : contains all the nodes that are part of the
                                'winning' path
    """
    nodes = []
    edges = []
    for step, index in node_dependencies:
        opacity = 0.2
        width = 1
        if (step, index) in successful_path:
            opacity = 1
            if (step, index) in chip._get_flowgraph_exit_nodes() or \
               (step, index) in chip._get_flowgraph_entry_nodes():
                width = 3

        flow = chip.get("option", "flow")
        taskStatus = chip.get('flowgraph', flow, step, index, 'status')
        if taskStatus == core.TaskStatus.SUCCESS:
            nodeColor = successColor
        elif taskStatus == core.TaskStatus.ERROR:
            nodeColor = failureColor
        else:
            nodeColor = pendingColor

        tool, task = chip._get_tool_task(step, index)
        label = step+index+"\n"+tool+"/"+task
        if chip._is_builtin(tool, task):
            label = step+index+"\n"+tool

        nodes.append(Node(id=step+index,
                          label=label,
                          color=nodeColor,
                          opacity=opacity,
                          borderWidth=width,
                          shape='oval'))

        for sourceStep, sourceIndex in node_dependencies[step, index]:
            width = 3
            if (sourceStep, sourceIndex) in successful_path and \
               (sourceStep, sourceIndex) in successful_path:
                width = 5
            edges.append(Edge(source=sourceStep+sourceIndex,
                              dir='up',
                              target=step+index,
                              width=width,
                              color='black',
                              curve=True))

    return nodes, edges


def show_file_preview(display_file_content, file_extension, path):
    """
    Displays the file_preview if present. If not, displays an error message.

    Args:
        displau_file_content (bool) : boolean representing if we should (true)
                                      or should not (false) display content
        file_extension (string) : string of file_extension (i.e., .png)
        path (string) : the path is the file path to the file
    """
    if display_file_content:
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


def show_logs_reports(step, index):
    """
    Displays the logs and reports using streamlit_tree_select

    Args:
        step (string) : step of node
        index (string) : index of node
    """
    streamlit.caption(step+index)

    logs_and_reports = report.get_logs_and_reports(new_chip, step, index)

    selected = tree_select(logs_and_reports,
                           expand_on_click=True,
                           only_leaf_checkboxes=True)

    display_file_content = False

    if selected["checked"] != []:
        display_file_content = True
        file_position = 0

        # searches for the first file selected in order of tree
        while os.path.isdir(selected["checked"][file_position]):
            file_position += 1
        path = selected["checked"][file_position]
        file_name, file_extension = os.path.splitext(path)
        streamlit.download_button(label="Download file",
                                  data=path,
                                  file_name=path[path.rfind("/"):])

        return file_extension, path, display_file_content
    return None, None, display_file_content


def show_manifest(manifest):
    """
    Displays the logs and reports using streamlit_tree_select

    Args:
        step (string) : step of node
        index (string) : index of node
    """
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

    numOfKeys = report.get_total_manifest_parameter_count(manifest)

    streamlit.json(manifest, expanded=numOfKeys < 20)


def select_nodes(metric_dataframe, return_value):
    if streamlit.session_state['transpose']:
        # if data is tranposed, tranpose data back
        metric_dataframe = metric_dataframe.transpose()

    option = metric_dataframe.columns.tolist()[0]

    with streamlit.expander("Select Node"):
        with streamlit.form("nodes"):
            option = streamlit.selectbox('Pick a node to inspect',
                                         metric_dataframe.columns.tolist())

            params_submitted = streamlit.form_submit_button("Run")
            if not params_submitted and return_value is not None:
                option = return_value
    return option


def show_dataframe_and_parameter_selection(metric_dataframe):
    container = streamlit.container()

    transpose = streamlit.session_state['transpose']

    if transpose:
        metric_dataframe = metric_dataframe.transpose()

    # pick parameters
    displayToData = {}
    displayOptions = []

    if transpose:
        for metric, unit in metric_dataframe.columns.tolist():
            displayToData[metric] = (metric, unit)
            displayOptions.append(metric)
    else:
        for metric, unit in metric_dataframe.index.tolist():
            displayToData[metric] = (metric, unit)
            displayOptions.append(metric)

    options = {'cols': metric_dataframe.columns.tolist(),
               'rows': metric_dataframe.index.tolist()}

    with streamlit.expander("Select Parameters"):
        with streamlit.form("params"):
            if transpose:
                nodes = streamlit.multiselect('Pick nodes to include',
                                              metric_dataframe.index.tolist(),
                                              [])
                options['rows'] = nodes

                metrics = streamlit.multiselect('Pick metrics to include?',
                                                displayOptions,
                                                [])
                options['cols'] = []
                for metric in metrics:
                    options['cols'].append(displayToData[metric])
            else:
                display_dataframe = metric_dataframe.columns.tolist()
                nodes = streamlit.multiselect('Pick nodes to include',
                                              display_dataframe,
                                              [])
                options['cols'] = nodes

                metrics = streamlit.multiselect('Which metrics to include?',
                                                displayOptions,
                                                [])
                options['rows'] = []
                for metric in metrics:
                    options['rows'].append(displayToData[metric])

            streamlit.form_submit_button("Run")

    if options['cols'] == [] or options['rows'] == []:
        options = {'cols': metric_dataframe.columns.tolist(),
                   'rows': metric_dataframe.index.tolist()}

    # showing the dataframe
    if transpose:
        to_show = (metric_dataframe.loc[options['rows'],
                   options['cols']]).copy(deep=True)
        to_show.columns = to_show.columns.map(lambda x: x[0] + "    " +
                                              x[1] if x[1] else x[0])
        container.dataframe(to_show, use_container_width=True)
    else:
        container.dataframe((metric_dataframe.loc[options['rows'],
                                                  options['cols']]),
                            use_container_width=True)


def show_dataframe_header():
    headerCol, transposeCol = streamlit.columns([0.7, 0.3], gap="large")

    with headerCol:
        streamlit.header('Data Metrics')

    with transposeCol:
        streamlit.markdown("\n")
        if 'transpose' not in streamlit.session_state:
            streamlit.session_state['transpose'] = False
            transpose = st_toggle_switch(label="Transpose",
                                         key="switch_1",
                                         default_value=False,
                                         label_after=False,
                                         inactive_color="#D3D3D3",  # optional
                                         active_color="#11567f",  # optional
                                         track_color="#29B5E8",  # optional
                                         )
            streamlit.session_state['transpose'] = transpose


def show_flowgraph():
    col1, col2 = streamlit.columns([0.4, 0.6], gap="large")

    with col1:
        headerCol, toggleCol = streamlit.columns([0.7, 0.3], gap="large")
        with headerCol:
            streamlit.header('Flowgraph')

        with toggleCol:
            streamlit.markdown("\n")
            flowgraph_toggle = st_toggle_switch(label="",
                                                key="switch_2",
                                                default_value=True,
                                                label_after=False,
                                                inactive_color="#D3D3D3",
                                                active_color="#11567f",
                                                track_color="#29B5E8",
                                                )
            streamlit.session_state['flowgraph'] = flowgraph_toggle

            if not streamlit.session_state['flowgraph']:
                streamlit.experimental_rerun()

        # need to update dynamically, could use number of attributes displayed
        # + offset
        config = Config(width='100%',
                        directed=True,
                        physics=False,
                        hierarchical=True,
                        clickToUse=True,
                        nodeSpacing=150,
                        levelSeparation=100,
                        sortMethod='directed')

        return_value = agraph(nodes=nodes,
                              edges=edges,
                              config=config)
    return return_value, col2


def dont_show_flowgraph():
    col1, col2 = streamlit.columns([0.1, 0.9], gap="large")

    with col1:
        streamlit.markdown("\n")
        flowgraph_toggle = st_toggle_switch(label="",
                                            key="switch_2",
                                            default_value=False,
                                            label_after=False,
                                            inactive_color="#D3D3D3",
                                            active_color="#11567f",
                                            track_color="#29B5E8")

        streamlit.session_state['flowgraph'] = flowgraph_toggle
        if streamlit.session_state['flowgraph']:
            streamlit.experimental_rerun()

    return None, col2


col1, col2 = streamlit.columns([0.7, 0.3], gap="large")

if 'job' not in streamlit.session_state:
    chip = core.Chip(design='')
    # chip.read_manifest('build/heartbeat/job0/heartbeat.pkg.json')
    # chip.read_manifest('build/zerosoc/job0/zerosoc.pkg.json')
    chip.read_manifest('build/gcd/job0_optimize_9/gcd.pkg.json')
    new_chip = chip
    streamlit.session_state['master chip'] = chip
else:
    chip = streamlit.session_state['master chip']
    new_chip = core.Chip(design='')
    job = streamlit.session_state['job']
    new_chip.schema = chip.schema.history(job)

    # remove once bug is fixed
    new_chip.set('design', chip.design)

with col1:
    streamlit.title(f'{new_chip.design} Metrics')

with col2:
    all_jobs = streamlit.session_state['master chip'].getkeys('history')
    job = streamlit.selectbox('', all_jobs)
    streamlit.session_state['job'] = job

# gathering data
metric_dataframe = report.make_metric_dataframe(new_chip)

# create mapping between task and step, index
task_map_to_step_index = {}
for step, index in metric_dataframe.columns.tolist():
    task_map_to_step_index[step+index] = (step, index)

# concatenate step and index
metric_dataframe.columns = metric_dataframe.columns.map(lambda x:
                                                        f'{x[0]}{x[1]}')
nodes, edges = get_nodes_and_edges(report.get_flowgraph_edges(new_chip),
                                   report.get_flowgraph_path(new_chip))
manifest = report.make_manifest(new_chip)

if 'flowgraph' not in streamlit.session_state:
    streamlit.session_state['flowgraph'] = True

if os.path.isfile(f'{new_chip._getworkdir()}/{new_chip.design}.png'):
    tab1, tab2, tab3, tab4 = streamlit.tabs(["Metrics",
                                             "Manifest",
                                             "File Preview",
                                             "Design Preview"])
    with tab4:
        streamlit.header('Design Preview')

        streamlit.image(f'{new_chip._getworkdir()}/{new_chip.design}.png')
else:
    tab1, tab2, tab3 = streamlit.tabs(["Metrics", "Manifest", "File Preview"])

with tab1:
    if streamlit.session_state['flowgraph']:
        return_value, col2 = show_flowgraph()
    else:
        return_value, col2 = dont_show_flowgraph()

    with col2:
        show_dataframe_header()

        show_dataframe_and_parameter_selection(metric_dataframe)

        streamlit.header('Node Information')

        col1, col2, col3 = streamlit.columns(3, gap='small')

        option = select_nodes(metric_dataframe, return_value)

        with col1:  # not dropping None
            streamlit.dataframe(metric_dataframe[option].dropna().transpose(),
                                use_container_width=True)

        with col2:
            step, index = task_map_to_step_index[option]
            nodes = {}
            nodes[step+index] = report.get_flowgraph_nodes(chip, step, index)
            node_reports = pandas.DataFrame.from_dict(nodes)
            streamlit.dataframe(node_reports.dropna(),
                                use_container_width=True)

        with col3:
            step, index = task_map_to_step_index[option]
            file_ext, path, display_file_content = show_logs_reports(step,
                                                                     index)


with tab2:
    show_manifest(manifest)

with tab3:
    show_file_preview(display_file_content, file_ext, path)
