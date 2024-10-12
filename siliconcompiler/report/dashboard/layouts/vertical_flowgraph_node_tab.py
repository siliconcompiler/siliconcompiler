import math
import os
import streamlit

from siliconcompiler.report.dashboard import components
from siliconcompiler.report.dashboard.components import graph
from siliconcompiler.report.dashboard.components import file_utils
from siliconcompiler.report.dashboard import state
import streamlit_antd_components as sac


def layout(
        chip,
        metric_dataframe):
    components.page_header()

    tab_headings = [
        sac.TabsItem(
            "Metrics",
            icon='stack'),
        sac.TabsItem(
            "Node Information",
            icon='diagram-2'),
        sac.TabsItem(
            "Manifest",
            icon=file_utils.get_file_icon('manifest.pkg.json')),
        sac.TabsItem(
            "File Viewer",
            icon=file_utils.get_file_icon(streamlit.session_state[state.SELECTED_FILE])),
        sac.TabsItem(
            "Design Preview",
            icon=file_utils.get_file_icon('design.png'),
            disabled=not os.path.isfile(f'{chip.getworkdir()}/{chip.design}.png')),
        sac.TabsItem(
            "Graphs",
            icon='graph-up',
            disabled=len(streamlit.session_state[state.LOADED_CHIPS]) == 1)
    ]

    index = 0
    if state.DEBUG:
        print("Tab before", streamlit.session_state[state.SELECT_TAB])
    if streamlit.session_state[state.SELECT_TAB] == "file":
        if streamlit.session_state[state.SELECTED_FILE]:
            index = 3
    elif streamlit.session_state[state.SELECT_TAB] == "node":
        if streamlit.session_state[state.SELECTED_NODE]:
            index = 1
    streamlit.session_state[state.SELECT_TAB] = None
    if state.DEBUG:
        print("Tab after", streamlit.session_state[state.SELECT_TAB])

    tab_selected = sac.tabs(
        tab_headings,
        align='center',
        variant='outline',
        use_container_width=True,
        index=index)

    if tab_selected == "Metrics":
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
            components.metrics_viewer(metric_dataframe, height=1000)

    if tab_selected == "Node Information":
        nodes = streamlit.session_state[state.NODE_MAPPING]

        header_col, settings_col = \
            streamlit.columns(
                [0.7, 0.3],
                gap='small')
        with header_col:
            streamlit.header('Node Information')
        with settings_col:
            components.node_selector(list(nodes.keys()))

        step, index = nodes[streamlit.session_state[state.SELECTED_NODE]]
        components.node_viewer(chip, step, index, metric_dataframe, height=1000)

    if tab_selected == "Manifest":
        components.manifest_viewer(chip)

    if tab_selected == "File Viewer":
        path = None
        if state.SELECTED_FILE in streamlit.session_state:
            path = streamlit.session_state[state.SELECTED_FILE]

        components.file_viewer(chip, path)

    if tab_selected == "Design Preview":
        components.file_viewer(chip, f'{chip.getworkdir()}/{chip.design}.png')

    if tab_selected == "Graphs":
        metrics = metric_dataframe.index.map(
            lambda x: streamlit.session_state[state.METRIC_MAPPING][x])
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
                graph.graph(metrics, nodes, graph_number)
                if graph_number < last_row_num:
                    streamlit.divider()
            graph_number += 1
