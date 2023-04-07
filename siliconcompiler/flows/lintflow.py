import siliconcompiler

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
    pipe = [('import', 'surelog', 'parse'),
            ('lint', 'verilator', 'lint'),
            ('export', 'nop', 'nop')]

    prevstep = None
    for step, tool, task in pipe:
        flow.node(flowname, step, tool, task)
        if prevstep:
            flow.edge(flowname, prevstep, step)
        prevstep = step

    return flow

##################################################
if __name__ == "__main__":
    flow = setup(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
