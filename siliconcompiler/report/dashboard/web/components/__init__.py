import base64
import json
import os

import streamlit
from streamlit_agraph import agraph
import streamlit_antd_components as sac

from PIL import Image

import siliconcompiler
from siliconcompiler import __version__ as sc_version
from siliconcompiler import utils
from siliconcompiler.report import report

from siliconcompiler.report.dashboard.web import state
from siliconcompiler.report.dashboard.web import layouts
from siliconcompiler.report.dashboard.web.utils import file_utils
from siliconcompiler.report.dashboard.web.components import flowgraph


SC_ABOUT = [
    f"SiliconCompiler {sc_version}",
    '''A compiler framework that automates translation from source code to
     silicon.''',
    "https://www.siliconcompiler.com/",
    "https://github.com/siliconcompiler/siliconcompiler/"
]
SC_MENU = {
    "Get help": "https://docs.siliconcompiler.com/",
    "Report a Bug":
    '''https://github.com/siliconcompiler/siliconcompiler/issues''',
    "About": "\n\n".join(SC_ABOUT)}
SC_DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(siliconcompiler.__file__), 'data'))
SC_LOGO_PATH = os.path.join(SC_DATA_ROOT, 'logo.png')
SC_FONT_PATH = os.path.join(SC_DATA_ROOT, 'RobotoMono', 'RobotoMono-Regular.ttf')


def page_header(title_col_width=0.7):
    """
    Displays the title and a selectbox that allows you to select a given run
    to inspect.

    Args:
        title_col_width (float) : A number between 0 and 1 which is the percentage of the
            width of the screen given to the title and logo. The rest is given to selectbox.
    """

    if state.DEVELOPER:
        col_width = (1 - title_col_width) / 2
        title_col, job_select_col, settings_col = \
            streamlit.columns([title_col_width, col_width, col_width], gap="large")
    else:
        title_col, job_select_col = \
            streamlit.columns([title_col_width, 1 - title_col_width], gap="large")

    with title_col:
        design_title(design=state.get_chip().design)
    with job_select_col:
        job_selector()

    if state.DEVELOPER:
        with settings_col:
            with streamlit.popover("Settings", use_container_width=True):
                all_layouts = layouts.get_all_layouts()
                layout_index = all_layouts.index(state.get_key(state.APP_LAYOUT))
                if state.set_key(
                        state.APP_LAYOUT,
                        streamlit.selectbox("Layout", all_layouts, index=layout_index)):
                    state.set_key(state.APP_RERUN, "Layout")

                state._DEBUG = streamlit.checkbox("Debug", state._DEBUG)

                state.set_key(
                    state.APP_RUNNING_REFRESH,
                    streamlit.slider(
                        "Running refresh rate (ms)",
                        min_value=1000,
                        max_value=10000,
                        step=500,
                        value=state.get_key(state.APP_RUNNING_REFRESH)))

                state.set_key(
                    state.APP_STOPPED_REFRESH,
                    streamlit.slider(
                        "Stopped refresh rate (ms)",
                        min_value=1000,
                        max_value=100000,
                        step=1000,
                        value=state.get_key(state.APP_STOPPED_REFRESH)))

                state.set_key(
                    state.MAX_DICT_ITEMS_TO_SHOW,
                    streamlit.number_input(
                        "Maximum dict item to show",
                        min_value=1,
                        max_value=10000,
                        value=state.get_key(state.MAX_DICT_ITEMS_TO_SHOW)))

                state.set_key(
                    state.MAX_FILE_LINES_TO_SHOW,
                    streamlit.number_input(
                        "Maximum file lines to show",
                        min_value=100,
                        max_value=1000,
                        step=100,
                        value=state.get_key(state.MAX_FILE_LINES_TO_SHOW)))


def design_title(design=""):
    font = base64.b64encode(open(SC_FONT_PATH, "rb").read()).decode()
    streamlit.html(
        f'''
<head>
    <style>
        /* Define the @font-face rule */
        @font-face {{
        font-family: 'Roboto Mono';
        src: url(data:font/truetype;charset=utf-8;base64,{font}) format('truetype');
        font-weight: normal;
        font-style: normal;
        }}

        /* Styles for the logo and text */
        .logo-container {{
        display: flex;
        align-items: flex-start;
        }}

        .logo-image {{
        margin-right: 10px;
        margin-top: -10px;
        }}

        .logo-text {{
        display: flex;
        flex-direction: column;
        margin-top: -20px;
        }}

        .design-text {{
        color: #F1C437; /* Yellow color */
        font-family: 'Roboto Mono', sans-serif;
        font-weight: 700 !important;
        font-size: 30px !important;
        margin-bottom: -16px;
        }}

        .dashboard-text {{
        color: #1D4482; /* Blue color */
        font-family: 'Roboto Mono', sans-serif;
        font-weight: 700 !important;
        font-size: 30px !important;
        }}

    </style>
</head>
        '''
    )

    logo = base64.b64encode(open(SC_LOGO_PATH, "rb").read()).decode()
    streamlit.html(
        f'''
<body>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo}" alt="SiliconCompiler logo"
             class="logo-image" height="61">
        <div class="logo-text">
            <p class="design-text">{design}</p>
            <p class="dashboard-text">dashboard</p>
        </div>
    </div>
</body>
        '''
    )


def job_selector():
    job = streamlit.selectbox(
        'pick a job',
        state.get_chips(),
        label_visibility='collapsed')

    if state.set_key(state.SELECTED_JOB, job):
        # Job changed, so need to run
        state.set_key(state.APP_RERUN, "Job")


def setup_page():
    streamlit.set_page_config(
        page_title=f'{state.get_chip().design} dashboard',
        page_icon=Image.open(SC_LOGO_PATH),
        layout="wide",
        menu_items=SC_MENU)


def file_viewer(chip, path, page_key=None, header_col_width=0.89):
    if not path:
        streamlit.error('Select a file')
        return

    if not os.path.isfile(path):
        streamlit.error(f'{path} is not a file')
        return

    # Detect file type
    relative_path = os.path.relpath(path, chip.getworkdir())
    filename = os.path.basename(path)
    file_extension = utils.get_file_ext(path)

    # Build streamlit module
    header_col, download_col = \
        streamlit.columns([header_col_width, 1 - header_col_width], gap='small')

    with header_col:
        streamlit.header(relative_path)

    with download_col:
        streamlit.markdown(' ')  # aligns download button with title
        streamlit.download_button(
            label="Download",
            data=path,
            file_name=filename,
            use_container_width=True)

    try:
        if file_extension in ('jpg', 'jpeg', 'png'):
            # Data is an image
            streamlit.image(path)
        elif file_extension == 'json':
            # Data is a json file
            data = json.loads(file_utils.read_file(path, None))
            expand_keys = report.get_total_manifest_key_count(data) < \
                state.get_key(state.MAX_DICT_ITEMS_TO_SHOW)
            if not expand_keys:
                # Open two levels
                expand_keys = 2
            streamlit.json(data, expanded=expand_keys)
        else:
            file_data = file_utils.read_file(path, None).splitlines()
            max_pages = len(file_data)
            page_size = state.get_key(state.MAX_FILE_LINES_TO_SHOW)

            file_section = streamlit.container()

            if page_key:
                if state.get_key(page_key) is None:
                    state.set_key(page_key, 1)
                index = state.get_key(page_key)
            else:
                index = 1

            page = sac.pagination(
                align='center',
                index=index,
                jump=True,
                show_total=True,
                page_size=page_size,
                total=max_pages,
                disabled=max_pages < state.get_key(state.MAX_FILE_LINES_TO_SHOW))

            if page_key:
                state.set_key(page_key, page)

            start_idx = (page - 1) * state.get_key(state.MAX_FILE_LINES_TO_SHOW)
            end_idx = start_idx + state.get_key(state.MAX_FILE_LINES_TO_SHOW)
            file_show = file_data[start_idx:end_idx]
            with file_section:
                # Assume file is text
                streamlit.code(
                    "\n".join(file_show),
                    language=file_utils.get_file_type(file_extension),
                    line_numbers=True)
    except Exception as e:
        streamlit.markdown(f'Error occurred reading file: {e}')


def manifest_viewer(
        chip,
        header_col_width=0.70):
    """
    Displays the manifest and a way to search through the manifest.

    Args:
        chip (Chip) : Chip object
        header_col_width (float) : A number between 0 and 1 which is the maximum
            percentage of the width of the screen given to the header. The rest
            is given to the settings and download buttons.
    """
    end_column_widths = (1 - header_col_width) / 2
    header_col, settings_col, download_col = \
        streamlit.columns(
            [header_col_width, end_column_widths, end_column_widths],
            gap='small')
    with header_col:
        streamlit.header('Manifest')

    with settings_col:
        streamlit.markdown(' ')  # aligns with title
        with streamlit.popover("Settings", use_container_width=True):
            if streamlit.checkbox(
                    'Raw manifest',
                    help='Click here to see the manifest before it was made more readable'):
                manifest_to_show = chip.schema.getdict()
            else:
                manifest_to_show = report.make_manifest(chip)

            if streamlit.checkbox(
                    'Hide empty values',
                    help='Hide empty keypaths',
                    value=True):
                manifest_to_show = report.search_manifest(
                    manifest_to_show,
                    value_search='*')

            search_key = streamlit.text_input('Search Keys', '', placeholder="Keys")
            search_value = streamlit.text_input('Search Values', '', placeholder="Values")

            manifest_to_show = report.search_manifest(
                manifest_to_show,
                key_search=search_key,
                value_search=search_value)

    with download_col:
        streamlit.markdown(' ')  # aligns with title
        streamlit.download_button(
            label='Download',
            file_name='manifest.json',
            data=json.dumps(chip.schema.getdict(), indent=2),
            mime="application/json",
            use_container_width=True)

    expand_keys = report.get_total_manifest_key_count(manifest_to_show) < \
        state.get_key(state.MAX_DICT_ITEMS_TO_SHOW)
    if not expand_keys:
        # Open two levels
        expand_keys = 2
    streamlit.json(manifest_to_show, expanded=expand_keys)


def metrics_viewer(metric_dataframe, metric_to_metric_unit_map, header_col_width=0.7, height=None):
    """
    Displays multi-select check box to the users which allows them to select
    which nodes and metrics to view in the dataframe.

    Args:
        metric_dataframe (Pandas.DataFrame) : Contains the metrics of all nodes.
        metric_to_metric_unit_map (dict) : Maps the metric to the associated metric unit.
    """

    all_nodes = metric_dataframe.columns.tolist()
    all_metrics = list(metric_to_metric_unit_map.values())

    header_col, settings_col = streamlit.columns(
        [header_col_width, 1 - header_col_width],
        gap="large")
    with header_col:
        streamlit.header('Metrics')
    with settings_col:
        # Align to header
        streamlit.markdown('')

        with streamlit.popover("Settings", use_container_width=True):
            transpose = streamlit.checkbox(
                'Transpose',
                help='Transpose the metrics table')

            display_nodes = streamlit.multiselect('Pick nodes to include', all_nodes, [])
            display_metrics = streamlit.multiselect('Pick metrics to include?', all_metrics, [])

    # Filter data
    if not display_nodes:
        display_nodes = all_nodes

    if not display_metrics:
        display_metrics = all_metrics

    dataframe_nodes = list(display_nodes)
    dataframe_metrics = []
    for metric in metric_dataframe.index.tolist():
        if metric_to_metric_unit_map[metric] in display_metrics:
            dataframe_metrics.append(metric)

    metric_dataframe = metric_dataframe.loc[dataframe_metrics, dataframe_nodes]
    if transpose:
        metric_dataframe = metric_dataframe.transpose()

    # TODO By July 2024, Streamlit will let catch click events on the dataframe
    streamlit.dataframe(metric_dataframe, use_container_width=True, height=height)


def node_image_viewer(chip, step, index):
    exts = ('png', 'jpg', 'jpeg')
    images = []
    for path, _, files in report.get_files(chip, step, index):
        images.extend([os.path.join(path, f) for f in files if utils.get_file_ext(f) in exts])

    if not images:
        streamlit.markdown("No images to show")

    work_dir = chip.getworkdir(step=step, index=index)

    columns = streamlit.slider(
        "Image columns",
        min_value=1,
        max_value=min(len(images), 10),
        value=min(len(images), 4),
        disabled=len(images) < 2)

    column = 0
    for image in sorted(images):
        if column == 0:
            cols = streamlit.columns(columns)

        with cols[column]:
            streamlit.image(
                image,
                caption=os.path.relpath(image, work_dir),
                use_column_width=True)

        column += 1
        if column == columns:
            column = 0


def node_file_tree_viewer(chip, step, index):
    logs_and_reports = file_utils.convert_filepaths_to_select_tree(
        report.get_files(chip, step, index))

    if not logs_and_reports:
        streamlit.markdown("No files to show")

    lookup = {}
    tree_items = []

    metrics_source, file_metrics = report.get_metrics_source(chip, step, index)
    work_dir = chip.getworkdir(step=step, index=index)

    def make_item(file):
        lookup[file['value']] = file['label']
        item = sac.TreeItem(
            file['value'],
            icon=file_utils.get_file_icon(file['value']),
            tag=[],
            children=[])

        check_file = os.path.relpath(file['value'], work_dir)
        if check_file in file_metrics:
            metrics = set(file_metrics[check_file])
            primary_source = set()
            if check_file in metrics_source:
                primary_source = set(metrics_source[check_file])
            metrics = metrics - primary_source

            for color, metric_set in (('blue', primary_source), ('green', metrics)):
                if len(item.tag) >= 5:
                    break

                for metric in metric_set:
                    if len(item.tag) < 5:
                        item.tag.append(sac.Tag(metric, color=color))
                    else:
                        item.tag.append(sac.Tag('metrics...', color='geekblue'))
                        break
            item.tooltip = "metrics: " + ", ".join(file_metrics[check_file])

        if 'children' in file:
            item.icon = 'folder'
            for child in file['children']:
                item.children.append(make_item(child))

        return item

    for file in logs_and_reports:
        tree_items.append(make_item(file))

    def format_label(value):
        return lookup[value]

    selected = sac.tree(
        items=tree_items,
        format_func=format_label,
        size='md',
        icon='table',
        open_all=True)

    if selected and os.path.isfile(selected):
        state.set_key(state.SELECTED_FILE, selected)
        state.set_key(state.SELECTED_FILE_PAGE, None)


def node_viewer(chip, step, index, metric_dataframe, height=None):
    from pandas import DataFrame

    metrics_col, records_col, logs_and_reports_col = streamlit.columns(3, gap='small')

    node_name = f'{step}{index}'

    with metrics_col:
        streamlit.subheader(f'{node_name} metrics')
        if node_name in metric_dataframe:
            streamlit.dataframe(
                metric_dataframe[node_name].dropna(),
                use_container_width=True,
                height=height)
    with records_col:
        streamlit.subheader(f'{step}{index} details')
        nodes = {}
        nodes[step + index] = report.get_flowgraph_nodes(chip, step, index)
        streamlit.dataframe(
            DataFrame.from_dict(nodes),
            use_container_width=True,
            height=height)
    with logs_and_reports_col:
        streamlit.subheader(f'{step}{index} files')
        node_file_tree_viewer(chip, step, index)


def flowgraph_viewer(chip):
    '''
    This function creates, displays, and returns the selected node of the flowgraph.

    Args:
        chip (Chip) : The chip object that contains the schema read from.
    '''

    nodes, edges = flowgraph.get_nodes_and_edges(chip)
    if state.set_key(state.SELECTED_FLOWGRAPH_NODE, agraph(
            nodes=nodes,
            edges=edges,
            config=flowgraph.get_graph_config())):
        if state.get_key(state.SELECTED_FLOWGRAPH_NODE):
            state.set_key(state.NODE_SOURCE, "flowgraph")


def node_selector(nodes):
    """
    Displays selectbox for nodes to show in the node information panel. Since
    both the flowgraph and selectbox show which node's information is
    displayed, the one clicked more recently will be displayed.

    Args:
        nodes (list) : Contains the metrics of all nodes.
    """
    prev_node = state.get_selected_node()

    with streamlit.popover("Select Node", use_container_width=True):
        # Preselect node
        idx = 0
        if prev_node:
            idx = nodes.index(prev_node)
        if state.set_key(
                state.SELECTED_SELECTOR_NODE,
                streamlit.selectbox(
                    'Pick a node to inspect',
                    nodes,
                    index=idx)):
            state.set_key(state.NODE_SOURCE, "selector")
