"""
Defines a dashboard layout that organizes different views into a set of
vertical tabs using Streamlit's native `st.tabs` component.
"""
import os
import streamlit

from siliconcompiler.report.dashboard.web import components
from siliconcompiler.report.dashboard.web.components import graph
from siliconcompiler.report.dashboard.web import state
from siliconcompiler.report.dashboard.web import utils
from siliconcompiler.report.dashboard.web.layouts import _common
from siliconcompiler.utils.paths import jobdir


def layout():
    """
    Constructs a layout using Streamlit's native tabs.

    This function sets up the main page header and then creates a tabbed
    interface for the primary content areas. The "Metrics" tab is a
    comprehensive view containing the flowgraph, metrics table, and detailed
    node information. Other views like the Manifest, File Viewer, and Graphs
    are in separate, conditionally rendered tabs.
    """
    project = state.get_project()
    metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map = \
        utils.generate_metric_dataframe(project)

    # Render the main page header (title, job selector, settings)
    components.page_header()

    # --- Dynamically create tabs based on available data ---
    tab_headings = ["Metrics", "Manifest", "File Viewer"]
    if os.path.isfile(os.path.join(jobdir(project), f'{project.name}.png')):
        tab_headings.append("Design Preview")

    has_graphs = len(state.get_key(state.LOADED_PROJECTS)) > 1
    if has_graphs:
        tab_headings.append("Graphs")

    # Create a dictionary mapping tab names to the tab container objects
    tabs = {name: tab for name, tab in zip(tab_headings, streamlit.tabs(tab_headings))}

    # --- Populate the "Metrics" tab ---
    with tabs["Metrics"]:
        if state.get_key(state.DISPLAY_FLOWGRAPH):
            # Create a two-column layout for the flowgraph and main content
            default_flowgraph_width_in_percent = 0.4
            flowgraph_col_width_in_pixels = 520
            flowgraph_col_width_in_percent = state.compute_component_size(
                default_flowgraph_width_in_percent,
                flowgraph_col_width_in_pixels)

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

            # Display the main metrics table
            components.metrics_viewer(metric_dataframe, metric_to_metric_unit_map)

            streamlit.divider()

            # Display the node information section within the same tab
            header_col, settings_col = streamlit.columns([0.7, 0.3], gap='small')
            with header_col:
                streamlit.header('Node Information')
            with settings_col:
                components.node_selector(list(node_to_step_index_map.keys()))

            if state.get_selected_node():
                step, index = node_to_step_index_map[state.get_selected_node()]
                components.node_viewer(project, step, index, metric_dataframe)

    # --- Populate the "Manifest" tab ---
    with tabs["Manifest"]:
        components.manifest_viewer(project)

    # --- Populate the "File Viewer" tab ---
    with tabs["File Viewer"]:
        components.file_viewer(
            project,
            state.get_key(state.SELECTED_FILE),
            page_key=state.SELECTED_FILE_PAGE)

    # --- Populate conditional tabs ---
    if "Design Preview" in tabs:
        with tabs["Design Preview"]:
            components.file_viewer(project, os.path.join(jobdir(project), f'{project.name}.png'))

    if "Graphs" in tabs:
        with tabs["Graphs"]:
            graph.viewer(node_to_step_index_map)

    # Check if a rerun is needed to switch to a different tab (not applicable
    # for st.tabs, but kept for consistency with other layouts).
    _common.check_rerun()
