import siliconcompiler

from siliconcompiler.tools.verilator import lint as verilator_lint
from siliconcompiler.tools.slang import lint as slang_lint


###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip, tool='verilator'):
    '''
    An RTL linting flow.
    '''

    flowname = 'lintflow'
    flow = siliconcompiler.Flow(chip, flowname)

    if tool == 'verilator':
        flow.node(flowname, 'lint', verilator_lint)
    elif tool == 'slang':
        flow.node(flowname, 'lint', slang_lint)
    else:
        raise ValueError(f'Unsupported lint tool: {tool}')

    return flow


##################################################
if __name__ == "__main__":
    flow = setup(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
