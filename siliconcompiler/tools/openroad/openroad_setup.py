import os
import importlib
import re
import shutil
import sys
import siliconcompiler
from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' OpenROAD is an integrated chip physical design tool that takes a design
    from synthesized netlist to routed layout.

    Implementation steps done by OpenROAD include:

    * Physical database management
    * DEF/LEF/Liberty/Verilog/SDC file interfaces
    * Static timing analysis
    * Floorplan initialize
    * Pin placement
    * Tap cell insertion
    * Power grid inesertion
    * Macro Placement
    * Global placement of standard cells
    * Electrical design rule repair
    * Clock tree synthesis
    * Timing driven optimization
    * Filler insertion
    * Global routing (route guides for detailed routing)
    * Detailed routing

    SC Configuration:
    All communiucation from siliconcompiler to openroad is done through
    the file 'sc_manifeset.tcl'. The entry point for all openroad based steps
    is the 'sc_apr.tcl' script. The script handles general input/output
    function and is the main interface to SC. Execution then branches off to
    separate files based on the step being executed (place, route, etc).

    Documentation:
    https://github.com/The-OpenROAD-Project/OpenROAD

    Source code:
    https://github.com/The-OpenROAD-Project/OpenROAD
    https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts

    '''

    # default tool settings, note, not additive!
    tool = 'openroad'
    refdir = 'siliconcompiler/tools/openroad'

    chip.set('eda', 'format', tool, step, index, 'tcl')
    chip.set('eda', 'vendor',tool, step, index, tool)
    chip.set('eda', 'exe', tool, step, index, tool)
    chip.set('eda', 'vswitch', tool, step, index, '-version')
    chip.set('eda', 'version', tool, step, index, 'af9a0f9faafb7e61ae18e9496169c3527312b82a')
    chip.set('eda', 'copy', tool, step, index, False)
    chip.set('eda', 'refdir', tool, step, index, refdir)
    chip.set('eda', 'script',tool, step, index, refdir + '/sc_apr.tcl')
    chip.set('eda', 'option', tool, step, index, 'cmdline', '-no_init')
    #Don't override command line arguments
    chip.set('eda', 'threads', tool, step, index, os.cpu_count())

    # defining default dictionary
    default_options = {
        'place_density': [],
        'pad_global_place': [],
        'pad_detail_place': [],
        'macro_place_halo': [],
        'macro_place_channel': []
    }

    # Setting up technologies with default values
    # NOTE: no reasonable defaults, for halo and channel.
    # TODO: Could possibly scale with node number for default, but safer to error out?
    # perhaps we should use node as comp instead?
    if chip.get('pdk','process'):
        process = chip.get('pdk','process')
        if process == 'freepdk45':
            default_options = {
                'place_density': ['0.3'],
                'pad_global_place': ['2'],
                'pad_detail_place': ['1'],
                'macro_place_halo': ['22.4', '15.12'],
                'macro_place_channel': ['18.8', '19.95']
            }
        elif process == 'asap7':
           default_options = {
                'place_density': ['0.77'],
                'pad_global_place': ['2'],
                'pad_detail_place': ['1'],
                'macro_place_halo': ['22.4', '15.12'],
                'macro_place_channel': ['18.8', '19.95']
            }
        elif process == 'skywater130':
           default_options = {
                'place_density': ['0.6'],
                'pad_global_place': ['4'],
                'pad_detail_place': ['2'],
                'macro_place_halo': ['1', '1'],
                'macro_place_channel': ['80', '80']
            }
        else:
            chip.error = 1
            chip.logger.error(f'Process {process} not set up for OpenROAD.')

    for option in default_options:
        if option in chip.getkeys('eda', 'option', tool, step, index):
            chip.logger.info('User provided option %s OpenROAD flow detected.', option)
        elif not default_options[option]:
            chip.error = 1
            chip.logger.error('Missing option %s for OpenROAD.', option)
        else:
            chip.set('eda', 'option', tool, step, index, option, default_options[option])

    # exit automatically unless bkpt
    if (step not in chip.get('bkpt')):
        chip.add('eda', 'option', tool, step, index, 'cmdline', '-exit')

################################
# Post_process (post executable)
################################

def post_process(chip, step, index):
     ''' Tool specific function to run after step execution
     '''

     #Check log file for errors and statistics
     tool = 'openroad'
     errors = 0
     warnings = 0
     metric = None
     exe = chip.get('eda', 'exe', tool, step, index)
     design = chip.get('design')
     with open(exe + ".log") as f:
          for line in f:
               metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
               errmatch = re.match(r'^Error:', line)
               warnmatch = re.match(r'^\[WARNING', line)
               area = re.search(r'^Design area (\d+)', line)
               tns = re.search(r'^tns (.*)',line)
               vias = re.search(r'^Total number of vias = (.*).',line)
               wirelength = re.search(r'^Total wire length = (.*) um',line)
               power = re.search(r'^Total(.*)',line)
               slack = re.search(r'^worst slack (.*)',line)
               if metricmatch:
                   metric = metricmatch.group(1)
               elif errmatch:
                   errors = errors + 1
               elif warnmatch:
                   warnings = warnings +1
               elif area:
                   chip.set('metric', 'area_cells',  step, index, 'real', round(float(area.group(1)),2), clobber=True)
               elif tns:
                   chip.set('metric', 'setup_tns',  step, index, 'real', round(float(tns.group(1)),2), clobber=True)
               elif wirelength:
                   chip.set('metric', 'wirelength',  step, index, 'real', round(float(wirelength.group(1)),2), clobber=True)
               elif vias:
                   chip.set('metric', 'vias',  step, index, 'real', int(vias.group(1)), clobber=True)
               elif slack:
                   chip.set('metric', metric, step, index, 'real', round(float(slack.group(1)),2), clobber=True)
               elif metric == "power":
                   if power:
                       powerlist = power.group(1).split()
                       leakage = powerlist[2]
                       total = powerlist[3]
                       chip.set('metric', 'power_total', step, index, 'real',  float(total), clobber=True)
                       chip.set('metric', 'power_leakage', step, index, 'real', float(leakage), clobber=True)

     #Setting Warnings and Errors
     chip.set('metric', 'errors', step, index, 'real',  errors , clobber=True)
     chip.set('metric', 'warnings', step, index, 'real', warnings, clobber=True)

     #Temporary superhack!rm
     #Getting cell count and net number from DEF
     if errors == 0:
          with open("outputs/" + design + ".def") as f:
               for line in f:
                    cells = re.search(r'^COMPONENTS (\d+)', line)
                    nets = re.search(r'^NETS (\d+)',line)
                    pins = re.search(r'^PINS (\d+)',line)
                    if cells:
                         chip.set('metric', 'cells', step, index, 'real', int(cells.group(1)), clobber=True)
                    elif nets:
                         chip.set('metric', 'nets', step, index, 'real', int(nets.group(1)), clobber=True)
                    elif pins:
                         chip.set('metric', 'pins', step, index, 'real', int(pins.group(1)), clobber=True)

     if step == 'sta':
          # Copy along GDS for verification steps that rely on it
          design = chip.get('design')
          shutil.copy(f'inputs/{design}.gds', f'outputs/{design}.gds')

     #Return 0 if successful
     return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(loglevel='DEBUG')
    chip.set('pdk','process','freepdk45')
    chip.writecfg('tmp.json', prune=False)
    # load configuration
    setup_tool(chip, step='syn', index='0')
    # write out results
    chip.writecfg(output)
