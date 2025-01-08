import siliconcompiler
from siliconcompiler import SiliconCompilerError


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    from siliconcompiler.targets import freepdk45_demo
    chip.use(freepdk45_demo)
    return setup(filetype='gds', showtools=chip._showtools, np=3)


###########################################################################
# Flowgraph Setup
############################################################################
def setup(flowname='showflow', filetype=None, screenshot=False, showtools=None, np=1):
    '''
    A flow to show the output files generated from other flows.

    Required settings for this flow are below:

    * filetype : Type of file to show

    Optional settings for this flow are below:

    * np : Number of parallel show jobs to launch
    * screenshot : true/false, indicate if this should be configured as a screenshot
    * showtools: dictionary of file extensions with the associated show and screenshot tasks
    '''

    flow = siliconcompiler.Flow(flowname)

    # Get required parameters first
    if not filetype:
        raise ValueError('filetype is a required argument')

    if not showtools:
        raise ValueError('showtools is a required argument')

    if filetype not in showtools:
        raise SiliconCompilerError(f'Show tool for {filetype} is not defined.')

    show_tool = showtools[filetype]

    stepname = 'show'
    if screenshot:
        stepname = 'screenshot'

    if stepname not in show_tool:
        raise SiliconCompilerError(f'{stepname} for {filetype} is not defined.')

    for idx in range(np):
        flow.node(flowname, stepname, show_tool[stepname], index=idx)

    return flow


##################################################
if __name__ == "__main__":
    chip = siliconcompiler.Chip('design')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
