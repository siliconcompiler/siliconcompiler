import siliconcompiler
import re

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A configurable RTL linting flow.

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('option', 'flow', 'lintflow')
    setup(chip)
    return chip

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

    # Linear flow, up until branch to run parallel verification steps.
    pipe = [{'import' : 'surelog'},
            {'lint' : 'verilator'},
            {'export' : 'nop'}]

    for i,val in enumerate(pipe):
        step = list(val.keys())[0]
        tool = pipe[i][step]
        chip.node(flowname, step, tool)
        if step != 'import':
            chip.edge(flowname, prevstep, step)
        prevstep = step

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("lintflow.png")
