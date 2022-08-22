import siliconcompiler
import re

from siliconcompiler.flows._common import setup_frontend

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    A configurable ASIC compilation flow.

    The 'asicflow' includes the stages below. The steps syn, floorplan,
    physyn, place, cts, route, and dfm have minimizataion associated
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
    options that can be set up by setting the 'arg, flow,'<step>_np'
    arg to a value > 1, as detailed below:

    * syn_np : Number of parallel synthesis jobs to launch
    * floorplan_np : Number of parallel floorplan jobs to launch
    * physyn_np : Number of parallel physical synthesis jobs to launch
    * place_np : Number of parallel place jobs to launch
    * cts_np : Number of parallel clock tree synthesis jobs to launch
    * route_np : Number of parallel routing jobs to launch
    '''

    chip = siliconcompiler.Chip('<topmodule>')
    n = '3'
    chip.set('arg', 'flow', 'verify','true')
    chip.set('arg', 'flow', 'syn_np', n)
    chip.set('arg', 'flow', 'floorplan_np', n)
    chip.set('arg', 'flow', 'physyn_np', n)
    chip.set('arg', 'flow', 'place_np', n)
    chip.set('arg', 'flow', 'cts_np', n)
    chip.set('arg', 'flow', 'route_np', n)
    chip.set('option', 'flow', 'asicflow')
    setup(chip)

    return chip

###########################################################################
# Flowgraph Setup
############################################################################
def setup(chip, flowname='asicflow'):
    '''
    Setup function for 'asicflow' ASIC compilation execution flowgraph.

    Args:
        chip (object): SC Chip object

    '''

    # Linear flow, up until branch to run parallel verification steps.
    longpipe = ['syn',
                'synmin',
                'floorplan',
                'floorplanmin',
                'physyn',
                'physynmin',
                'place',
                'placemin',
                'cts',
                'ctsmin',
                'route',
                'routemin',
                'dfm',
                'export']

    tools = {
        'syn' : 'yosys',
        'synmin' : 'minimum',
        'floorplan' : 'openroad',
        'floorplanmin' : 'minimum',
        'physyn' : 'openroad',
        'physynmin' : 'minimum',
        'place' : 'openroad',
        'placemin' : 'minimum',
        'cts' : 'openroad',
        'ctsmin' : 'minimum',
        'route' : 'openroad',
        'routemin' : 'minimum',
        'dfm' : 'openroad',
        'export' : 'klayout',
    }

    # Clear old flowgraph if it exists
    if flowname in chip.getkeys('flowgraph'):
        del chip.cfg['flowgraph'][flowname]

    #Remove built in steps where appropriate
    flowpipe = []
    for step in longpipe:
        if re.search(r'join|maximum|minimum|verify', tools[step]):
            if bool(prevstep + "_np" in chip.getkeys('arg','flow')):
                flowpipe.append(step)
        else:
            flowpipe.append(step)
        prevstep = step

    # Set mandatory mode
    chip.set('option', 'mode', 'asic')

    # Showtool definitions
    chip.set('option', 'showtool', 'def', 'klayout')
    chip.set('option', 'showtool', 'gds', 'klayout')

    flowtools = setup_frontend(chip)
    for step in flowpipe:
        flowtools.append((step, tools[step]))

    # Programatically build linear portion of flowgraph and fanin/fanout args
    for step, tool in flowtools:
        param = step + "_np"
        fanout = 1
        if param in chip.getkeys('arg', 'flow'):
            fanout = int(chip.get('arg', 'flow', param)[0])
        # create nodes
        for index in range(fanout):
            # nodes
            chip.node(flowname, step, tool, index=index)
            # edges
            if re.search(r'join|maximum|minimum|verify', tool):
                prevparam = prevstep + "_np"
                fanin  = int(chip.get('arg', 'flow', prevparam)[0])
                for i in range(fanin):
                    chip.edge(flowname, prevstep, step, tail_index=i)
            elif step != 'import':
                chip.edge(flowname, prevstep, step, head_index=index)
            # metrics
            goal_metrics = ()
            weight_metrics = ()
            if tool == 'yosys':
                goal_metrics = ('errors',)
                weight_metrics = ()
            elif tool == 'openroad':
                goal_metrics = ('errors', 'setupwns', 'setuptns')
                weight_metrics = ('cellarea', 'peakpower', 'leakagepower')

            for metric in goal_metrics:
                chip.set('flowgraph', flowname, step, str(index), 'goal', metric, 0)
            for metric in weight_metrics:
                chip.set('flowgraph', flowname, step, str(index), 'weight', metric, 1.0)
        prevstep = step

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("asicflow.png")
