import streamlit
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select
from streamlit_toggle import st_toggle_switch
import streamlit_javascript
from PIL import Image
from pathlib import Path
import os
import argparse
import json
import pandas
import gzip
import base64
from siliconcompiler.report import report
from siliconcompiler import Chip, TaskStatus, utils
from siliconcompiler import __version__ as sc_version

# for flowgraph
SUCCESS_COLOR = '#8EA604'  # green
PENDING_COLOR = '#F5BB00'  # yellow, could use: #EC9F05
FAILURE_COLOR = '#FF4E00'  # red

# for toggle
INACTIVE_TOGGLE_COLOR = "#D3D3D3"
ACTIVE_TOGGLE_COLOR = "#11567f"
TRACK_TOGGLE_COLOR = "#29B5E8"


sc_logo_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'logo.png')

sc_font_path = \
    os.path.join(os.path.dirname(__file__), '..', 'data', 'RobotoMono', 'RobotoMono-Regular.ttf')

sc_about = [
    f"SiliconCompiler {sc_version}",
    '''A compiler framework that automates translation from source code to
     silicon.''',
    "https://www.siliconcompiler.com/",
    "https://github.com/siliconcompiler/siliconcompiler/"
]

sc_menu = {"Get help": "https://docs.siliconcompiler.com/",
           "Report a Bug":
           '''https://github.com/siliconcompiler/siliconcompiler/issues''',
           "About": "\n\n".join(sc_about)}

# opened by running command in siliconcompiler/apps/sc_dashboard.py
parser = argparse.ArgumentParser('dashboard')
parser.add_argument('cfg', nargs='?')
args = parser.parse_args()

if not args.cfg:
    raise ValueError('configuration not provided')

if 'job' not in streamlit.session_state:
    with open(args.cfg, 'r') as f:
        config = json.load(f)

    chip = Chip(design='')
    chip.read_manifest(config["manifest"])
    streamlit.set_page_config(page_title=f'{chip.design} dashboard',
                              page_icon=Image.open(sc_logo_path),
                              layout="wide",
                              menu_items=sc_menu)
    streamlit.session_state['master chip'] = chip
    streamlit.session_state['job'] = 'default'
    new_chip = chip
    streamlit.session_state['transpose'] = False
else:
    chip = streamlit.session_state['master chip']
    streamlit.set_page_config(page_title=f'{chip.design} dashboard',
                              page_icon=Image.open(sc_logo_path),
                              layout="wide",
                              menu_items=sc_menu)
    new_chip = Chip(design='')
    job = streamlit.session_state['job']
    if job == 'default':
        new_chip = chip
    else:
        new_chip.schema = chip.schema.history(job)
        new_chip.set('design', chip.design)


def _convert_filepaths(logs_and_reports):
    """
    Converts the logs_and_reports found to the structure
    required by streamlit_tree_select. Success is predicated on the order of
    logs_and_reports outlined in report.get_files.

    Args:
        logs_and_reports (list) : A list of 3-tuples with order of a path name,
            folder in the..., and files in the....
    """
    subsect_logs_and_reports = {}
    if not logs_and_reports:
        return []
    starting_path_name = logs_and_reports[0][0]
    # reverse the list to start building the tree from the leaves up
    for path_name, folders, files in reversed(logs_and_reports):
        children = []
        for folder in folders:
            children.append(subsect_logs_and_reports[folder])
        for file in files:
            node = {}
            node['label'] = file
            node['value'] = f'{path_name}/{file}'
            children.append(node)
        if starting_path_name == path_name:
            return children
        else:
            node = {}
            folder = Path(path_name).name
            node['label'] = folder
            node['value'] = path_name
            node['children'] = children
            subsect_logs_and_reports[folder] = node


def get_nodes_and_edges(chip, node_dependencies, successful_path,
                        successful_path_node_opacity=1,
                        successful_path_node_width=3,
                        successful_path_edge_width=5, default_node_opacity=0.2,
                        default_node_border_width=1, default_edge_width=3):
    """
    Returns the nodes and edges required to make a streamlit_agraph.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
        node_dependencies (dict) : Dictionary mapping nodes
            (as tuples of step/index) to their input nodes.
        successful_path (set) : Contains all the nodes that are part of the
            'winning' path.
        succesful_path_node_opacity (float) : A number between 0 and 1
            (inclusive) which represents the opacity for nodes on a succesful
            path.
        succesful_path_node_border_width (int) : A number between 0 or greater
            which represents the width for nodes on a succesful path.
        succesful_path_edge_width (int) : A number between 0 or greater which
            represents the width for edges on a succesful path.
        default_node_opacity (float) : A number between 0 and 1(inclusive)
            which represents the opacity for nodes of a node not on a
            successful path.
        default_node_border_width (int) : A number between 0 or greater
            which represents the width for nodes not on a succesful path.
        default_edge_width (int) : A number between 0 or greater which
            represents the width for edges not on a succesful path.
    """
    nodes = []
    edges = []
    for step, index in node_dependencies:
        node_opacity = default_node_opacity
        node_border_width = default_node_border_width
        if (step, index) in successful_path:
            node_opacity = successful_path_node_opacity
            if (step, index) in chip._get_flowgraph_exit_nodes() or \
               (step, index) in chip._get_flowgraph_entry_nodes():
                node_border_width = successful_path_node_width

        flow = chip.get("option", "flow")
        task_status = chip.get('flowgraph', flow, step, index, 'status')
        if task_status == TaskStatus.SUCCESS:
            node_color = SUCCESS_COLOR
        elif task_status == TaskStatus.ERROR:
            node_color = FAILURE_COLOR
        else:
            node_color = PENDING_COLOR

        tool, task = chip._get_tool_task(step, index)
        node_name = f'{step}{index}'
        label = node_name + "\n" + tool + "/" + task
        if chip._is_builtin(tool, task):
            label = node_name + "\n" + tool

        nodes.append(Node(id=node_name,
                          label=label,
                          color=node_color,
                          opacity=node_opacity,
                          borderWidth=node_border_width,
                          shape='oval'))
        for source_step, source_index in node_dependencies[step, index]:
            edge_width = default_edge_width
            if (source_step, source_index) in successful_path and \
               (source_step, source_index) in successful_path:
                edge_width = successful_path_edge_width
            edges.append(Edge(source=source_step + source_index,
                              dir='up',
                              target=node_name,
                              width=edge_width,
                              color='black',
                              curve=True))

    return nodes, edges


def show_file_viewer(chip, step, index, header_col_width=0.89):
    """
    Displays the file if present. If not, displays an error message.

    Args:
        header_col_width (float) : A number between 0 and 1 which is the
            percentage of the width of the screen given to the header. The rest
            is given to the download button.
    """
    path = streamlit.session_state['selected'][0]
    # This file extension may be '.gz', if it is, it is compressed.
    file_name, compressed_file_extension = os.path.splitext(path)
    # This is the true file_extension of the file, regardless of if it is
    # compressed or not.
    file_extension = utils.get_file_ext(path)
    header_col, download_col = streamlit.columns([header_col_width,
                                                  1 - header_col_width],
                                                 gap='small')
    relative_path = os.path.relpath(path,
                                    chip._getworkdir(step=step, index=index))
    with header_col:
        streamlit.header(relative_path)
    with download_col:
        streamlit.markdown(' ')  # aligns download button with title
        streamlit.download_button(label="Download file",
                                  data=path,
                                  file_name=relative_path)

    if file_extension.lower() in {".png", ".jpg"}:
        streamlit.image(path)
    else:
        try:
            if compressed_file_extension == '.gz':
                fid = gzip.open(path, 'rt')
            else:
                fid = open(path, 'r')
            content = fid.read()
            fid.close()
            if file_extension.lower() == ".json":
                streamlit.json(content)
            else:
                streamlit.code(content, language='markdown', line_numbers=True)
        except UnicodeDecodeError:  # might be OSError, not sure yet
            streamlit.markdown('Cannot read file')


def show_files(chip, step, index):
    """
    Displays the logs and reports using streamlit_tree_select.

    Args:
        chip (Chip) : the chip object that contains the schema read from.
        step (string) : step of node.
        index (string) : index of node.
    """
    streamlit.caption('files')

    logs_and_reports = report.get_files(chip, step, index)
    logs_and_reports = _convert_filepaths(logs_and_reports)

    if logs_and_reports == []:
        streamlit.markdown('No files to show')
        return False

    # kinda janky at the moment, does not always flip immediately
    # TODO make so that selection changes on first click
    if "selected" not in streamlit.session_state:
        streamlit.session_state['selected'] = []
    if "expanded" not in streamlit.session_state:
        streamlit.session_state['expanded'] = []

    selected = tree_select(logs_and_reports,
                           expand_on_click=True,
                           checked=streamlit.session_state['selected'],
                           expanded=streamlit.session_state['expanded'],
                           only_leaf_checkboxes=True)
    # only include files in 'checked' (folders are also included when they
    # are opened)
    selected['checked'] = [x for x in selected['checked'] if os.path.isfile(x)]

    if len(selected['checked']) == 0:
        streamlit.session_state['selected'] = []
    if len(selected["checked"]) == 1:
        streamlit.session_state['selected'] = selected["checked"]
    if len(selected["checked"]) > 1:
        for x in selected["checked"]:
            if x != streamlit.session_state['selected'][0]:
                newly_selected = x
                break
        streamlit.session_state['selected'] = [newly_selected]
        streamlit.session_state['expanded'] = selected["expanded"]
        streamlit.session_state['right after rerun'] = True
        streamlit.experimental_rerun()

    if streamlit.session_state.selected != []:
        return True
    return False


def show_metrics_for_file(chip, step, index):
    """
    Displays the metrics that are included in each file.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
        step (string) : Step of node.
        index (string) : Index of node.
    """
    if 'selected' in streamlit.session_state and \
       len(streamlit.session_state['selected']) == 1:
        file = streamlit.session_state['selected'][0]
        metrics_of_file = report.get_metrics_source(chip, step, index)
        file = os.path.relpath(file, f"/{step}/{index}")
        if file in metrics_of_file:
            metrics = ", ".join(metrics_of_file[file]) + "."
            streamlit.success("This file includes the metrics of " + metrics)
        else:
            streamlit.warning("This file does not include any metrics.")


def show_manifest(manifest, max_num_of_keys_to_show=20):
    """
    Displays the manifest and a way to search through the manifest.

    Args:
        manifest (dict) : Represents the manifest json.
        max_num_of_keys_to_show (int) : The maximum number of keys that the
            manifest may have in order to be automatically expanded.
    """
    streamlit.header('Manifest Tree')

    key_search_col, value_search_col = streamlit.columns(2, gap="large")

    with key_search_col:
        key = streamlit.text_input('Search Keys', '', placeholder="Keys")
        if key != '':
            manifest = report.search_manifest(manifest, key_search=key)

    with value_search_col:
        value = streamlit.text_input('Search Values', '', placeholder="Values")
        if value != '':
            manifest = report.search_manifest(manifest, value_search=value)

    numOfKeys = report.get_total_manifest_key_count(manifest)

    streamlit.json(manifest, expanded=(numOfKeys < max_num_of_keys_to_show))


def select_nodes(metric_dataframe, node_from_flowgraph):
    """
    Displays selectbox for nodes to show in the node information panel. Since
    both the flowgraph and selectbox show which node's information is
    displayed, the one clicked more recently will be displayed.

    Args:
        metric_dataframe (Pandas.DataFrame) : Contains the metrics of all
            nodes.
        node_from_flowgraph (string/None) : Contains a string of the node to
            display or None if none exists.
    """
    option = metric_dataframe.columns.tolist()[0]

    with streamlit.expander("Select Node"):
        with streamlit.form("nodes"):
            option = streamlit.selectbox('Pick a node to inspect',
                                         metric_dataframe.columns.tolist())

            params_submitted = streamlit.form_submit_button("Run")
            if not params_submitted and node_from_flowgraph is not None:
                option = node_from_flowgraph
                streamlit.session_state['selected'] = []
            if params_submitted:
                streamlit.session_state['selected'] = []
    return option


def show_dataframe_and_parameter_selection(metric_dataframe):
    """
    Displays multi-select check box to the users which allows them to select
    which nodes and metrics to view in the dataframe.

    Args:
        metric_dataframe (Pandas.DataFrame) : Contains the metrics of all
            nodes.
    """
    container = streamlit.container()

    transpose = streamlit.session_state['transpose']

    if transpose:
        metric_dataframe = metric_dataframe.transpose()
        metrics_list = metric_dataframe.columns.tolist()
        node_list = metric_dataframe.index.tolist()
    else:
        metrics_list = metric_dataframe.index.tolist()
        node_list = metric_dataframe.columns.tolist()

    display_to_data = {}
    display_options = []

    for metric_unit in metrics_list:
        metric = metric_to_metric_unit_map[metric_unit]
        display_to_data[metric] = metric_unit
        display_options.append(metric)

    options = {'metrics': [], 'nodes': []}

    # pick parameters
    with streamlit.expander("Select Parameters"):
        with streamlit.form("params"):
            nodes = streamlit.multiselect('Pick nodes to include',
                                          node_list,
                                          [])
            options['nodes'] = nodes

            metrics = streamlit.multiselect('Pick metrics to include?',
                                            display_options,
                                            [])
            options['metrics'] = []
            for metric in metrics:
                options['metrics'].append(display_to_data[metric])

            streamlit.form_submit_button("Run")

    if not options['nodes']:
        options['nodes'] = node_list

    if not options['metrics']:
        options['metrics'] = metrics_list

    # showing the dataframe
    # TODO By July 2024, Streamlit will let catch click events on the dataframe
    if transpose:
        container.dataframe((metric_dataframe.loc[options['nodes'],
                                                  options['metrics']]),
                            use_container_width=True)
    else:
        container.dataframe((metric_dataframe.loc[options['metrics'],
                                                  options['nodes']]),
                            use_container_width=True)


def show_dataframe_header(header_col_width=0.7):
    """
    Displays the header and toggle for the dataframe. If the toggle is flipped,
    it will update the view of the dataframe accordingly.

    Args:
        header_col_width (float) : A number between 0 and 1 which is the
            percentage of the width of the screen given to the header. The rest
            is given to the transpose toggle.
    """
    header_col, transpose_col = streamlit.columns([header_col_width,
                                                   1 - header_col_width],
                                                  gap="large")

    with header_col:
        streamlit.header('Data Metrics')

    with transpose_col:
        streamlit.markdown('')
        # TODO: By October, streamlit will have their own toggle widget
        transpose = st_toggle_switch(label='Transpose',
                                     key='transpose_toggle',
                                     default_value=False,
                                     label_after=True,
                                     # the colors are optional
                                     inactive_color=INACTIVE_TOGGLE_COLOR,
                                     active_color=ACTIVE_TOGGLE_COLOR,
                                     track_color=TRACK_TOGGLE_COLOR)

        # this if statement deals with a problem with st_toggle_switch. The
        # widget does not update during the streamlit.experimental_rerun.
        # We need to keep track of the 'true' flip of the toggle to make sure
        # everything is synced
        if 'right after rerun' in streamlit.session_state and \
           streamlit.session_state['right after rerun']:
            transpose = streamlit.session_state['transpose']
            streamlit.session_state['right after rerun'] = False
        streamlit.session_state['transpose'] = transpose


def display_flowgraph_toggle(label_after):
    """
    Displays the toggle for the flowgraph.

    Args:
        label_after (bool) : the default label fro the toggle
    """
    # this horizontally aligns the toggle with the header
    streamlit.markdown("\n")
    # TODO: By October, streamlit will have their own toggle widget
    fg_toggle = st_toggle_switch(label=" ",
                                 key="flowgraph_toggle",
                                 default_value=label_after,
                                 label_after=True,
                                 # the colors are optional
                                 inactive_color=INACTIVE_TOGGLE_COLOR,
                                 active_color=ACTIVE_TOGGLE_COLOR,
                                 track_color=TRACK_TOGGLE_COLOR)
    streamlit.session_state['flowgraph'] = fg_toggle

    if streamlit.session_state['flowgraph'] != label_after:
        streamlit.session_state['right after rerun'] = True
        streamlit.experimental_rerun()


def show_flowgraph(flowgraph_col_width=0.4, header_col_width=0.7):
    """
    Displays the header and toggle for the flowgraph, and the flowgraph itself.
    This function shows the flowgraph. If the toggle is flipped, the flowgraph
    will disappear.

    Args:
        flowgraph_col_width (float) : A number between 0 and 1 which is the
            percentage of the width of the screen given to the flowgraph when
            expanded. The rest is given to the metrics and node info.
        header_col_width (float) : A number between 0 and 1 which is the
            percentage of the width of the screen given to the header. The rest
            is given to the transpose toggle.
    """
    flowgraph_col, metrics_and_nodes_info_col = \
        streamlit.columns([flowgraph_col_width,
                           1 - flowgraph_col_width], gap="large")

    with flowgraph_col:
        header_col, toggle_col = streamlit.columns([header_col_width,
                                                    1 - header_col_width],
                                                   gap="large")
        with header_col:
            streamlit.header('Flowgraph')

        with toggle_col:
            display_flowgraph_toggle(True)

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

        node_from_flowgraph = agraph(nodes=nodes,
                                     edges=edges,
                                     config=config)
    return node_from_flowgraph, metrics_and_nodes_info_col


def dont_show_flowgraph(flowgraph_col_width=0.1):
    """
    Displays the header and toggle for the flowgraph, and the flowgraph itself.
    This function doesn't show the flowgraph. If the toggle is flipped, the
    flowgraph will re-appear.

    Args:
        flowgraph_col_width (float) : A number between 0 and 1 which is the
            percentage of the width of the screen given to the flowgraph when
            the flowgraph is collapsed. The rest is given to the metrics and
            node info.
    """
    flowgraph_col, metrics_and_nodes_info_col = \
        streamlit.columns([flowgraph_col_width, 1 - flowgraph_col_width],
                          gap="large")

    with flowgraph_col:
        display_flowgraph_toggle(False)

    return None, metrics_and_nodes_info_col


def show_title_and_runs(title_col_width=0.7):
    """
    Displays the title and a selectbox that allows you to select a given run
    to inspect.

    Args:
        title_col_width (float) : A number between 0 and 1 which is
            the percentage of the width of the screen given to the title and
            logo. The rest is given to selectbox.
    """
    title_col, job_select_col = \
        streamlit.columns([title_col_width, 1 - title_col_width], gap="large")

    with title_col:
        streamlit.markdown(
            '''
            <head>
                <style>
                    /* Define the @font-face rule */
                    @font-face {
                    font-family: 'Roboto Mono';
                    src: url(sc_font_path) format('truetype');
                    font-weight: normal;
                    font-style: normal;
                    }

                    /* Styles for the logo and text */
                    .logo-container {
                    display: flex;
                    align-items: flex-start;
                    }

                    .logo-image {
                    margin-right: 10px;
                    margin-top: -10px;
                    }

                    .logo-text {
                    display: flex;
                    flex-direction: column;
                    margin-top: -20px;
                    }

                    .text1 {
                    color: #F1C437; /* Yellow color */
                    font-family: 'Roboto Mono', sans-serif;
                    font-weight: 700 !important;
                    font-size: 30px !important;
                    margin-bottom: -16px;
                    }

                    .text2 {
                    color: #1D4482; /* Blue color */
                    font-family: 'Roboto Mono', sans-serif;
                    font-weight: 700 !important;
                    font-size: 30px !important;
                    }

                </style>
            </head>''',
            unsafe_allow_html=True
        )

        streamlit.markdown(
            f'''
            <body>
                <div class="logo-container">
                    <img src="data:image/png;base64,{base64.b64encode(open(sc_logo_path,
                    "rb").read()).decode()}" alt="Logo Image" class="logo-image" height="61">
                    <div class="logo-text">
                        <p class="text1">{streamlit.session_state['master chip'].design}</p>
                        <p class="text2">dashboard</p>
                    </div>
                </div>
            </body>
            ''',
            unsafe_allow_html=True
        )

    with job_select_col:
        all_jobs = streamlit.session_state['master chip'].getkeys('history')
        all_jobs.insert(0, 'default')
        job = streamlit.selectbox('pick a job', all_jobs,
                                  label_visibility='collapsed')
        previous_job = streamlit.session_state['job']
        streamlit.session_state['job'] = job
        if previous_job != job:
            streamlit.session_state['right after rerun'] = True
            streamlit.experimental_rerun()

    return new_chip


new_chip = show_title_and_runs()

# gathering data
metric_dataframe = report.make_metric_dataframe(new_chip)

# create mapping between task and step, index
node_to_step_index_map = {}
for step, index in metric_dataframe.columns.tolist():
    node_to_step_index_map[step + index] = (step, index)
# concatenate step and index
metric_dataframe.columns = metric_dataframe.columns.map(lambda x:
                                                        f'{x[0]}{x[1]}')

# create mapping between metric concatenated with unit and just the metric
metric_to_metric_unit_map = {}
for metric, unit in metric_dataframe.index.tolist():
    if unit != '':
        metric_to_metric_unit_map[f'{metric} ({unit})'] = metric
    else:
        metric_to_metric_unit_map[metric] = metric
# concatenate metric and unit
metric_dataframe.index = metric_dataframe.index.map(lambda x:
                                                    f'{x[0]} ({x[1]})'
                                                    if x[1] else x[0])

nodes, edges = get_nodes_and_edges(new_chip,
                                   report.get_flowgraph_edges(new_chip),
                                   report.get_flowgraph_path(new_chip))
manifest = report.make_manifest(new_chip)

if 'flowgraph' not in streamlit.session_state:
    streamlit.session_state['flowgraph'] = True

if os.path.isfile(f'{new_chip._getworkdir()}/{new_chip.design}.png'):
    tabs = streamlit.tabs(["Metrics",
                           "Manifest",
                           "File Viewer",
                           "Design Preview"])
    metrics_tab, manifest_tab, file_viewer_tab, design_preview_tab = tabs

    with design_preview_tab:
        streamlit.header('Design Preview')

        streamlit.image(f'{new_chip._getworkdir()}/{new_chip.design}.png')
else:
    tabs = streamlit.tabs(["Metrics", "Manifest", "File Viewer"])
    metrics_tab, manifest_tab, file_viewer_tab = tabs

with metrics_tab:
    ui_width = streamlit_javascript.st_javascript("window.innerWidth")

    if streamlit.session_state['flowgraph']:
        default_flowgraph_width_in_percent = 0.4
        flowgraph_col_width_in_pixels = 520
    else:
        default_flowgraph_width_in_percent = 0.1
        flowgraph_col_width_in_pixels = 120

    if ui_width > 0:
        flowgraph_col_width_in_percent = \
            min(flowgraph_col_width_in_pixels / ui_width,
                default_flowgraph_width_in_percent)
    else:
        flowgraph_col_width_in_percent = default_flowgraph_width_in_percent

    if streamlit.session_state['flowgraph']:
        node_from_flowgraph, datafram_and_node_info_col = \
            show_flowgraph(flowgraph_col_width=flowgraph_col_width_in_percent)
    else:
        node_from_flowgraph, datafram_and_node_info_col = \
            dont_show_flowgraph(flowgraph_col_width=flowgraph_col_width_in_percent)

    with datafram_and_node_info_col:
        show_dataframe_header()

        show_dataframe_and_parameter_selection(metric_dataframe)

        streamlit.header('Node Information')

        metrics_col, records_col, logs_and_reports_col = \
            streamlit.columns(3, gap='small')

        option = select_nodes(metric_dataframe, node_from_flowgraph)

        with metrics_col:
            streamlit.dataframe(metric_dataframe[option].dropna(),
                                use_container_width=True)

        with records_col:
            step, index = node_to_step_index_map[option]
            nodes = {}
            nodes[step + index] = report.get_flowgraph_nodes(new_chip,
                                                             step,
                                                             index)
            node_reports = pandas.DataFrame.from_dict(nodes)
            streamlit.dataframe(node_reports,
                                use_container_width=True)

        with logs_and_reports_col:
            step, index = node_to_step_index_map[option]
            display_file_content = show_files(new_chip, step, index)
            show_metrics_for_file(new_chip, step, index)

with manifest_tab:
    show_manifest(manifest)

with file_viewer_tab:
    if display_file_content:
        show_file_viewer(new_chip, step, index)
    else:
        streamlit.error('Select a file in the metrics tab first!')
