"""
A registry for different dashboard layouts.

This module imports layout functions from other files and provides a centralized
way to access them by name. This allows the main application to dynamically
switch between different UI arrangements.
"""
from siliconcompiler.report.dashboard.web.layouts import vertical_flowgraph
from siliconcompiler.report.dashboard.web.layouts import vertical_flowgraph_sac_tabs
from siliconcompiler.report.dashboard.web.layouts import vertical_flowgraph_node_tab

# A dictionary mapping layout names to their corresponding layout functions.
__LAYOUTS = {
    "vertical_flowgraph": vertical_flowgraph.layout,
    "vertical_flowgraph_sac_tabs": vertical_flowgraph_sac_tabs.layout,
    "vertical_flowgraph_node_tab": vertical_flowgraph_node_tab.layout
}


def get_all_layouts():
    """
    Retrieves a list of all available layout names.

    Returns:
        list[str]: A list of strings, where each string is the name of a
                   registered layout.
    """
    return list(__LAYOUTS.keys())


def get_layout(name):
    """
    Retrieves a layout function by its registered name.

    Args:
        name (str): The name of the layout to retrieve.

    Returns:
        function: The corresponding layout function.

    Raises:
        ValueError: If the provided name does not match any registered layout.
    """
    if name not in __LAYOUTS:
        raise ValueError(f"'{name}' is not a valid layout. "
                         f"Available layouts: {', '.join(get_all_layouts())}")

    return __LAYOUTS[name]
