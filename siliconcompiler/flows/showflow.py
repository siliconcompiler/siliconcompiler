import siliconcompiler
from siliconcompiler import SiliconCompilerError


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    chip.load_target('freepdk45_demo')
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

    if filetype not in chip._showtools:
        raise SiliconCompilerError(f'Show tool for {filetype} is not defined.')

    show_tool = chip._showtools[filetype]

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
