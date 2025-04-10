import streamlit_antd_components as sac

from siliconcompiler.report.dashboard.web import state


def check_rerun():
    # Determine if node was modified
    if state.set_key(state.SELECTED_NODE, state.get_selected_node()):
        state.set_key(state.APP_RERUN, "Node")

    if state.get_key(state.APP_RERUN) == "Node":
        state.set_key(state.SELECT_TAB, "Node Information")
        state.del_key(state.TAB_STATE)
    elif state.get_key(state.APP_RERUN) == "File":
        state.set_key(state.SELECT_TAB, "File Viewer")
        state.del_key(state.TAB_STATE)
    else:
        state.set_key(state.SELECT_TAB, None)


def sac_tabs(tab_headings):
    index = 0

    if state.get_key(state.SELECT_TAB):
        for n, tab in enumerate(tab_headings):
            if state.get_key(state.SELECT_TAB) == tab.label:
                index = n
    elif state.get_key(state.TAB_INDEX) is not None:
        index = state.get_key(state.TAB_INDEX)

    tab_selected = sac.tabs(
        tab_headings,
        align='center',
        variant='outline',
        use_container_width=True,
        index=index,
        key=state.TAB_STATE)

    for n, tab in enumerate(tab_headings):
        if tab_selected == tab.label:
            state.set_key(state.TAB_INDEX, n)

    return tab_selected
