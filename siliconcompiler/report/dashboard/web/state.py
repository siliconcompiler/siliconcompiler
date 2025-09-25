"""
Manages the session state for the SiliconCompiler web dashboard.

This module defines the keys used in Streamlit's session state and provides
a set of utility functions to initialize, access, and modify that state.
It is the central point for managing UI state, loaded data (project manifests),
and application configuration throughout the user's session.

The main functions are:
- init(): Parses command-line arguments and sets up the initial session state.
- setup(): Performs per-rerun setup, like capturing UI dimensions.
- update_manifest(): Checks for changes in the manifest file and reloads data.
- A set of getters and setters (get_key, set_key, etc.) for safe access
  to the session state.
"""
import argparse
import fasteners
import json
import os
import streamlit
import streamlit_javascript

from siliconcompiler import Project

# --- State Keys ---
# These constants define the keys used to store and access data in
# streamlit.session_state, ensuring consistency across the application.

# UI Component State
DISPLAY_FLOWGRAPH = "show_flowgraph"
SELECTED_JOB = "selected_job"
SELECTED_NODE = "selected_node"
# The following keys differentiate the source of a node selection, as multiple
# UI components (the graph, a dropdown) can select a node.
SELECTED_FLOWGRAPH_NODE = "selected_flowgraph_node"
SELECTED_SELECTOR_NODE = "selected_selector_node"
NODE_SOURCE = "node_source"
SELECTED_FILE = "selected_file"
SELECTED_FILE_PAGE = "selected_file_page"
UI_WIDTH = "ui_width"
SELECT_TAB = "select_tab"
TAB_INDEX = "tab-index"
TAB_STATE = "tab-state"

# Data State
LOADED_PROJECTS = "loaded_projects"
MANIFEST_FILE = "manifest_file"
MANIFEST_LOCK = "manifest_lock"
MANIFEST_TIME = "manifest_time"
IS_RUNNING = "is_flow_running"
GRAPH_JOBS = "graph_jobs"

# Application Configuration & Control
APP_LAYOUT = "app_layout"
APP_RERUN = "app_rerun"
APP_RUNNING_REFRESH = "app_running_refresh"
APP_STOPPED_REFRESH = "app_stopped_refresh"
MAX_DICT_ITEMS_TO_SHOW = "max_dict_items"
MAX_FILE_LINES_TO_SHOW = "max_file_lines"

# --- Debugging ---
_DEBUG = False
DEVELOPER = False


def _add_default(key, value):
    """
    Initializes a key in the session state if it doesn't already exist.

    Args:
        key (str): The key to add to the session state.
        value: The default value to assign if the key is not present.
    """
    if key not in streamlit.session_state:
        streamlit.session_state[key] = value


def update_manifest():
    """
    Checks for updates to the main manifest file and reloads it if necessary.

    Compares the current file modification time with the stored time. If they
    differ, it re-reads the manifest, re-populates the project objects (including
    history), and updates the timestamp in the session state.

    Returns:
        bool: True if the manifest was updated, False otherwise.
    """
    file_time = os.stat(get_key(MANIFEST_FILE)).st_mtime

    if get_key(MANIFEST_TIME) != file_time:
        with get_key(MANIFEST_LOCK):
            proj = Project.from_manifest(filepath=get_key(MANIFEST_FILE))
        set_key(MANIFEST_TIME, file_time)
        debug_print("Read manifest", get_key(MANIFEST_FILE))

        add_project("default", proj)

        # Load historical runs from the manifest
        for history in proj.getkeys('history'):
            add_project(history, proj.history(history).copy())

        return True
    return False


def init():
    """
    Initializes the application's session state on first run.

    This function sets default values for all state keys, parses command-line
    arguments to find the dashboard configuration file, and loads the initial
    set of project manifests.
    """
    # Set default values for all session state keys.
    _add_default(DISPLAY_FLOWGRAPH, True)
    _add_default(SELECTED_JOB, None)
    _add_default(SELECTED_NODE, None)
    _add_default(SELECTED_FLOWGRAPH_NODE, None)
    _add_default(SELECTED_SELECTOR_NODE, None)
    _add_default(NODE_SOURCE, None)
    _add_default(SELECTED_FILE, None)
    _add_default(SELECTED_FILE_PAGE, None)
    _add_default(LOADED_PROJECTS, {})
    _add_default(MANIFEST_FILE, None)
    _add_default(MANIFEST_LOCK, None)
    _add_default(MANIFEST_TIME, None)
    _add_default(IS_RUNNING, False)
    _add_default(GRAPH_JOBS, None)
    _add_default(UI_WIDTH, None)
    _add_default(APP_LAYOUT, "vertical_flowgraph_sac_tabs")
    _add_default(APP_RERUN, None)
    _add_default(APP_RUNNING_REFRESH, 2 * 1000)  # 2 seconds
    _add_default(APP_STOPPED_REFRESH, 30 * 1000)  # 30 seconds
    _add_default(MAX_DICT_ITEMS_TO_SHOW, 100)
    _add_default(MAX_FILE_LINES_TO_SHOW, 100)
    _add_default(SELECT_TAB, None)
    _add_default(TAB_INDEX, 0)

    # Parse command-line arguments to get the config file path.
    parser = argparse.ArgumentParser('dashboard')
    parser.add_argument('cfg', nargs='?')
    args = parser.parse_args()

    if not args.cfg:
        raise ValueError('Dashboard configuration not provided via command line.')

    # On the very first run, load the configuration and initial data.
    if not get_key(LOADED_PROJECTS):
        with open(args.cfg, 'r') as f:
            config = json.load(f)

        set_key(MANIFEST_FILE, config["manifest"])
        set_key(MANIFEST_LOCK, fasteners.InterProcessLock(config["lock"]))

        update_manifest()
        project = get_project("default")

        # Load any additional graph-related projects specified in the config.
        for graph_info in config['graph_projects']:
            file_path = graph_info['path']
            graph_project = Project.from_manifest(filepath=file_path)
            graph_project.unset('arg', 'step')
            graph_project.unset('arg', 'index')

            if graph_info['cwd']:
                graph_project._Project__cwd = graph_info['cwd']

            add_project(os.path.basename(file_path), graph_project)

        # Pre-select a node if specified in the project's arguments.
        project_step = project.get('arg', 'step')
        project_index = project.get('arg', 'index')
        if project_step and project_index:
            set_key(SELECTED_NODE, f'{project_step}/{project_index}')

    # Clean up args for subsequent runs.
    project = get_project("default")
    project.unset('arg', 'step')
    project.unset('arg', 'index')

    # Ensure a job is selected.
    if not get_key(SELECTED_JOB):
        set_key(SELECTED_JOB, "default")


def setup():
    """
    Performs setup tasks required on every page rerun.
    """
    # Use a javascript call to get the browser window's current width.
    with streamlit.empty():
        set_key(UI_WIDTH, streamlit_javascript.st_javascript("window.innerWidth"))
        # Replace with an empty container to avoid adding a visual gap at the top.
        streamlit.empty()

    # Reset the node source on each rerun.
    set_key(NODE_SOURCE, None)


def get_project(job=None):
    """
    Retrieves a loaded project object from the session state.

    Args:
        job (str, optional): The name of the job/project to retrieve.
                             Defaults to the currently selected job.

    Returns:
        project: The requested project object.
    """
    if not job:
        job = get_key(SELECTED_JOB)
    return get_key(LOADED_PROJECTS)[job]


def add_project(name, project):
    """
    Adds a project object to the session state.

    Args:
        name (str): The name to associate with the project (e.g., 'default' or a history ID).
        project (Project): The project object to store.
    """
    streamlit.session_state[LOADED_PROJECTS][name] = project


def get_projects():
    """
    Gets a list of all loaded project names.

    Returns:
        list: A list of strings, with 'default' guaranteed to be the first element.
    """
    projects = list(get_key(LOADED_PROJECTS).keys())
    projects.remove('default')
    projects.insert(0, 'default')
    return projects


def get_selected_node():
    """
    Gets the currently selected node, accounting for the selection source.

    Returns:
        str or None: The identifier of the selected node (e.g., 'import/0').
    """
    if get_key(NODE_SOURCE) == "flowgraph":
        return get_key(SELECTED_FLOWGRAPH_NODE)

    if get_key(NODE_SOURCE) == "selector":
        return get_key(SELECTED_SELECTOR_NODE)

    return get_key(SELECTED_NODE)


def get_key(key):
    """
    Generic getter for a value from the session state.

    Args:
        key (str): The key of the value to retrieve.

    Returns:
        The value associated with the key.
    """
    return streamlit.session_state[key]


def set_key(key, value):
    """
    Generic setter for a value in the session state.

    This function checks if the new value is different from the old one
    before setting it, which helps in preventing unnecessary reruns.

    Args:
        key (str): The key of the value to set.
        value: The new value to assign.

    Returns:
        bool: True if the value was changed, False otherwise.
    """
    changed = value != streamlit.session_state[key]
    if changed:
        debug_print("set_key()", key, "changed", streamlit.session_state[key], "->", value)
        streamlit.session_state[key] = value
        return True
    return False


def del_key(key):
    """
    Deletes a key from the session state if it exists.

    Args:
        key (str): The key to delete.
    """
    debug_print("del_key()", key)
    if key in streamlit.session_state:
        del streamlit.session_state[key]


def compute_component_size(minimum, requested_px):
    """
    Utility to calculate component sizes based on UI width.

    Args:
        minimum (float): The minimum size as a fraction of the width.
        requested_px (int): The desired size in pixels.

    Returns:
        float: The calculated size as a fraction of the width.
    """
    ui_width = get_key(UI_WIDTH)

    if ui_width > 0:
        return min(requested_px / ui_width, minimum)

    return minimum


def debug_print(*args):
    """Prints messages to the console only if the _DEBUG flag is True."""
    if not _DEBUG:
        return
    print(*args)


def debug_print_state():
    """Prints the entire Streamlit session state to the console for debugging."""
    if not _DEBUG:
        return

    for n, key in enumerate(sorted(streamlit.session_state.keys())):
        value = streamlit.session_state[key]
        print("state", n, key, type(value), value)
    print()
