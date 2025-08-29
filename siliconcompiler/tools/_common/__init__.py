###########################################################################
def get_tool_task(chip, step, index, flow=None):
    '''
    Helper function to get the name of the tool and task associated with a given step/index.
    '''
    if not flow:
        flow = chip.get('option', 'flow')

    tool = chip.get('flowgraph', flow, step, index, 'tool')
    task = chip.get('flowgraph', flow, step, index, 'task')
    return tool, task
