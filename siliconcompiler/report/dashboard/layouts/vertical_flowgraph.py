import math
import os
import streamlit

from siliconcompiler.report.dashboard import components
from siliconcompiler.report.dashboard.components import graph
from siliconcompiler.report.dashboard import state
from siliconcompiler.report.dashboard import utils


def layout():
    chip = state.get_chip()
    metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map = \
        utils.generate_metric_dataframe(chip)

    components.page_header()

    tab_headings = ["Metrics", "Manifest", "File Viewer"]
    if os.path.isfile(f'{chip.getworkdir()}/{chip.design}.png'):
        tab_headings.append("Design Preview")

    has_graphs = len(state.get_key(state.LOADED_CHIPS)) > 1
    if has_graphs:
        tab_headings.append("Graphs")

    tabs = {
        name: tab for name, tab in zip(tab_headings, streamlit.tabs(tab_headings))
    }

    with tabs["Metrics"]:
        # Add flowgraph
        if state.get_key(state.DISPLAY_FLOWGRAPH):
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

            changed = state.set_key(state.DISPLAY_FLOWGRAPH, not streamlit.checkbox(
                'Hide flowgraph',
                help='Click here to hide the flowgraph'))

            if changed:
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

            step, index = node_to_step_index_map[state.get_key(state.SELECTED_NODE)]
            components.node_viewer(chip, step, index, metric_dataframe)

    with tabs["Manifest"]:
        components.manifest_viewer(chip)

    with tabs["File Viewer"]:
        path = state.get_key(state.SELECTED_FILE)

        components.file_viewer(chip, path)

    if "Design Preview" in tabs:
        with tabs["Design Preview"]:
            components.file_viewer(chip, f'{chip.getworkdir()}/{chip.design}.png')

    if "Graphs" in tabs:
        with tabs["Graphs"]:
            metrics = metric_dataframe.index.map(lambda x: metric_to_metric_unit_map[x])
            nodes = metric_dataframe.columns

            job_selector_col, graph_adder_col = streamlit.columns(2, gap='large')
            with job_selector_col:
                graph.job_selector()
            with graph_adder_col:
                graphs = graph.graph_count_selector()

            streamlit.divider()

            columns = 1 if graphs <= 1 else 2
            last_row_num = int(math.floor((graphs - 1) / columns)) * columns

            graph_number = 0
            graph_cols = streamlit.columns(columns, gap='large')
            while graph_number < graphs:
                with graph_cols[graph_number % columns]:
                    graph.graph(metrics, nodes, node_to_step_index_map, graph_number)
                    if graph_number < last_row_num:
                        streamlit.divider()
                graph_number += 1
