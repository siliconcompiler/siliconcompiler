import siliconcompiler

from siliconcompiler.tools.verilator import lint
from siliconcompiler.flows._common import _make_docs


###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip):
    '''
    An RTL linting flow.
    '''

    flowname = 'lintflow'
    flow = siliconcompiler.Flow(chip, flowname)

    flow.node(flowname, 'lint', lint)

    return flow


##################################################
if __name__ == "__main__":
    chip = siliconcompiler.Chip('design')
    _make_docs(chip)
    flow = setup(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
