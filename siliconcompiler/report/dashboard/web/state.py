import argparse
import json
import os
import streamlit
import streamlit_javascript
import fasteners

from siliconcompiler import Chip


DISPLAY_FLOWGRAPH = "show_flowgraph"
SELECTED_JOB = "selected_job"
SELECTED_NODE = "selected_node"
# This is needed until the graph supports setting a selected node
SELECTED_FLOWGRAPH_NODE = "selected_flowgraph_node"
SELECTED_SELECTOR_NODE = "selected_selector_node"
NODE_SOURCE = "node_source"
SELECTED_FILE = "selected_file"
SELECTED_FILE_PAGE = "selected_file_page"
LOADED_CHIPS = "loaded_chips"
UI_WIDTH = "ui_width"
MANIFEST_FILE = "manifest_file"
MANIFEST_LOCK = "manifest_lock"
MANIFEST_TIME = "manifest_time"
IS_RUNNING = "is_flow_running"
GRAPH_JOBS = "graph_jobs"
APP_LAYOUT = "app_layout"
APP_RERUN = "app_rerun"
APP_RUNNING_REFRESH = "app_running_refresh"
APP_STOPPED_REFRESH = "app_stopped_refresh"
MAX_DICT_ITEMS_TO_SHOW = "max_dict_items"
MAX_FILE_LINES_TO_SHOW = "max_file_lines"
SELECT_TAB = "select_tab"
TAB_INDEX = "tab-index"
TAB_STATE = "tab-state"

_DEBUG = False
DEVELOPER = False


def _add_default(key, value):
    if key not in streamlit.session_state:
        streamlit.session_state[key] = value


def update_manifest():
    file_time = os.stat(get_key(MANIFEST_FILE)).st_mtime

    if get_key(MANIFEST_TIME) != file_time:
        chip = Chip(design='')

        with get_key(MANIFEST_LOCK):
            chip.read_manifest(get_key(MANIFEST_FILE))
        set_key(MANIFEST_TIME, file_time)
        debug_print("Read manifest", get_key(MANIFEST_FILE))

        add_chip("default", chip)

        for history in chip.getkeys('history'):
            history_chip = Chip(design='')
            history_chip.schema = chip.schema.history(history).copy()
            history_chip.set('design', chip.design)
            add_chip(history, history_chip)

        return True
    return False


def init():
    _add_default(DISPLAY_FLOWGRAPH, True)
    _add_default(SELECTED_JOB, None)
    _add_default(SELECTED_NODE, None)
    _add_default(SELECTED_FLOWGRAPH_NODE, None)
    _add_default(SELECTED_SELECTOR_NODE, None)
    _add_default(NODE_SOURCE, None)
    _add_default(SELECTED_FILE, None)
    _add_default(SELECTED_FILE_PAGE, None)
    _add_default(LOADED_CHIPS, {})
    _add_default(MANIFEST_FILE, None)
    _add_default(MANIFEST_LOCK, None)
    _add_default(MANIFEST_TIME, None)
    _add_default(IS_RUNNING, False)
    _add_default(GRAPH_JOBS, None)
    _add_default(UI_WIDTH, None)
    _add_default(APP_LAYOUT, "vertical_flowgraph_sac_tabs")
    _add_default(APP_RERUN, None)
    _add_default(APP_RUNNING_REFRESH, 2 * 1000)
    _add_default(APP_STOPPED_REFRESH, 30 * 1000)
    _add_default(MAX_DICT_ITEMS_TO_SHOW, 100)
    _add_default(MAX_FILE_LINES_TO_SHOW, 100)
    _add_default(SELECT_TAB, None)
    _add_default(TAB_INDEX, 0)

    parser = argparse.ArgumentParser('dashboard')
    parser.add_argument('cfg', nargs='?')
    args = parser.parse_args()

    if not args.cfg:
        raise ValueError('configuration not provided')

    if not get_key(LOADED_CHIPS):
        # First time through

        with open(args.cfg, 'r') as f:
            config = json.load(f)

        set_key(MANIFEST_FILE, config["manifest"])
        set_key(MANIFEST_LOCK, fasteners.InterProcessLock(config["lock"]))

        update_manifest()
        chip = get_chip("default")
        for graph_info in config['graph_chips']:
            file_path = graph_info['path']
            graph_chip = Chip(design='')
            graph_chip.read_manifest(file_path)
            graph_chip.unset('arg', 'step')
            graph_chip.unset('arg', 'index')

            if graph_info['cwd']:
                graph_chip.cwd = graph_info['cwd']

            add_chip(os.path.basename(file_path), graph_chip)

        chip_step = chip.get('arg', 'step')
        chip_index = chip.get('arg', 'index')

        if chip_step and chip_index:
            set_key(SELECTED_NODE, f'{chip_step}{chip_index}')

    chip = get_chip("default")
    chip.unset('arg', 'step')
    chip.unset('arg', 'index')

    if not get_key(SELECTED_JOB):
        set_key(SELECTED_JOB, "default")


def setup():
    with streamlit.empty():
        # get width
        set_key(UI_WIDTH, streamlit_javascript.st_javascript("window.innerWidth"))
        # replace with a empty container to avoid adding a gap at the top
        streamlit.empty()

    set_key(NODE_SOURCE, None)


def get_chip(job=None):
    if not job:
        job = get_key(SELECTED_JOB)
    return get_key(LOADED_CHIPS)[job]


def add_chip(name, chip):
    streamlit.session_state[LOADED_CHIPS][name] = chip


def get_chips():
    chips = list(get_key(LOADED_CHIPS).keys())
    chips.remove('default')
    chips.insert(0, 'default')
    return chips


def get_selected_node():
    if get_key(NODE_SOURCE) == "flowgraph":
        return get_key(SELECTED_FLOWGRAPH_NODE)

    if get_key(NODE_SOURCE) == "selector":
        return get_key(SELECTED_SELECTOR_NODE)

    return get_key(SELECTED_NODE)


def get_key(key):
    return streamlit.session_state[key]


def set_key(key, value):
    changed = value != streamlit.session_state[key]
    if changed:
        debug_print("set_key()", key, "changed", streamlit.session_state[key], "->", value)
        streamlit.session_state[key] = value
        return True
    return False


def del_key(key):
    debug_print("del_key()", key)
    if key in streamlit.session_state:
        del streamlit.session_state[key]


def compute_component_size(minimum, requested_px):
    ui_width = get_key(UI_WIDTH)

    if ui_width > 0:
        return min(requested_px / ui_width, minimum)

    return minimum


def debug_print(*args):
    if not _DEBUG:
        return

    print(*args)


def debug_print_state():
    if not _DEBUG:
        return

    for n, key in enumerate(sorted(streamlit.session_state.keys())):
        value = streamlit.session_state[key]
        print("state", n, key, type(value), value)
    print()
