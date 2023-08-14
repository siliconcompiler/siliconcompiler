import siliconcompiler
from siliconcompiler import SiliconCompilerError
import importlib


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

    if filetype not in chip.getkeys('option', 'showtool'):
        raise SiliconCompilerError(f'Show tool for {filetype} is not defined.')

    show_tool = chip.get('option', 'showtool', filetype)

    stepname = 'show'
    if screenshot:
        stepname = 'screenshot'

    # Find suitable tool
    tools = set()
    for flowg in chip.getkeys('flowgraph'):
        for step in chip.getkeys('flowgraph', flowg):
            for index in chip.getkeys('flowgraph', flowg, step):
                tool, _ = chip._get_tool_task(step, index, flow=flowg)
                if tool != show_tool:
                    continue
                try:
                    tool_module = chip._get_tool_module(step, index, flow=flowg)
                    if not tool_module:
                        continue
                    tools.add(tool_module.__name__)
                except SiliconCompilerError:
                    pass
    # If no tools found in flowgraph, check the loaded modules
    if not tools:
        for module_name in chip._get_loaded_modules().keys():
            if module_name.endswith(f".{show_tool}"):
                tools.add(module_name)

    show_task_module = None
    for tool in tools:
        tool_base = '.'.join(tool.split('.')[:-1])
        search_modules = [
            f'{tool}.{stepname}',
            f'{tool_base}.{stepname}'
        ]
        for search_module in search_modules:
            try:
                show_task_module = importlib.import_module(search_module)
                break
            except ModuleNotFoundError:
                pass

    if not show_task_module:
        raise SiliconCompilerError(f'Cannot determine {stepname} module for {show_tool}.')

    for idx in range(np):
        flow.node(flowname, stepname, show_task_module, index=idx)

    return flow


##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
