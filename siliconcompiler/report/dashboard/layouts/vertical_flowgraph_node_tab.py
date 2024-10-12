import math
import os
import streamlit

from siliconcompiler.report.dashboard import components
from siliconcompiler.report.dashboard.components import graph
from siliconcompiler.report.dashboard import state
from siliconcompiler.report.dashboard import utils
from siliconcompiler.report.dashboard.utils import file_utils
import streamlit_antd_components as sac


def layout():
    chip = state.get_chip()
    metric_dataframe, node_to_step_index_map, metric_to_metric_unit_map = \
        utils.generate_metric_dataframe(chip)

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
            icon=file_utils.get_file_icon(state.get_key(state.SELECTED_FILE))),
        sac.TabsItem(
            "Design Preview",
            icon=file_utils.get_file_icon('design.png'),
            disabled=not os.path.isfile(f'{chip.getworkdir()}/{chip.design}.png')),
        sac.TabsItem(
            "Graphs",
            icon='graph-up',
            disabled=len(state.get_key(state.LOADED_CHIPS)) == 1)
    ]

    index = 0
    if state.get_key(state.SELECT_TAB) == "File":
        if state.get_key(state.SELECTED_FILE):
            index = 3
    if state.get_key(state.SELECT_TAB) == "Node":
        index = 1

    tab_selected = sac.tabs(
        tab_headings,
        align='center',
        variant='outline',
        use_container_width=True,
        index=index)

    if tab_selected == "Metrics":
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

            if state.set_key(state.DISPLAY_FLOWGRAPH, not streamlit.checkbox(
                    'Hide flowgraph',
                    help='Click here to hide the flowgraph')):
                state.set_key(state.APP_RERUN, "Flowgraph")

        with metrics_container:
            components.metrics_viewer(metric_dataframe, metric_to_metric_unit_map)

    if tab_selected == "Node Information":
        header_col, settings_col = \
            streamlit.columns(
                [0.7, 0.3],
                gap='small')
        with header_col:
            streamlit.header('Node Information')
        with settings_col:
            components.node_selector(list(node_to_step_index_map.keys()))

        step, index = node_to_step_index_map[state.get_selected_node()]
        current_file = state.get_key(state.SELECTED_FILE)
        components.node_viewer(chip, step, index, metric_dataframe)
        if state.get_key(state.SELECTED_FILE) and \
                current_file != state.get_key(state.SELECTED_FILE):
            state.set_key(state.APP_RERUN, "File")
            state.set_key(state.SELECT_TAB, "File")

    if tab_selected == "Manifest":
        components.manifest_viewer(chip)

    if tab_selected == "File Viewer":
        components.file_viewer(chip, state.get_key(state.SELECTED_FILE))

    if tab_selected == "Design Preview":
        components.file_viewer(chip, f'{chip.getworkdir()}/{chip.design}.png')

    if tab_selected == "Graphs":
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

    # Determine if node was modified
    if state.set_key(state.SELECTED_NODE, state.get_selected_node()):
        state.set_key(state.APP_RERUN, "Node")
        state.set_key(state.SELECT_TAB, "Node")
