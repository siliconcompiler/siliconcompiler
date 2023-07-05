import siliconcompiler

from siliconcompiler.tools.icarus import compile as icarus_compile
from siliconcompiler.tools.execute import exec_input


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    return setup(chip, np=5)


#############################################################################
# Flowgraph Setup
#############################################################################
def setup(chip,
          flowname='dvflow',
          tool='icarus',
          np=1):
    '''
    A configurable constrained random stimulus DV flow.

    The verification pipeline includes the followins teps:

    * **compile**: RTL sources are compiled into object form (once)
    * **sim**: Compiled RTL is exercised using generated test

    The dvflow can be parametrized using a single 'np' parameter.
    Setting 'np' > 1 results in multiple independent verificaiton
    pipelines to be launched.

    This flow is a WIP
    '''

    flow = siliconcompiler.Flow(chip, flowname)

    tasks = {
        'compile': None,
        'sim': None
    }

    if tool == 'icarus':
        tasks['compile'] = icarus_compile
        tasks['sim'] = exec_input
        flowpipe = [
            'compile',
            'sim'
        ]
        flow_np = {
            'compile': 1,
            'sim': np
        }
    else:
        raise ValueError(f'{tool} is not a supported tool for {flowname}: icarus')

    prevstep = None
    # Flow setup
    for step in flowpipe:
        task = tasks[step]

        parallel = flow_np[step]

        for n in range(parallel):
            flow.node(flowname, step, task, index=n)

            if prevstep:
                flow.edge(flowname, prevstep, step, tail_index=0, head_index=n)

        prevstep = step

    return flow


##################################################
if __name__ == "__main__":
    flow = make_docs(siliconcompiler.Chip('<flow>'))
    flow.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
