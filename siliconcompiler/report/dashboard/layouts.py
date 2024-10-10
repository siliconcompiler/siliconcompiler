import os
import streamlit

from siliconcompiler.report.dashboard import components
from siliconcompiler.report.dashboard import graphs
from siliconcompiler.report.dashboard import state


def vertical_flowgraph(
        chip,
        metric_dataframe,
        node_to_step_index_map,
        metric_to_metric_unit_map,
        manifest):
    components.page_header()

    tab_headings = ["Metrics", "Manifest", "File Viewer"]
    if os.path.isfile(f'{chip.getworkdir()}/{chip.design}.png'):
        tab_headings.append("Design Preview")

    has_graphs = len(streamlit.session_state[state.LOADED_CHIPS]) > 1
    if has_graphs:
        tab_headings.append("Graphs")

    tabs = {
        name: tab for name, tab in zip(tab_headings, streamlit.tabs(tab_headings))
    }

    with tabs["Metrics"]:
        # Add flowgraph
        if streamlit.session_state[state.DISPLAY_FLOWGRAPH]:
            default_flowgraph_width_in_percent = 0.4
            flowgraph_col_width_in_pixels = 520
            flowgraph_col_width_in_percent = \
                state.compute_component_size(
                    default_flowgraph_width_in_percent,
                    flowgraph_col_width_in_pixels)

            flowgraph_col, metrics_container = \
                streamlit.columns(
                    [flowgraph_col_width_in_percent, 1 - flowgraph_col_width_in_percent],
                    gap="large")

            with flowgraph_col:
                header_col, flowgraph_toggle_container = streamlit.columns(2, gap="large")
                with header_col:
                    streamlit.header('Flowgraph')
                components.flowgraph_viewer(chip)
        else:
            flowgraph_toggle_container = streamlit.container()
            metrics_container = streamlit.container()

        with flowgraph_toggle_container:
            streamlit.markdown("")
            streamlit.markdown("")

            prev_toggle = streamlit.session_state[state.DISPLAY_FLOWGRAPH]
            streamlit.session_state[state.DISPLAY_FLOWGRAPH] = not streamlit.checkbox(
                'Hide flowgraph',
                help='Click here to hide the flowgraph')

            if prev_toggle != streamlit.session_state[state.DISPLAY_FLOWGRAPH]:
                streamlit.rerun()

        with metrics_container:
            components.metrics_viewer(metric_dataframe, metric_to_metric_unit_map)

            header_col, settings_col = \
                streamlit.columns(
                    [0.7, 0.3],
                    gap='small')
            with header_col:
                streamlit.header('Node Information')
            with settings_col:
                components.node_selector(list(node_to_step_index_map.keys()))

            step, index = node_to_step_index_map[streamlit.session_state[state.SELECTED_NODE]]
            components.node_viewer(chip, step, index, metric_dataframe)

    with tabs["Manifest"]:
        components.manifest_viewer(manifest, chip.schema.cfg)

    with tabs["File Viewer"]:
        path = None
        if state.SELECTED_FILE in streamlit.session_state:
            path = streamlit.session_state[state.SELECTED_FILE]

        components.file_viewer(chip, path)

    if "Design Preview" in tabs:
        with tabs["Design Preview"]:
            components.file_viewer(chip, f'{chip.getworkdir()}/{chip.design}.png')

    if "Graphs" in tabs:
        with tabs["Graphs"]:
            graphs.graphs_module(
                metric_dataframe,
                node_to_step_index_map,
                metric_to_metric_unit_map)
