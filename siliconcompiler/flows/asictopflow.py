import siliconcompiler

from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.klayout import export


def setup(chip):
    '''A flow for stitching together hardened blocks without doing any automated
    place-and-route.

    This flow generates a GDS and a netlist for passing to a
    verification/signoff flow.
    '''
    flow = siliconcompiler.Flow(chip, 'asictopflow')

    flow.node(flow.design, 'import', surelog_parse)
    flow.node(flow.design, 'syn', syn_asic)
    flow.node(flow.design, 'export', export)

    flow.edge(flow.design, 'import', 'export')
    flow.edge(flow.design, 'import', 'syn')

    # Set default goal
    for step in flow.getkeys('flowgraph', flow.design):
        flow.set('flowgraph', flow.design, step, '0', 'goal', 'errors', 0)

    return flow


##################################################
if __name__ == "__main__":
    flow = setup(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
