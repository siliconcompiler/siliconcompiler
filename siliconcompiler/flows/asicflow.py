import importlib
import os
import siliconcompiler
import re

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, process, signoff=True):
    '''
    This is a standard open source ASIC flow. The asic flow is a liner
    pipeline that includes the stages below. The steps syn, floorplan,
    physyn, place, cts, route, and dfm have minimizataion associated
    with them. To view the graph, see the .png file.

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
    * **package**: Package design for reuse
    * **archive**: Archive design

    Args:
        process (string): Specifies the process of the compilation.
            Used in complex flows and reserved for future use.

    '''

    # A simple linear flow (relying on Python orderered local dict)
    flow = {
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
        'export' : 'klayout'
    }

    # Conditional signoff flow
    signoff = {
        'sta' : 'openroad'
    }

    if process == 'skywater':
        signoff['drc'] = 'magic'
        signfoff['lvs'] = 'magic',
        
    signoff = {
        'collectall' : 'join',
        'signoff' : 'verify'
        }


    
    # Set the steplist which can run remotely (if required)
    steplist =list(flow.keys())
    chip.set('remote', 'steplist', steplist[1:])

    # Showtool definitions
    chip.set('showtool', 'def', 'openroad')
    chip.set('showtool', 'gds', 'klayout')

    # Definining the exeuction graph
    index = '0'
    for step in flow:
        # tool vs function
        if re.match(r'join|maximum|minimum|verify', flow[step]):
            chip.set('flowgraph', step, index, 'function', flow[step])
        else:
            chip.set('flowgraph', step, index, 'tool', flow[step])
        # order
        if step == 'import':
            pass
        else:
            chip.add('flowgraph', step, index, 'input', prevstep, "0")

        # Metrics
        chip.set('flowgraph', step, index, 'weight',  'cellarea', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'peakpower', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'standbypower', 1.0)

        # Goals
        chip.set('metric', step, index, 'drv', 'errors', 0)
        #chip.set('metric', step, index, 'drv', 'warnings', 0)
        chip.set('metric', step, index, 'drv', 'goal', 0.0)
        chip.set('metric', step, index, 'holdwns', 'goal', 0.0)
        chip.set('metric', step, index, 'holdtns', 'goal', 0.0)
        chip.set('metric', step, index, 'setupwns', 'goal', 0.0)
        chip.set('metric', step, index, 'setuptns', 'goal', 0.0)
        
        prevstep = step


##################################################
if __name__ == "__main__":

    prefix = os.path.splitext(os.path.basename(__file__))[0]
    chip = siliconcompiler.Chip()
    setup_flow(chip,"freepdk45")
    chip.writecfg(prefix + '.json')
    chip.writegraph(prefix + '.png')
