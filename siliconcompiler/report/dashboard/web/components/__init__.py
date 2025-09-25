"""
A collection of functions that create and manage UI components for the
SiliconCompiler web dashboard using Streamlit.

This module contains functions for rendering various parts of the dashboard,
such as headers, file viewers, metric tables, and the interactive flowgraph.
These components are composed by the layout functions to build the complete UI.
"""
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
from siliconcompiler.utils.paths import workdir, jobdir


# --- Constants for Page Configuration ---
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
    Displays the main page header, including the design title, a job selector,
    and a settings popover for developers.

    Args:
        title_col_width (float): The percentage of the page width to allocate
            to the title and logo. The rest is divided among other components.
    """
    if state.DEVELOPER:
        col_width = (1 - title_col_width) / 2
        title_col, job_select_col, settings_col = \
            streamlit.columns([title_col_width, col_width, col_width], gap="large")
    else:
        title_col, job_select_col = \
            streamlit.columns([title_col_width, 1 - title_col_width], gap="large")

    with title_col:
        design_title(design=state.get_project().design.name)
    with job_select_col:
        job_selector()

    if state.DEVELOPER:
        with settings_col:
            with streamlit.popover("Settings", use_container_width=True):
                # Layout selection
                all_layouts = layouts.get_all_layouts()
                layout_index = all_layouts.index(state.get_key(state.APP_LAYOUT))
                if state.set_key(
                        state.APP_LAYOUT,
                        streamlit.selectbox("Layout", all_layouts, index=layout_index)):
                    state.set_key(state.APP_RERUN, "Layout")

                # Debugging and refresh rate settings
                state._DEBUG = streamlit.checkbox("Debug", state._DEBUG)
                state.set_key(
                    state.APP_RUNNING_REFRESH,
                    streamlit.slider(
                        "Running refresh rate (ms)",
                        min_value=1000, max_value=10000, step=500,
                        value=state.get_key(state.APP_RUNNING_REFRESH)))
                state.set_key(
                    state.APP_STOPPED_REFRESH,
                    streamlit.slider(
                        "Stopped refresh rate (ms)",
                        min_value=1000, max_value=100000, step=1000,
                        value=state.get_key(state.APP_STOPPED_REFRESH)))

                # Content display settings
                state.set_key(
                    state.MAX_DICT_ITEMS_TO_SHOW,
                    streamlit.number_input(
                        "Maximum dict item to show",
                        min_value=1, max_value=10000,
                        value=state.get_key(state.MAX_DICT_ITEMS_TO_SHOW)))
                state.set_key(
                    state.MAX_FILE_LINES_TO_SHOW,
                    streamlit.number_input(
                        "Maximum file lines to show",
                        min_value=100, max_value=1000, step=100,
                        value=state.get_key(state.MAX_FILE_LINES_TO_SHOW)))


def design_title(design=""):
    """
    Renders the SiliconCompiler logo and design name using custom HTML and CSS.

    Args:
        design (str): The name of the design to display.
    """
    # Inject custom font and CSS for styling the title
    font = base64.b64encode(open(SC_FONT_PATH, "rb").read()).decode()
    streamlit.html(f'''
<head>
    <style>
        @font-face {{
            font-family: 'Roboto Mono';
            src: url(data:font/truetype;charset=utf-8;base64,{font}) format('truetype');
        }}
        .logo-container {{ display: flex; align-items: flex-start; }}
        .logo-image {{ margin-right: 10px; margin-top: -10px; }}
        .logo-text {{ display: flex; flex-direction: column; margin-top: -20px; }}
        .design-text, .dashboard-text {{
            font-family: 'Roboto Mono', sans-serif;
            font-weight: 700 !important;
            font-size: 30px !important;
        }}
        .design-text {{ color: #F1C437; margin-bottom: -16px; }}
        .dashboard-text {{ color: #1D4482; }}
    </style>
</head>''')

    # Render the logo and title HTML
    logo = base64.b64encode(open(SC_LOGO_PATH, "rb").read()).decode()
    streamlit.html(f'''
<body>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo}" alt="SiliconCompiler logo"
             class="logo-image" height="61">
        <div class="logo-text">
            <p class="design-text">{design}</p>
            <p class="dashboard-text">dashboard</p>
        </div>
    </div>
</body>''')


def job_selector():
    """
    Displays a selectbox for choosing a job/run to inspect.

    The list of jobs includes the current run ('default') and any historical
    runs found in the manifest.
    """
    job = streamlit.selectbox(
        'pick a job',
        state.get_projects(),
        label_visibility='collapsed')

    if state.set_key(state.SELECTED_JOB, job):
        # If the job changes, trigger a rerun to update the entire dashboard.
        state.set_key(state.APP_RERUN, "Job")


def setup_page():
    """
    Configures the global Streamlit page settings.

    This should be one of the first Streamlit commands called. It sets the page
    title, icon, layout, and custom menu items.
    """
    streamlit.set_page_config(
        page_title=f'{state.get_project().design.name} dashboard',
        page_icon=Image.open(SC_LOGO_PATH),
        layout="wide",
        menu_items=SC_MENU)


def file_viewer(project, path, page_key=None, header_col_width=0.89):
    """
    Renders a viewer for a specified file.

    Supports images, JSON, and plain text files with syntax highlighting
    and pagination.

    Args:
        project (Project): The project object, used for context (e.g., workdir).
        path (str): The absolute path to the file to display.
        page_key (str, optional): The state key to use for storing the current
            page number for paginated text files.
        header_col_width (float): The percentage of width for the file header.
    """
    if not path:
        streamlit.error('Select a file')
        return

    if not os.path.isfile(path):
        streamlit.error(f'{path} is not a file')
        return

    # --- File Header and Download Button ---
    relative_path = os.path.relpath(path, jobdir(project))
    filename = os.path.basename(path)
    file_extension = utils.get_file_ext(path)

    header_col, download_col = \
        streamlit.columns([header_col_width, 1 - header_col_width], gap='small')
    with header_col:
        streamlit.header(relative_path)
    with download_col:
        streamlit.markdown(' ')  # Aligns download button with title
        with open(path, "rb") as fp:
            streamlit.download_button(
                label="Download",
                data=fp,
                file_name=filename,
                use_container_width=True)

    # --- File Content Viewer ---
    try:
        if file_extension in ('jpg', 'jpeg', 'png'):
            streamlit.image(path)
        elif file_extension == 'json':
            data = json.loads(file_utils.read_file(path, None))
            # Expand JSON if it's not too large
            expand_keys = report.get_total_manifest_key_count(data) < \
                state.get_key(state.MAX_DICT_ITEMS_TO_SHOW)
            if not expand_keys:
                expand_keys = 2  # Default to expanding two levels
            streamlit.json(data, expanded=expand_keys)
        else:
            # For text files, implement pagination
            file_data = file_utils.read_file(path, None).splitlines()
            page_size = state.get_key(state.MAX_FILE_LINES_TO_SHOW)
            max_pages = (len(file_data) + page_size - 1) // page_size

            if page_key and state.get_key(page_key) is None:
                state.set_key(page_key, 1)
            index = state.get_key(page_key) if page_key else 1

            page = sac.pagination(
                align='center', index=index, total=max_pages,
                disabled=max_pages <= 1)

            if page_key:
                state.set_key(page_key, page)

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            file_show = file_data[start_idx:end_idx]

            streamlit.code(
                "\n".join(file_show),
                language=file_utils.get_file_type(file_extension),
                line_numbers=True)
    except Exception as e:
        streamlit.error(f'Error occurred reading file: {e}')


def manifest_viewer(project, header_col_width=0.70):
    """
    Displays the project's manifest with search and filtering options.

    Args:
        project (Project): The project object whose manifest will be displayed.
        header_col_width (float): The percentage of width for the header.
    """
    # --- Header and Settings ---
    end_column_widths = (1 - header_col_width) / 2
    header_col, settings_col, download_col = \
        streamlit.columns(
            [header_col_width, end_column_widths, end_column_widths],
            gap='small')
    with header_col:
        streamlit.header('Manifest')
    with settings_col:
        streamlit.markdown(' ')  # Aligns with title
        with streamlit.popover("Settings", use_container_width=True):
            # Filtering options
            if streamlit.checkbox('Raw manifest', help='View raw, unprocessed manifest'):
                manifest_to_show = json.loads(json.dumps(project.getdict(), sort_keys=True))
            else:
                manifest_to_show = report.make_manifest(project)

            if streamlit.checkbox('Hide empty values', value=True):
                manifest_to_show = report.search_manifest(manifest_to_show, value_search='*')

            # Search functionality
            search_key = streamlit.text_input('Search Keys', placeholder="Keys")
            search_value = streamlit.text_input('Search Values', placeholder="Values")
            manifest_to_show = report.search_manifest(
                manifest_to_show, key_search=search_key, value_search=search_value)
    with download_col:
        streamlit.markdown(' ')  # Aligns with title
        streamlit.download_button(
            label='Download', file_name='manifest.json',
            data=json.dumps(project.getdict(), indent=2),
            mime="application/json", use_container_width=True)

    # --- Manifest Display ---
    expand_keys = report.get_total_manifest_key_count(manifest_to_show) < \
        state.get_key(state.MAX_DICT_ITEMS_TO_SHOW)
    if not expand_keys:
        expand_keys = 2  # Default to expanding two levels
    streamlit.json(manifest_to_show, expanded=expand_keys)


def metrics_viewer(metric_dataframe, metric_to_metric_unit_map, header_col_width=0.7, height=None):
    """
    Displays a filterable and transposable table of metrics.

    Args:
        metric_dataframe (pandas.DataFrame): The dataframe containing all metrics.
        metric_to_metric_unit_map (dict): A mapping from formatted metric names
            (with units) to raw metric names.
        header_col_width (float): The percentage of width for the header.
        height (int, optional): The height of the dataframe in pixels.
    """
    all_nodes = metric_dataframe.columns.tolist()
    all_metrics = list(metric_to_metric_unit_map.values())

    # --- Header and Settings ---
    header_col, settings_col = streamlit.columns(
        [header_col_width, 1 - header_col_width], gap="large")
    with header_col:
        streamlit.header('Metrics')
    with settings_col:
        streamlit.markdown('')  # Align to header
        with streamlit.popover("Settings", use_container_width=True):
            transpose = streamlit.checkbox('Transpose', help='Transpose the metrics table')
            display_nodes = streamlit.multiselect('Pick nodes to include', all_nodes, [])
            display_metrics = streamlit.multiselect('Pick metrics to include?', all_metrics, [])

    # --- Filter and Display Dataframe ---
    if not display_nodes:
        display_nodes = all_nodes
    if not display_metrics:
        display_metrics = all_metrics

    dataframe_nodes = list(display_nodes)
    dataframe_metrics = [
        metric for metric in metric_dataframe.index.tolist()
        if metric_to_metric_unit_map.get(metric) in display_metrics
    ]

    filtered_df = metric_dataframe.loc[dataframe_metrics, dataframe_nodes]
    if transpose:
        filtered_df = filtered_df.transpose()

    streamlit.dataframe(filtered_df, use_container_width=True, height=height)


def node_image_viewer(project, step, index):
    """
    Displays a gallery of all image files associated with a given node.

    Args:
        project (Project): The project object.
        step (str): The step of the node.
        index (str): The index of the node.
    """
    exts = ('png', 'jpg', 'jpeg')
    images = []
    for path, _, files in report.get_files(project, step, index):
        images.extend([os.path.join(path, f) for f in files if utils.get_file_ext(f) in exts])

    if not images:
        streamlit.markdown("No images to show")
        return

    work_dir = workdir(project, step=step, index=index)
    columns = streamlit.slider(
        "Image columns",
        min_value=1, max_value=min(len(images), 10),
        value=min(len(images), 4), disabled=len(images) < 2)

    # Display images in a grid
    for i, image in enumerate(sorted(images)):
        if i % columns == 0:
            cols = streamlit.columns(columns)
        with cols[i % columns]:
            streamlit.image(
                image,
                caption=os.path.relpath(image, work_dir),
                use_column_width=True)


def node_file_tree_viewer(project, step, index):
    """
    Displays an interactive file tree for a given node.

    Files are decorated with tags indicating which metrics they are a source for.
    Selecting a file in the tree updates the application state to display it
    in the file viewer.

    Args:
        project (Project): The project object.
        step (str): The step of the node.
        index (str): The index of the node.
    """
    logs_and_reports = file_utils.convert_filepaths_to_select_tree(
        report.get_files(project, step, index))

    if not logs_and_reports:
        streamlit.markdown("No files to show")
        return

    # --- Prepare data for the tree component ---
    lookup = {}
    tree_items = []
    metrics_source, file_metrics = report.get_metrics_source(project, step, index)
    work_dir = workdir(project, step=step, index=index)

    def make_item(file):
        """Recursively builds a tree item for the antd component."""
        lookup[file['value']] = file['label']
        item = sac.TreeItem(
            file['value'],
            icon=file_utils.get_file_icon(file['value']),
            tag=[],
            children=[])

        # Add metric source tags
        check_file = os.path.relpath(file['value'], work_dir)
        if check_file in file_metrics:
            metrics = set(file_metrics[check_file])
            primary_source = set(metrics_source.get(check_file, []))
            other_metrics = metrics - primary_source

            tags = [sac.Tag(m, color='blue') for m in primary_source]
            tags += [sac.Tag(m, color='green') for m in other_metrics]

            item.tag = tags[:5]
            if len(tags) > 5:
                item.tag.append(sac.Tag('...', color='geekblue'))
            item.tooltip = "metrics: " + ", ".join(file_metrics[check_file])

        # Recursively add children for folders
        if 'children' in file:
            item.icon = 'folder'
            item.children = [make_item(child) for child in file['children']]

        return item

    tree_items = [make_item(file) for file in logs_and_reports]

    # --- Render the tree ---
    selected = sac.tree(
        items=tree_items,
        format_func=lambda v: lookup.get(v, v),
        size='md', icon='table', open_all=True)

    if selected and os.path.isfile(selected):
        state.set_key(state.SELECTED_FILE, selected)
        state.set_key(state.SELECTED_FILE_PAGE, 1)


def node_viewer(project, step, index, metric_dataframe, height=None):
    """
    Displays a summary view for a single node, including metrics, records, and files.

    Args:
        project (Project): The project object.
        step (str): The step of the node.
        index (str): The index of the node.
        metric_dataframe (pandas.DataFrame): The dataframe of all metrics.
        height (int, optional): The height for the dataframe components.
    """
    from pandas import DataFrame

    metrics_col, records_col, logs_and_reports_col = streamlit.columns(3, gap='small')
    node_name = f'{step}/{index}'

    with metrics_col:
        streamlit.subheader(f'{node_name} metrics')
        if node_name in metric_dataframe:
            streamlit.dataframe(
                metric_dataframe[node_name].dropna(),
                use_container_width=True, height=height)
    with records_col:
        streamlit.subheader(f'{node_name} details')
        nodes = {step + index: report.get_flowgraph_nodes(project, step, index)}
        streamlit.dataframe(
            DataFrame.from_dict(nodes),
            use_container_width=True, height=height)
    with logs_and_reports_col:
        streamlit.subheader(f'{node_name} files')
        node_file_tree_viewer(project, step, index)


def flowgraph_viewer(project):
    """
    Displays the interactive flowgraph for the current job.

    Selecting a node in the graph updates the application state.

    Args:
        project (Project): The project object containing the flowgraph to display.
    """
    nodes, edges = flowgraph.get_nodes_and_edges(project)
    selected_node = agraph(
        nodes=nodes,
        edges=edges,
        config=flowgraph.get_graph_config())

    if state.set_key(state.SELECTED_FLOWGRAPH_NODE, selected_node):
        if state.get_key(state.SELECTED_FLOWGRAPH_NODE):
            state.set_key(state.NODE_SOURCE, "flowgraph")


def node_selector(nodes):
    """
    Displays a dropdown for selecting a node.

    This provides an alternative to selecting a node by clicking on the flowgraph.

    Args:
        nodes (list): A list of node name strings (e.g., ['import/0', 'syn/0']).
    """
    prev_node = state.get_selected_node()

    with streamlit.popover("Select Node", use_container_width=True):
        idx = nodes.index(prev_node) if prev_node in nodes else 0
        selected_node = streamlit.selectbox(
            'Pick a node to inspect',
            nodes,
            index=idx)

        if state.set_key(state.SELECTED_SELECTOR_NODE, selected_node):
            state.set_key(state.NODE_SOURCE, "selector")
