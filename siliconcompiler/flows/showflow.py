import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A flow to show the output files generated from other flows.

    Required settings for this flow are below:

    * show_filetype : Type of file to show
    * show_filepath : Path to file to show
    * show_job : Source job name
    * show_step : Source step name
    * show_index : Source index name

    Optional settings for this flow are below:

    * show_np : Number of parallel show jobs to launch
    * show_screenshot : true/false, indicate if this should be configured as a screenshot
    '''

    chip = siliconcompiler.Chip('<topmodule>')
    chip.set('arg', 'flow', 'show_np', '3')
    chip.set('arg', 'flow', 'show_filetype', 'def')
    chip.set('arg', 'flow', 'show_filepath', 'gcd.def')
    chip.set('arg', 'flow', 'show_step', 'place')
    chip.set('arg', 'flow', 'show_index', '0')
    chip.set('arg', 'flow', 'show_job', 'job0')
    chip.set('option', 'flow', 'showflow')
    setup(chip)

    return chip

###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='showflow'):
    '''
    Setup function for 'showflow' execution flowgraph.

    Args:
        chip (object): SC Chip object
        flowname (str): name for the flow
    '''

    # Get required parameters first
    if 'show_filetype' in chip.getkeys('arg', 'flow'):
        filetype = chip.get('arg', 'flow', 'show_filetype')[0]
    else:
        raise ValueError('show_filetype is a required argument')

    sc_screenshot = False
    if 'show_screenshot' in chip.getkeys('arg', 'flow'):
        sc_screenshot = chip.get('arg', 'flow', 'show_screenshot')[0] == "true"

    # Clear old flowgraph if it exists
    if flowname in chip.getkeys('flowgraph'):
        del chip.schema.cfg['flowgraph'][flowname]

    chip.node(flowname, 'import', 'builtin', 'import')

    show_tool = chip.get('option', 'showtool', filetype)

    stepname = 'show'
    if sc_screenshot:
        stepname = 'screenshot'

    np = 1
    if 'show_np' in chip.getkeys('arg', 'flow'):
        np = int(chip.get('arg', 'flow', 'show_np')[0])

    for idx in range(np):
        chip.node(flowname, stepname, show_tool, stepname, index=idx)
        chip.edge(flowname, 'import', stepname, head_index=idx, tail_index=0)

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("showflow.png")
