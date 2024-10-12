from siliconcompiler.report.dashboard.layouts import vertical_flowgraph

__LAYOUTS = {
    "vertical_flowgraph": vertical_flowgraph.layout
}


def get_all_layouts():
    return list(__LAYOUTS.keys())


def get_layout(name):
    if name not in __LAYOUTS:
        raise ValueError(f"{name} is not a layout")

    return __LAYOUTS[name]
