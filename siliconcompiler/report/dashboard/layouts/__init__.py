from . import vertical_flowgraph
from . import vertical_flowgraph_sac_tabs
from . import vertical_flowgraph_node_tab


_layouts = {
    "vertical_flowgraph": vertical_flowgraph.layout,
    "vertical_flowgraph_sac_tabs": vertical_flowgraph_sac_tabs.layout,
    "vertical_flowgraph_node_tab": vertical_flowgraph_node_tab.layout,
}


def get_default_layout():
    return "vertical_flowgraph"


def get_all_layouts():
    return sorted(list(_layouts.keys()))


def get_layout(name):
    if name in _layouts:
        return _layouts[name]

    raise ValueError(f"{name} not supported")
