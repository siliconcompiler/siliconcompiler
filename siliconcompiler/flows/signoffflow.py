import siliconcompiler

def setup(chip):
    '''A flow for running LVS/DRC signoff on a GDS layout.

    Inputs must be passed to this flow as follows::

        flow.input('<path-to-layout>.gds')
        flow.input('<path-to-netlist>.vg')
    '''
    flowname = 'signoffflow'

    flow = siliconcompiler.Flow(chip, flowname)

    # nop import since we don't need to pull in any sources
    flow.node(flowname, 'import', 'builtin', 'import')

    flow.node(flowname, 'extspice', 'magic', 'extspice')
    flow.node(flowname, 'drc', 'magic', 'drc')
    flow.node(flowname, 'lvs', 'netgen', 'lvs')
    flow.node(flowname, 'signoff', 'builtin', 'join')

    flow.edge(flowname, 'import', 'drc')
    flow.edge(flowname, 'import', 'extspice')
    flow.edge(flowname, 'extspice', 'lvs')
    flow.edge(flowname, 'lvs', 'signoff')
    flow.edge(flowname, 'drc', 'signoff')

    # Set default goal
    for step in flow.getkeys('flowgraph', flowname):
        flow.set('flowgraph', flowname, step, '0', 'goal', 'errors', 0)

    return flow

##################################################
if __name__ == "__main__":
    flow = setup(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
