import importlib
import os
import siliconcompiler
import re

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
    * dfm_np : Number of parallel dfm jobs to launch

    '''

    chip = siliconcompiler.Chip()
    setup_flow(chip)

    return chip

###########################################################################
# Flowgraph Setup
############################################################################
def setup_flow(chip):
    '''
    Setup function for 'asicflow' ASIC compilation execution flowgraph.

    Args:
        chip (object): SC Chip object

    '''

    # A simple linear flow (relying on Python orderered local dict)

    flowpipe = ['import',
                'syn',
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
                'dfmmin',
                'export']


    if chip.get('pdk', 'process') == 'skywater130':
        flowpipe.append('extspice')
        flowpipe.append('lvs')
        flowpipe.append('drc')

    tools = {
        'import' : 'verilator',
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
        'dfmmin' : 'minimum',
        'export' : 'klayout',
        'drc' : 'magic',
        'extspice': 'magic',
        'lvs' : 'netgen'
    }

    # Set the steplist which can run remotely (if required)
    chip.set('remote', 'steplist', flowpipe[1:])

    # Showtool definitions
    chip.set('showtool', 'def', 'openroad')
    chip.set('showtool', 'gds', 'klayout')

    # Implementation flow graph
    for step in flowpipe:
        param = step + "_np"
        fanout = 1
        if param in chip.getkeys('flowarg'):
            fanout = int(chip.get('flowarg', param)[0])
        for index in range(fanout):
            for metric in chip.getkeys('metric', 'default', 'default'):
                if metric in ('errors','warnings','drvs','holdwns','setupwns','holdtns','setuptns'):
                    chip.set('flowgraph', step, str(index), 'weight', metric, 1.0)
                    chip.set('metric', step, str(index), metric, 'goal', 0)
                elif metric in ('cellarea', 'peakpower', 'standbypower'):
                    chip.set('flowgraph', step, str(index), 'weight', metric, 1.0)
                elif metric in ('dsps', 'brams', 'luts'):
                    chip.set('flowgraph', step, str(index), 'weight', metric, 0.0)
                else:
                    chip.set('flowgraph', step, str(index), 'weight', metric, 0.001)
            #graph
            if step == 'import':
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
            elif re.match(r'join|maximum|minimum|verify', tools[step]):
                chip.set('flowgraph', step, '0', 'function', tools[step])
                prevparam = prevstep + "_np"
                fanin = 1
                if prevparam in chip.getkeys('flowarg'):
                    fanin  = int(chip.get('flowarg', prevparam)[0])
                for i in range(fanin):
                    chip.add('flowgraph', step, str(index), 'input', prevstep, str(i))
            else:
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.add('flowgraph', step, str(index), 'input', prevstep, '0')

        prevstep = step

##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.writecfg("asicflow.json")
