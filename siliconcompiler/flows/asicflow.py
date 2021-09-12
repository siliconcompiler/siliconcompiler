import importlib
import os
import siliconcompiler
import re

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip):
    '''
    This is a standard open source ASIC flow. The asic flow is a liner
    pipeline that includes the stages below. The steps syn, floorplan,
    physyn, place, cts, route, and dfm have minimizataion associated
    with them. To view the flowgraph, see the .png file.

    The syn, physyn, place, cts, route steps supports per process
    options that can be set up by settingg the 'techarg','<step>_np'
    arg to a value > 1.

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

    Args:
        chip (object): Reference to chip object.

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
        'lvs' : 'magic'
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
            fanout = int(chip.get('flowarg', param))
        for index in range(fanout):
            # Metrics
            chip.set('flowgraph', step, str(index), 'weight',  'cellarea', 1.0)
            chip.set('flowgraph', step, str(index), 'weight',  'peakpower', 1.0)
            chip.set('flowgraph', step, str(index), 'weight',  'standbypower', 1.0)
            # Goals
            chip.set('metric', step, str(index), 'drv', 'errors', 0)
            chip.set('metric', step, str(index), 'drv', 'goal', 0.0)
            chip.set('metric', step, str(index), 'holdwns', 'goal', 0.0)
            chip.set('metric', step, str(index), 'holdtns', 'goal', 0.0)
            chip.set('metric', step, str(index), 'setupwns', 'goal', 0.0)
            chip.set('metric', step, str(index), 'setuptns', 'goal', 0.0)
            #graph
            if step == 'import':
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
            elif re.match(r'join|maximum|minimum|verify', tools[step]):
                chip.set('flowgraph', step, '0', 'function', tools[step])
                prevparam = prevstep + "_np"
                fanin = 1
                if prevparam in chip.getkeys('flowarg'):
                    fanin  = int(chip.get('flowarg', prevparam))
                for i in range(fanin):
                    chip.add('flowgraph', step, str(index), 'input', prevstep, str(i))
            else:
                chip.set('flowgraph', step, str(index), 'tool', tools[step])
                chip.add('flowgraph', step, str(index), 'input', prevstep, '0')

        prevstep = step

##################################################
if __name__ == "__main__":

    prefix = os.path.splitext(os.path.basename(__file__))[0]
    for target in ('freepdk45', 'skywater130'):
        chip = siliconcompiler.Chip()
        setup_flow(chip)
        chip.writecfg(f'{prefix}_{target}.json')
        chip.writegraph(f'{prefix}_{target}.png')
