import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    chip = siliconcompiler.Chip('<design>')
    chip.set('option', 'flow', 'lintflow')
    return setup(chip)

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
