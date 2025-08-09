"""
Utility functions for managing the state of tab components in the web dashboard.

This module provides helpers for controlling which tab is active, especially
when a user action (like selecting a node or a file) should automatically
switch the view to a different tab.
"""
import streamlit_antd_components as sac

from siliconcompiler.report.dashboard.web import state


def check_rerun():
    """
    Checks if the selected node or file has changed and updates the active tab accordingly.

    This function is called on each rerun to ensure that if a user selects a
    node in the flowgraph, the UI automatically switches to the "Node Information"
    tab. Similarly, if a file is selected, it switches to the "File Viewer" tab.
    """
    # If the globally selected node changes, flag a rerun to switch tabs.
    if state.set_key(state.SELECTED_NODE, state.get_selected_node()):
        state.set_key(state.APP_RERUN, "Node")

    # Based on the rerun flag, force a specific tab to be selected.
    if state.get_key(state.APP_RERUN) == "Node":
        state.set_key(state.SELECT_TAB, "Node Information")
        # Reset the component's internal state to ensure the change takes effect.
        state.del_key(state.TAB_STATE)
    elif state.get_key(state.APP_RERUN) == "File":
        state.set_key(state.SELECT_TAB, "File Viewer")
        state.del_key(state.TAB_STATE)
    else:
        # Clear the forced selection if no specific action was taken.
        state.set_key(state.SELECT_TAB, None)


def sac_tabs(tab_headings):
    """
    Renders a tab group using streamlit-antd-components and manages its state.

    This function determines which tab should be initially selected based on
    the application state and saves the user's new selection back to the state.

    Args:
        tab_headings (list[sac.Tabs.Item]): A list of tab items to display.

    Returns:
        str: The label of the currently selected tab.
    """
    index = 0

    # Determine the initial tab index based on a forced selection or the last known state.
    if state.get_key(state.SELECT_TAB):
        # A specific tab is being forced by an action (e.g., node selection).
        for n, tab in enumerate(tab_headings):
            if state.get_key(state.SELECT_TAB) == tab.label:
                index = n
                break
    elif state.get_key(state.TAB_INDEX) is not None:
        # Default to the last tab the user had open.
        index = state.get_key(state.TAB_INDEX)

    # Render the tabs component.
    tab_selected = sac.tabs(
        tab_headings,
        align='center',
        variant='outline',
        use_container_width=True,
        index=index,
        key=state.TAB_STATE)  # The key links to the component's internal state.

    # Save the index of the selected tab for the next rerun.
    for n, tab in enumerate(tab_headings):
        if tab_selected == tab.label:
            state.set_key(state.TAB_INDEX, n)
            break

    return tab_selected
