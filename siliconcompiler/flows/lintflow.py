import siliconcompiler

from siliconcompiler.tools.surelog import parse as surelog_parse
from siliconcompiler.tools.verilator import lint


###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip):
    '''
    An RTL linting flow.
    '''

    flowname = 'lintflow'
    flow = siliconcompiler.Flow(chip, flowname)

    # Linear flow, up until branch to run parallel verification steps.
    pipe = [('import', surelog_parse),
            ('lint', lint)]

    prevstep = None
    for step, task in pipe:
        flow.node(flowname, step, task)
        if prevstep:
            flow.edge(flowname, prevstep, step)
        prevstep = step

    return flow


##################################################
if __name__ == "__main__":
    flow = setup(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
