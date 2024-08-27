import siliconcompiler

from siliconcompiler.tools.icarus import compile as icarus_compile
from siliconcompiler.tools.verilator import compile as verilator_compile
from siliconcompiler.tools.execute import exec_input


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    chip.set('input', 'rtl', 'netlist', 'test')
    return setup(np=5)


#############################################################################
# Flowgraph Setup
#############################################################################
def setup(flowname='dvflow',
          tool='icarus',
          np=1):
    '''
    A configurable constrained random stimulus DV flow.

    The verification pipeline includes the following steps:

    * **compile**: RTL sources are compiled into object form (once)
    * **sim**: Compiled RTL is exercised using generated test

    The dvflow can be parametrized using a single 'np' parameter.
    Setting 'np' > 1 results in multiple independent verification
    pipelines to be launched.

    This flow is a WIP
    '''

    flow = siliconcompiler.Flow(flowname)

    tasks = {
        'compile': None,
        'sim': None
    }

    if tool == 'icarus':
        tasks['compile'] = icarus_compile
        tasks['sim'] = exec_input
    elif tool == 'verilator':
        tasks['compile'] = verilator_compile
        tasks['sim'] = exec_input
    else:
        raise ValueError(f'{tool} is not a supported tool for {flowname}: icarus')

    flowpipe = [
        'compile',
        'sim'
    ]
    flow_np = {
        'compile': 1,
        'sim': np
    }

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
    chip = siliconcompiler.Chip('design')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
