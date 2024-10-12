import streamlit
from siliconcompiler.report import report

from siliconcompiler.report.dashboard import components
from siliconcompiler.report.dashboard import layouts
from siliconcompiler.report.dashboard import state
from siliconcompiler.report.dashboard import utils

import streamlit_autorefresh


if __name__ == "__main__":
    # opened by running command in siliconcompiler/apps/sc_dashboard.py
    state.init()

    chip = state.get_chip()

    components.setup_page(chip.design)
    state.setup()

    metric_dataframe = report.make_metric_dataframe(chip)
    node_to_step_index_map, metric_dataframe = \
        utils.make_node_to_step_index_map(chip, metric_dataframe)
    metric_to_metric_unit_map, metric_dataframe = \
        utils.make_metric_to_metric_unit_map(metric_dataframe)
    manifest = report.make_manifest(chip)
    layouts.vertical_flowgraph(
        chip,
        metric_dataframe,
        node_to_step_index_map,
        metric_to_metric_unit_map,
        manifest)

    interval_count = None
    reload = False
    if state.get_key(state.SELECTED_JOB) == 'default':
        reload = state.set_key(state.IS_RUNNING, utils.is_running(chip))

        if state.get_key(state.IS_RUNNING):
            # only activate timer if flow is running
            interval_count = streamlit_autorefresh.st_autorefresh(
                interval=2 * 1000)

    if reload or state.update_manifest():
        streamlit.rerun()

    state.debug_print("Interval count", interval_count)
    state.debug_print_state()
