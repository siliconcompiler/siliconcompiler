from siliconcompiler.report.dashboard.layouts import vertical_flowgraph
from siliconcompiler.report.dashboard.layouts import vertical_flowgraph_sac_tabs

__LAYOUTS = {
    "vertical_flowgraph": vertical_flowgraph.layout,
    "vertical_flowgraph_sac_tabs": vertical_flowgraph_sac_tabs.layout
}


def get_all_layouts():
    return list(__LAYOUTS.keys())


def get_layout(name):
    if name not in __LAYOUTS:
        raise ValueError(f"{name} is not a layout")

    return __LAYOUTS[name]
