import siliconcompiler

from siliconcompiler.flows._common import _make_docs
from siliconcompiler.tools.verilator import lint as verilator_lint
from siliconcompiler.tools.slang import lint as slang_lint


from siliconcompiler import FlowgraphSchema


class LintFlowgraph(FlowgraphSchema):
    def __init__(self, tool="slang"):
        super().__init__()
        self.set_name("lintflow")

        if tool == "slang":
            self.node("lint", slang_lint.Lint())
        elif tool == "verilator":
            self.node("lint", verilator_lint.LintTask())


###########################################################################
# Flowgraph Setup
############################################################################
def setup(tool='verilator'):
    '''
    An RTL linting flow.
    '''

    flowname = 'lintflow'
    flow = siliconcompiler.Flow(flowname)

    if tool == 'verilator':
        flow.node(flowname, 'lint', verilator_lint)
    elif tool == 'slang':
        flow.node(flowname, 'lint', slang_lint)
    else:
        raise ValueError(f'Unsupported lint tool: {tool}')

    return flow


##################################################
if __name__ == "__main__":
    chip = siliconcompiler.Chip('design')
    _make_docs(chip)
    flow = setup()
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
