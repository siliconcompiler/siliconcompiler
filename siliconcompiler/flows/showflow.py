import siliconcompiler

############################################################################
# DOCS
############################################################################
def make_docs(chip):
    return setup(chip, filetype='gds', np=3)

###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='showflow', filetype=None, screenshot=False, np=1):
    '''
    A flow to show the output files generated from other flows.

    Required settings for this flow are below:

    * filetype : Type of file to show

    Optional settings for this flow are below:

    * np : Number of parallel show jobs to launch
    * screenshot : true/false, indicate if this should be configured as a screenshot
    '''

    flow = siliconcompiler.Flow(chip, flowname)

    # Get required parameters first
    if not filetype:
        raise ValueError('filetype is a required argument')

    flow.node(flowname, 'import', 'builtin', 'import')

    show_tool = chip.get('option', 'showtool', filetype)

    stepname = 'show'
    if screenshot:
        stepname = 'screenshot'

    for idx in range(np):
        flow.node(flowname, stepname, show_tool, stepname, index=idx)
        flow.edge(flowname, 'import', stepname, head_index=idx, tail_index=0)

    return flow

##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
