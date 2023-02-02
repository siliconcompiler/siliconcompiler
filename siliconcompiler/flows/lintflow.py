import siliconcompiler
from siliconcompiler import Flow

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A configurable RTL linting flow.

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('option', 'flow', 'lintflow')
    return setup(chip)

###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip):
    '''
    Setup function RTL linting flow

    Args:
        chip (object): SC Chip object

    '''

    flowname = 'lintflow'
    flow = Flow(chip, flowname)

    # Linear flow, up until branch to run parallel verification steps.
    pipe = [('import', 'surelog', 'import'),
            ('lint', 'verilator', 'lint'),
            ('export', 'nop', 'nop')]

    for step, tool, task in pipe:
        flow.node(flowname, step, tool, task)
        if task != 'import':
            flow.edge(flowname, prevstep, step)
        prevstep = step

    return flow

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("lintflow.png")
