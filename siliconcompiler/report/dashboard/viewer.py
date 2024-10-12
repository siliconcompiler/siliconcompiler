import streamlit

from siliconcompiler.report.dashboard import components
from siliconcompiler.report.dashboard import layouts
from siliconcompiler.report.dashboard import state
from siliconcompiler.report.dashboard import utils

import streamlit_autorefresh


if __name__ == "__main__":
    # opened by running command in siliconcompiler/apps/sc_dashboard.py
    state.init()

    components.setup_page()
    state.setup()

    layout = layouts.get_layout(state.get_key(state.APP_LAYOUT))
    layout()

    reload = False
    if state.get_key(state.SELECTED_JOB) == 'default':
        reload = state.set_key(state.IS_RUNNING, utils.is_running(state.get_chip()))

    if state.get_key(state.IS_RUNNING):
        update_interval = state.get_key(state.APP_RUNNING_REFRESH)
    else:
        update_interval = state.get_key(state.APP_STOPPED_REFRESH)

    streamlit_autorefresh.st_autorefresh(interval=update_interval)

    state.debug_print_state()

    if reload or state.update_manifest() or state.get_key(state.APP_RERUN):
        state.set_key(state.APP_RERUN, None)
        streamlit.rerun()
