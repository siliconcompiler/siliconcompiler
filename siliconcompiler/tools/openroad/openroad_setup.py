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

def setup_tool(chip, step):
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

    chip.set('eda', tool, step, 'format', 'tcl')
    chip.set('eda', tool, step, 'vendor', tool)
    chip.set('eda', tool, step, 'exe', tool)
    if chip.get('eda', tool, step, 'threads') is None:
        chip.set('eda', tool, step, 'threads', os.cpu_count())
    chip.set('eda', tool, step, 'copy', 'false')
    chip.set('eda', tool, step, 'refdir', refdir)

    if step == 'show':
        chip.set('eda', tool, step, 'option', '-gui')
        chip.set('eda', tool, step, 'script', refdir + '/sc_display.tcl')
    else:
        chip.set('eda', tool, step, 'option', '-no_init')
        chip.set('eda', tool, step, 'script', refdir + '/sc_apr.tcl')
        # exit automatically unless bkpt
        if (step not in chip.get('bkpt')):
            chip.add('eda', tool, step, 'option', '-exit')

        # enable programmatic pythonic floorplans
        if step == 'floorplan':
            floorplan_file = chip.get('asic', 'floorplan')

            if len(floorplan_file) == 0:
                 return

            floorplan_file = schema_path(floorplan_file[0])

            if os.path.splitext(floorplan_file)[-1] != '.py':
                 return

            if len(floorplan_file) > 1:
                 chip.logger.warning('OpenROAD-based flows expect only one Python '
                                     'floorplan, but multiple were provided. '
                                     f'Defaulting to {floorplan_file}.')

            fp = Floorplan(chip)

            # Import user's floorplan file, call setup_floorplan to set up their
            # floorplan, and save it as an input DEF

            mod_name = os.path.splitext(os.path.basename(floorplan_file))[0]
            mod_spec = importlib.util.spec_from_file_location(mod_name, floorplan_file)
            module = importlib.util.module_from_spec(mod_spec)
            mod_spec.loader.exec_module(module)
            setup_floorplan = getattr(module, "setup_floorplan")

            fp = setup_floorplan(fp, chip)

            topmodule = chip.get('design')
            def_file = 'inputs/' + topmodule + '.def'
            fp.write_def(def_file)

################################
# Post_process (post executable)
################################

def post_process(chip, step):
     ''' Tool specific function to run after step execution
     '''

     #Check log file for errors and statistics
     tool = 'openroad'
     errors = 0
     warnings = 0
     metric = None
     exe = chip.get('eda', tool, step, 'exe')
     design = chip.get('design')
     with open(exe + ".log") as f:
          for line in f:
               metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
               errmatch = re.match(r'^Error:', line)
               warnmatch = re.match(r'^\[WARNING', line)
               area = re.search(r'^Design area (\d+)', line)
               tns = re.search(r'^tns (.*)',line)
               vias = re.search(r'^total number of vias = (.*)',line)
               wirelength = re.search(r'^total wire length = (.*) um',line)
               power = re.search(r'^Total(.*)',line)
               slack = re.search(r'^worst slack (.*)',line)
               if metricmatch:
                    metric = metricmatch.group(1)
               elif errmatch:
                    errors = errors + 1
               elif warnmatch:
                    warnings = warnings +1
               elif area:
                    chip.set('metric', step, 'real', 'area_cells', round(float(area.group(1)),2))
               elif tns:
                    chip.set('metric', step, 'real', 'setup_tns', round(float(tns.group(1)),2))
               elif wirelength:
                    chip.set('metric', step, 'real', 'wirelength', round(float(wirelength.group(1)),2))
               elif vias:
                    chip.set('metric', step, 'real', 'vias', round(float(vias.group(1)),2))
               elif slack:
                    chip.set('metric', step, 'real', metric, round(float(slack.group(1)),2))
               elif metric == "power":
                    if power:
                         powerlist = power.group(1).split()
                         leakage = powerlist[2]
                         total = powerlist[3]
                         chip.set('metric', step, 'real', 'power_total', float(total))
                         chip.set('metric', step, 'real', 'power_leakage',  float(leakage))


     #Setting Warnings and Errors
     chip.set('metric', step, 'real', 'errors', errors)
     chip.set('metric', step, 'real', 'warnings', warnings)

     #Temporary superhack!
     #Getting cell count and net number from DEF
     if errors == 0:
          with open("outputs/" + design + ".def") as f:
               for line in f:
                    cells = re.search(r'^COMPONENTS (\d+)', line)
                    nets = re.search(r'^NETS (\d+)',line)
                    pins = re.search(r'^PINS (\d+)',line)
                    if cells:
                         chip.set('metric', step, 'real', 'cells', int(cells.group(1)))
                    elif nets:
                         chip.set('metric', step, 'real', 'nets', int(nets.group(1)))
                    elif pins:
                         chip.set('metric', step, 'real', 'pins', int(pins.group(1)))

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
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='apr')
    # write out results
    chip.writecfg(output)
