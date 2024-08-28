import siliconcompiler

from siliconcompiler.flows._common import setup_multiple_frontends
from siliconcompiler.flows._common import _make_docs

from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.opensta import timing

from siliconcompiler.tools.builtin import minimum


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    n = 3
    _make_docs(chip)
    return setup(syn_np=n, timing_np=n)


###########################################################################
# Flowgraph Setup
############################################################################
def setup(flowname='synflow',
          syn_np=1,
          timing_np=1):
    '''
    A configurable ASIC synthesys flow with static timing.

    The 'synflow' includes the stages below. The steps syn have
    minimization associated with them.
    To view the flowgraph, see the .png file.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Translates RTL to netlist using Yosys
    * **timing**: Create timing reports of design

    The syn and timing steps supports per process
    options that can be set up by setting 'syn_np' or 'timing_np'
    arg to a value > 1, as detailed below:

    * syn_np : Number of parallel synthesis jobs to launch
    * timing_np : Number of parallel timing jobs to launch
    '''

    flow = siliconcompiler.Flow(flowname)

    # Linear flow, up until branch to run parallel verification steps.
    longpipe = ['syn',
                'synmin',
                'timing']

    # step --> task
    tasks = {
        'syn': syn_asic,
        'synmin': minimum,
        'timing': timing
    }

    np = {
        "syn": syn_np,
        "timing": timing_np
    }

    prevstep = None
    # Remove built in steps where appropriate
    flowpipe = []
    for step in longpipe:
        task = tasks[step]
        if task == minimum:
            if prevstep in np and np[prevstep] > 1:
                flowpipe.append(step)
        else:
            flowpipe.append(step)
        prevstep = step

    flowtasks = []
    for step in flowpipe:
        flowtasks.append((step, tasks[step]))

    # Programmatically build linear portion of flowgraph and fanin/fanout args
    prevstep = setup_multiple_frontends(flow)
    for step, task in flowtasks:
        fanout = 1
        if step in np:
            fanout = np[step]
        # create nodes
        for index in range(fanout):
            # nodes
            flow.node(flowname, step, task, index=index)

            # edges
            if task == minimum:
                fanin = 1
                if prevstep in np:
                    fanin = np[prevstep]
                for i in range(fanin):
                    flow.edge(flowname, prevstep, step, tail_index=i)
            elif prevstep:
                flow.edge(flowname, prevstep, step, head_index=index)

            # metrics
            goal_metrics = ()
            weight_metrics = ()
            if task in (syn_asic, ):
                goal_metrics = ('errors',)
                weight_metrics = ()
            elif task in (timing, ):
                goal_metrics = ('errors', 'setupwns', 'setuptns')
                weight_metrics = ('cellarea', 'peakpower', 'leakagepower')

            for metric in goal_metrics:
                flow.set('flowgraph', flowname, step, str(index), 'goal', metric, 0)
            for metric in weight_metrics:
                flow.set('flowgraph', flowname, step, str(index), 'weight', metric, 1.0)
        prevstep = step

    return flow


##################################################
if __name__ == "__main__":
    chip = siliconcompiler.Chip('design')
    chip.set('input', 'constraint', 'sdc', 'test')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
