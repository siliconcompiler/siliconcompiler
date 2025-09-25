"""
Main entry point for the SiliconCompiler web-based dashboard using Streamlit.

This script initializes and runs the Streamlit application. It is responsible for:
- Initializing the application and session state.
- Setting up the page configuration (title, icon).
- Dynamically selecting and rendering the appropriate layout.
- Handling the auto-refresh mechanism to provide live updates.
- Triggering reruns when the underlying data changes.
"""
import streamlit

from siliconcompiler.report.dashboard.web import components
from siliconcompiler.report.dashboard.web import layouts
from siliconcompiler.report.dashboard.web import state
from siliconcompiler.report.dashboard.web import utils

import streamlit_autorefresh


if __name__ == "__main__":
    # This script is executed by the `sc-dashboard` command.
    # Initialize the Streamlit session state. This must be the first
    # Streamlit command used in the app.
    state.init()

    # Configure the page's title, icon, and other basic properties.
    components.setup_page()
    # Set up the application state, loading data from the project object.
    state.setup()

    # Dynamically select the layout function based on the current state
    # and then execute it to render the UI components for the page.
    layout = layouts.get_layout(state.get_key(state.APP_LAYOUT))
    layout()

    # Determine if a full page reload is needed.
    reload = False
    if state.get_key(state.SELECTED_JOB) == 'default':
        # Check if the underlying project process is running and update the state.
        reload = state.set_key(state.IS_RUNNING, utils.is_running(state.get_project()))

    # Set the refresh interval based on the run status.
    # Use a faster refresh rate when a job is running, and a slower one when stopped.
    if state.get_key(state.IS_RUNNING):
        update_interval = state.get_key(state.APP_RUNNING_REFRESH)
    else:
        update_interval = state.get_key(state.APP_STOPPED_REFRESH)

    # Add the auto-refresh component to the page.
    streamlit_autorefresh.st_autorefresh(interval=update_interval)

    # For debugging: print the current session state to the console.
    state.debug_print_state()

    # Check if a full re-render of the application is required. This can be
    # triggered by a data update, a manual rerun request, or a change in run status.
    if reload or state.update_manifest() or state.get_key(state.APP_RERUN):
        state.set_key(state.APP_RERUN, None)
        streamlit.rerun()
