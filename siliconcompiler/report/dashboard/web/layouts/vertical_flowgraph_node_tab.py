"""
Defines a dashboard layout that organizes different views into a set of tabs
using the streamlit-antd-components library.
"""
import os
import streamlit

from siliconcompiler.report.dashboard.web import components
from siliconcompiler.report.dashboard.web.components import graph
from siliconcompiler.report.dashboard.web import state
from siliconcompiler.report.dashboard.web import utils
from siliconcompiler.report.dashboard.web.utils import file_utils
from siliconcompiler.report.dashboard.web.layouts import _common
import streamlit_antd_components as sac
from siliconcompiler.utils.paths import jobdir


def layout():
    """
    Constructs a tab-based layout for the web dashboard.

    This function sets up the main page header and creates a tab group for
    navigating between different views:
    - Metrics: Shows the flowgraph alongside a table of key metrics.
    - Node Information: Provides a detailed view of a selected node's data and files.
    - Manifest: A searchable viewer for the project's manifest.
    - File Viewer: Displays the content of a selected file.
    - Design Preview: Shows a preview image of the design, if available.
    - Graphs: Interactive charts for comparing metrics across runs.

    It handles the logic for displaying the content of the currently selected tab.
    """
    project = state.get_project()
    metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map = \
        utils.generate_metric_dataframe(project)

    # Render the main page header (title, job selector, settings)
    components.page_header()

    # --- Define the tab items ---
    tab_headings = [
        sac.TabsItem("Metrics", icon='stack'),
        sac.TabsItem("Node Information", icon='diagram-2'),
        sac.TabsItem("Manifest", icon=file_utils.get_file_icon('manifest.pkg.json')),
        sac.TabsItem("File Viewer",
                     icon=file_utils.get_file_icon(state.get_key(state.SELECTED_FILE))),
        sac.TabsItem("Design Preview", icon=file_utils.get_file_icon('design.png'),
                     disabled=not os.path.isfile(os.path.join(jobdir(project),
                                                              f'{project.name}.png'))),
        sac.TabsItem("Graphs", icon='graph-up',
                     disabled=len(state.get_key(state.LOADED_PROJECTS)) <= 1)
    ]

    # Render the tabs and get the user's selection
    tab_selected = _common.sac_tabs(tab_headings)

    # --- Render the content for the selected tab ---
    if tab_selected == "Metrics":
        if state.get_key(state.DISPLAY_FLOWGRAPH):
            # Create a two-column layout for the flowgraph and metrics table
            default_flowgraph_width_in_percent = 0.4
            flowgraph_col_width_in_pixels = 520
            flowgraph_col_width_in_percent = state.compute_component_size(
                default_flowgraph_width_in_percent, flowgraph_col_width_in_pixels)

            flowgraph_col, metrics_container = streamlit.columns(
                [flowgraph_col_width_in_percent, 1 - flowgraph_col_width_in_percent],
                gap="large")

            with flowgraph_col:
                streamlit.header('Flowgraph')
                components.flowgraph_viewer(project)
        else:
            metrics_container = streamlit.container()

        with metrics_container:
            # Add a toggle to hide/show the flowgraph
            if state.set_key(state.DISPLAY_FLOWGRAPH, not streamlit.checkbox(
                    'Hide flowgraph', not state.get_key(state.DISPLAY_FLOWGRAPH),
                    help='Click here to hide the flowgraph')):
                state.set_key(state.APP_RERUN, "Flowgraph")

            components.metrics_viewer(
                metric_dataframe,
                metric_to_metric_unit_map,
                height=1000)

    elif tab_selected == "Node Information":
        header_col, settings_col = streamlit.columns([0.7, 0.3], gap='small')
        with header_col:
            streamlit.header('Node Information')
        with settings_col:
            components.node_selector(list(node_to_step_index_map.keys()))

        if state.get_selected_node():
            step, index = node_to_step_index_map[state.get_selected_node()]
            current_file = state.get_key(state.SELECTED_FILE)
            components.node_viewer(project, step, index, metric_dataframe, height=1000)
            # Check if a file was selected within the node viewer
            if current_file != state.get_key(state.SELECTED_FILE):
                state.set_key(state.APP_RERUN, "File")

    elif tab_selected == "Manifest":
        components.manifest_viewer(project)

    elif tab_selected == "File Viewer":
        components.file_viewer(
            project,
            state.get_key(state.SELECTED_FILE),
            page_key=state.SELECTED_FILE_PAGE)

    elif tab_selected == "Design Preview":
        components.file_viewer(project, os.path.join(jobdir(project), f'{project.name}.png'))

    elif tab_selected == "Graphs":
        graph.viewer(node_to_step_index_map)

    # Check if a rerun is needed to switch to a different tab
    _common.check_rerun()
