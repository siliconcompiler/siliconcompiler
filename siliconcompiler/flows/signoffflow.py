import siliconcompiler

from siliconcompiler.tools.magic import extspice
from siliconcompiler.tools.magic import drc
from siliconcompiler.tools.netgen import lvs
from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import join


def make_docs(chip):
    chip.set('input', 'netlist', 'verilog', 'test')
    return setup(chip)


def setup(chip):
    '''A flow for running LVS/DRC signoff on a GDS layout.

    Inputs must be passed to this flow as follows::

        flow.input('<path-to-layout>.gds')
        flow.input('<path-to-netlist>.vg')
    '''
    flowname = 'signoffflow'

    flow = siliconcompiler.Flow(chip, flowname)

    # nop import since we don't need to pull in any sources
    flow.node(flowname, 'import', nop)

    flow.node(flowname, 'extspice', extspice)
    flow.node(flowname, 'drc', drc)
    flow.node(flowname, 'lvs', lvs)
    flow.node(flowname, 'signoff', join)

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
    chip = siliconcompiler.Chip('design')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
