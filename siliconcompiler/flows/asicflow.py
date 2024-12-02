import siliconcompiler

from siliconcompiler.flows._common import setup_multiple_frontends
from siliconcompiler.flows._common import _make_docs

from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.openroad import init_floorplan
from siliconcompiler.tools.openroad import macro_placement
from siliconcompiler.tools.openroad import endcap_tapcell_insertion
from siliconcompiler.tools.openroad import power_grid
from siliconcompiler.tools.openroad import pin_placement
from siliconcompiler.tools.openroad import global_placement
from siliconcompiler.tools.openroad import repair_design
from siliconcompiler.tools.openroad import detailed_placement
from siliconcompiler.tools.openroad import clock_tree_synthesis
from siliconcompiler.tools.openroad import repair_timing
from siliconcompiler.tools.openroad import fillercell_insertion
from siliconcompiler.tools.openroad import global_route
from siliconcompiler.tools.openroad import antenna_repair
from siliconcompiler.tools.openroad import detailed_route
from siliconcompiler.tools.openroad import fillmetal_insertion
from siliconcompiler.tools.openroad import write_data
from siliconcompiler.tools.klayout import export as klayout_export

from siliconcompiler.tools.builtin import minimum


############################################################################
# DOCS
############################################################################
def make_docs(chip):
    n = 3
    _make_docs(chip)
    return setup(syn_np=n, floorplan_np=n, physyn_np=n, place_np=n, cts_np=n, route_np=n)


###########################################################################
# Flowgraph Setup
############################################################################
def setup(flowname='asicflow',
          syn_np=1,
          floorplan_np=1,
          physyn_np=1,
          place_np=1,
          cts_np=1,
          route_np=1):
    '''
    A configurable ASIC compilation flow.

    The 'asicflow' includes the stages below. The steps syn, floorplan,
    physyn, place, cts, route, and dfm have minimization associated
    with them. To view the flowgraph, see the .png file.

    * **import**: Sources are collected and packaged for compilation
    * **syn**: Translates RTL to netlist using Yosys
    * **floorplan**: Floorplanning
    * **physyn**: Physical Synthesis
    * **place**: Global and detailed placement
    * **cts**: Clock tree synthesis
    * **route**: Global and detailed routing
    * **dfm**: Metal fill, atenna fixes and any other post routing steps
    * **export**: Export design from APR tool and merge with library GDS
    * **sta**: Static timing analysis (signoff)
    * **lvs**: Layout versus schematic check (signoff)
    * **drc**: Design rule check (signoff)

    The syn, physyn, place, cts, route steps supports per process
    options that can be set up by setting '<step>_np'
    arg to a value > 1, as detailed below:

    * syn_np : Number of parallel synthesis jobs to launch
    * floorplan_np : Number of parallel floorplan jobs to launch
    * physyn_np : Number of parallel physical synthesis jobs to launch
    * place_np : Number of parallel place jobs to launch
    * cts_np : Number of parallel clock tree synthesis jobs to launch
    * route_np : Number of parallel routing jobs to launch
    '''

    flow = siliconcompiler.Flow(flowname)

    # Linear flow, up until branch to run parallel verification steps.
    longpipe = [
        'syn',
        'syn.min',
        'floorplan.init',
        'floorplan.macro_placement',
        'floorplan.tapcell',
        'floorplan.power_grid',
        'floorplan.pin_placement',
        'floorplan.min',
        'place.global',
        'place.repair_design',
        'place.detailed',
        'place.min',
        'cts.clock_tree_synthesis',
        'cts.repair_timing',
        'cts.fillcell',
        'cts.min',
        'route.global',
        'route.antenna_repair',
        'route.detailed',
        'route.min',
        'dfm.metal_fill'
    ]

    # step --> task
    tasks = {
        'syn': syn_asic,
        'syn.min': minimum,
        'floorplan.init': init_floorplan,
        'floorplan.macro_placement': macro_placement,
        'floorplan.tapcell': endcap_tapcell_insertion,
        'floorplan.power_grid': power_grid,
        'floorplan.pin_placement': pin_placement,
        'floorplan.min': minimum,
        'place.global': global_placement,
        'place.repair_design': repair_design,
        'place.detailed': detailed_placement,
        'place.min': minimum,
        'cts.clock_tree_synthesis': clock_tree_synthesis,
        'cts.repair_timing': repair_timing,
        'cts.fillcell': fillercell_insertion,
        'cts.min': minimum,
        'route.global': global_route,
        'route.antenna_repair': antenna_repair,
        'route.detailed': detailed_route,
        'route.min': minimum,
        'dfm.metal_fill': fillmetal_insertion
    }

    np = {
        "syn": syn_np,
        "floorplan": floorplan_np,
        "physyn": physyn_np,
        "place": place_np,
        "cts": cts_np,
        "route": route_np
    }

    prevstep = None
    # Remove built in steps where appropriate
    flowpipe = []
    for step in longpipe:
        task = tasks[step]
        if task == minimum:
            np_step = prevstep.split('.')[0]
            if np_step in np and np[np_step] > 1:
                flowpipe.append(step)
        else:
            flowpipe.append(step)
        prevstep = step

    flowtasks = []
    for step in flowpipe:
        flowtasks.append((step, tasks[step]))

    # Programmatically build linear portion of flowgraph and fanin/fanout args
    prevstep = setup_multiple_frontends(flow)
    prev_fanout = 1
    for step, task in flowtasks:
        fanout = 1
        np_step = step.split('.')[0]
        if np_step in np and task != minimum:
            fanout = np[np_step]

        # create nodes
        for index in range(fanout):
            # nodes
            flow.node(flowname, step, task, index=index)

        # create edges
        for index in range(fanout):
            # edges
            fanin = prev_fanout
            if task == minimum:
                for i in range(fanin):
                    flow.edge(flowname, prevstep, step, tail_index=i)
            elif prevstep:
                if fanin == fanout:
                    flow.edge(flowname, prevstep, step, tail_index=index, head_index=index)
                else:
                    flow.edge(flowname, prevstep, step, head_index=index)

            # metrics
            goal_metrics = ()
            weight_metrics = ()
            if task in (syn_asic, ):
                goal_metrics = ('errors',)
                weight_metrics = ()
            elif task in (init_floorplan, macro_placement, endcap_tapcell_insertion,
                          power_grid, pin_placement, global_placement, repair_design,
                          detailed_placement, clock_tree_synthesis, repair_timing,
                          fillercell_insertion, global_route, antenna_repair, detailed_route,
                          fillmetal_insertion):
                goal_metrics = ('errors', 'setupwns', 'setuptns')
                weight_metrics = ('cellarea', 'peakpower', 'leakagepower')

            for metric in goal_metrics:
                flow.set('flowgraph', flowname, step, str(index), 'goal', metric, 0)
            for metric in weight_metrics:
                flow.set('flowgraph', flowname, step, str(index), 'weight', metric, 1.0)
        prevstep = step
        prev_fanout = fanout

    # add write information steps
    flow.node(flowname, 'write.gds', klayout_export)
    flow.edge(flowname, prevstep, 'write.gds')
    flow.node(flowname, 'write.views', write_data)
    flow.edge(flowname, prevstep, 'write.views')

    return flow


##################################################
if __name__ == "__main__":
    chip = siliconcompiler.Chip('design')
    chip.set('input', 'constraint', 'sdc', 'test')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
