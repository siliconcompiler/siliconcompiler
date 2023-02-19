import siliconcompiler

def setup(chip):
    '''A flow for stitching together hardened blocks without doing any automated
    place-and-route.

    This flow generates a GDS and a netlist for passing to a
    verification/signoff flow.
    '''
    flow = siliconcompiler.Flow(chip, 'asictopflow')

    flow.node(flow.design, 'import', 'surelog', 'import')
    flow.node(flow.design, 'syn', 'yosys', 'syn_asic')
    flow.node(flow.design, 'export', 'klayout', 'export')

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
