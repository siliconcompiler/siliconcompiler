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
    options that can be set up by setting the 'flowarg','<step>_np'
    arg to a value > 1, as detailed below:

    * syn_np : Number of parallel synthesis jobs to launch
    * floorplan_np : Number of parallel floorplan jobs to launch
    * physyn_np : Number of parallel physical synthesis jobs to launch
    * place_np : Number of parallel place jobs to launch
    * cts_np : Number of parallel clock tree synthesis jobs to launch
    * route_np : Number of parallel routing jobs to launch

    In order to enable running DRC and LVS verification, set the 'flowarg',
    'verify' arg to "true" (currently supported for Skywater130 only).
    '''

    chip = siliconcompiler.Chip()
    n = '3'
    chip.set('flowarg','verify','true')
    chip.set('flowarg', 'syn_np', n)
    chip.set('flowarg', 'floorplan_np', n)
    chip.set('flowarg', 'physyn_np', n)
    chip.set('flowarg', 'place_np', n)
    chip.set('flowarg', 'cts_np', n)
    chip.set('flowarg', 'route_np', n)
    chip.set('flow', 'asicflow')
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


    #Remove built in steps where appropriate
    flowpipe = []
    for step in longpipe:
        if re.search(r'join|maximum|minimum|verify', tools[step]):
            if bool(prevstep + "_np" in chip.getkeys('flowarg')):
                flowpipe.append(step)
        else:
            flowpipe.append(step)
        prevstep = step

    # Run verification steps only if `flowarg, verify` is True
    verify = ('verify' in chip.getkeys('flowarg') and
              len(chip.get('flowarg', 'verify')) > 0 and
              chip.get('flowarg', 'verify')[0] == 'true')

    # Set mandatory mode
    chip.set('mode', 'asic')

    # Showtool definitions
    chip.set('showtool', 'def', 'klayout')
    chip.set('showtool', 'gds', 'klayout')

    flowtools = setup_frontend(chip)
    for step in flowpipe:
        flowtools.append((step, tools[step]))

    # Programatically build linear portion of flowgraph and fanin/fanout args
    for step, tool in flowtools:
        param = step + "_np"
        fanout = 1
        if param in chip.getkeys('flowarg'):
            fanout = int(chip.get('flowarg', param)[0])
        # create nodes
        for index in range(fanout):
            # nodes
            chip.node(flowname, step, tool, index=index)
            # edges
            if re.search(r'join|maximum|minimum|verify', tool):
                prevparam = prevstep + "_np"
                fanin  = int(chip.get('flowarg', prevparam)[0])
                for i in range(fanin):
                    chip.edge(flowname, prevstep, step, tail_index=i)
            elif step != 'import':
                chip.edge(flowname, prevstep, step, head_index=index)
            # metrics
            for metric in  ('errors','drvs','holdwns','setupwns','holdtns','setuptns'):
                chip.set('metric', step, str(index), metric, 'goal', 0)
            for metric in ('cellarea', 'peakpower', 'standbypower'):
                chip.set('flowgraph', flowname, step, str(index), 'weight', metric, 1.0)
        prevstep = step

    # If running verify steps, manually set up parallel LVS/DRC
    if verify:
        chip.node(flowname, 'extspice', 'magic')
        chip.node(flowname, 'lvsjoin', 'join')
        chip.node(flowname, 'drc', 'magic')
        chip.node(flowname, 'lvs', 'netgen')
        chip.node(flowname, 'signoff', 'join')

        chip.edge(flowname, 'export', 'extspice')
        chip.edge(flowname, 'extspice', 'lvsjoin')
        chip.edge(flowname, 'dfm', 'lvsjoin')
        chip.edge(flowname, 'lvsjoin', 'lvs')
        chip.edge(flowname, 'export', 'drc')
        chip.edge(flowname, 'lvs', 'signoff')
        chip.edge(flowname, 'drc', 'signoff')

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.write_flowgraph("asicflow.png")
