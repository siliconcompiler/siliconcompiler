import os
import streamlit

from siliconcompiler.report.dashboard.web import components
from siliconcompiler.report.dashboard.web.components import graph
from siliconcompiler.report.dashboard.web import state
from siliconcompiler.report.dashboard.web import utils
from siliconcompiler.report.dashboard.web.utils import file_utils
from siliconcompiler.report.dashboard.web.layouts import _common
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

    tab_selected = _common.sac_tabs(tab_headings)

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

            header_col, settings_col = \
                streamlit.columns(
                    [0.7, 0.3],
                    gap='small')
            with header_col:
                streamlit.header('Node Information')
            with settings_col:
                components.node_selector(list(node_to_step_index_map.keys()))

            if state.get_selected_node():
                step, index = node_to_step_index_map[state.get_selected_node()]
                current_file = state.get_key(state.SELECTED_FILE)
                components.node_viewer(chip, step, index, metric_dataframe)
                if state.get_key(state.SELECTED_FILE) and \
                        current_file != state.get_key(state.SELECTED_FILE):
                    state.set_key(state.APP_RERUN, "File")

    if tab_selected == "Manifest":
        components.manifest_viewer(chip)

    if tab_selected == "File Viewer":
        components.file_viewer(
            chip,
            state.get_key(state.SELECTED_FILE),
            page_key=state.SELECTED_FILE_PAGE)

    if tab_selected == "Design Preview":
        components.file_viewer(chip, f'{chip.getworkdir()}/{chip.design}.png')

    if tab_selected == "Graphs":
        graph.viewer(node_to_step_index_map)

    _common.check_rerun()
