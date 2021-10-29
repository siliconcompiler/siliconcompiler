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

    In order to enable running DRC and LVS verification, set the 'flowarg',
    'verify' arg to "true" (currently supported for Skywater130 only).
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

    # Linear flow, up until branch to run parallel verification steps.

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


    tools = {
        'import' : 'surelog',
        'convert': 'sv2v',
        'syn' : 'yosys',
        'synmin' : 'step_minimum',
        'floorplan' : 'openroad',
        'floorplanmin' : 'step_minimum',
        'physyn' : 'openroad',
        'physynmin' : 'step_minimum',
        'place' : 'openroad',
        'placemin' : 'step_minimum',
        'cts' : 'openroad',
        'ctsmin' : 'step_minimum',
        'route' : 'openroad',
        'routemin' : 'step_minimum',
        'dfm' : 'openroad',
        'dfmmin' : 'step_minimum',
        'export' : 'klayout',
    }

    # Run verification steps only if `flowarg, verify` is True
    verify = ('verify' in chip.getkeys('flowarg') and
              len(chip.get('flowarg', 'verify')) > 0 and
              chip.get('flowarg', 'verify')[0] == 'true')

    # Perform SystemVerilog to Verilog conversion step only if `flowarg, sv` is True
    sv = ('sv' in chip.getkeys('flowarg') and
           len(chip.get('flowarg', 'sv')) > 0 and
           chip.get('flowarg', 'sv')[0] == 'true')
    if sv:
        flowpipe = flowpipe[:1] + ['convert'] + flowpipe[1:]

    # Set mandatory mode
    chip.set('mode', 'asic')

    # Set the steplist which can run remotely (if required)
    chip.set('remote', 'steplist', flowpipe[1:] + (['extspice', 'lvsjoin', 'lvs', 'drc', 'signoff'] if verify else []))

    # Showtool definitions
    chip.set('showtool', 'def', 'klayout')
    chip.set('showtool', 'gds', 'klayout')

    # Programatically build linear portion of flowgraph and fanin/fanout args
    for step in flowpipe:
        param = step + "_np"
        fanout = 1
        if param in chip.getkeys('flowarg'):
            fanout = int(chip.get('flowarg', param)[0])
        for index in range(fanout):
            for metric in chip.getkeys('metric', 'default', 'default'):
                if metric in ('errors','warnings','drvs','holdwns','setupwns','holdtns','setuptns'):
                    chip.set('flowgraph', step, str(index), 'weight', metric, 0)
                    chip.set('metric', step, str(index), metric, 'goal', 0)
                elif metric in ('cellarea', 'peakpower', 'standbypower'):
                    chip.set('flowgraph', step, str(index), 'weight', metric, 1.0)
                elif metric not in ('dsps', 'brams', 'luts'):
                    chip.set('flowgraph', step, str(index), 'weight', metric, 0)

            #graph
            if step == 'import':
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
            elif re.search(r'join|maximum|minimum|verify', tools[step]):
                chip.set('flowgraph', step, '0', 'function', tools[step])
                prevparam = prevstep + "_np"
                fanin = 1
                if prevparam in chip.getkeys('flowarg'):
                    fanin  = int(chip.get('flowarg', prevparam)[0])
                for i in range(fanin):
                    chip.add('flowgraph', step, str(index), 'input', prevstep+str(i))
            else:
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.add('flowgraph', step, str(index), 'input', prevstep+'0')

        prevstep = step

    # If running verify steps, manually set up parallel LVS/DRC
    if verify:
        chip.set('flowgraph', 'extspice', '0', 'tool', 'magic')
        chip.add('flowgraph', 'extspice', '0', 'input', 'export0')

        chip.set('flowgraph', 'lvsjoin', '0', 'function', 'step_join')
        chip.add('flowgraph', 'lvsjoin', '0', 'input', 'dfmmin0')
        chip.add('flowgraph', 'lvsjoin', '0', 'input', 'extspice0')

        chip.set('flowgraph', 'lvs', '0', 'tool', 'netgen')
        chip.add('flowgraph', 'lvs', '0', 'input', 'lvsjoin0')

        chip.set('flowgraph', 'drc', '0', 'tool', 'magic')
        chip.add('flowgraph', 'drc', '0', 'input', 'export0')

        chip.set('flowgraph', 'signoff', '0', 'function', 'step_join')
        chip.add('flowgraph', 'signoff', '0', 'input', 'lvs0')
        chip.add('flowgraph', 'signoff', '0', 'input', 'drc0')


##################################################
if __name__ == "__main__":
    chip = make_docs()
    chip.writecfg("asicflow.json")
