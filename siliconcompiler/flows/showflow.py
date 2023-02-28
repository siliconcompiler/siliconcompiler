import siliconcompiler
import importlib
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

    flow.node(flowname, 'import', siliconcompiler, 'import')

    if filetype not in chip.getkeys('option', 'showtool'):
        raise SiliconCompilerError(f'Show tool for {filetype} is not defined.')
    show_tool = chip.get('option', 'showtool', filetype)

    show_tool_module = chip._lookup_toolmodule_by_name(show_tool)
    if not show_tool_module:
        # Search for module
        for search_module in [f'siliconcompiler.tools.{show_tool}.{show_tool}',
                              f'siliconcompiler.tools.{show_tool}',
                              show_tool]:
            try:
               show_tool_module = importlib.import_module(search_module)
               break
            except ModuleNotFoundError:
                pass

    if not show_tool_module:
        raise SiliconCompilerError(f'Cannot determine tool module for {show_tool}.')

    stepname = 'show'
    if screenshot:
        stepname = 'screenshot'

    for idx in range(np):
        flow.node(flowname, stepname, show_tool_module, stepname, index=idx)
        flow.edge(flowname, 'import', stepname, head_index=idx, tail_index=0)

    return flow

##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
