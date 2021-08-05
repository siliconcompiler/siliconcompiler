import os
import importlib
import re
import sys
import siliconcompiler
from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step):
    ''' Tool specific function to run before step execution
    '''

    # default tool settings, note, not additive!
    tool = 'openroad'
    refdir = 'eda/openroad'
    chip.set('eda', tool, step, 'format', 'tcl')
    chip.set('eda', tool, step, 'vendor', tool)
    chip.set('eda', tool, step, 'exe', tool)
    chip.set('eda', tool, step, 'threads', '4')
    chip.set('eda', tool, step, 'copy', 'false')
    chip.set('eda', tool, step, 'refdir', refdir)
    chip.set('eda', tool, step, 'script', refdir + '/sc_apr.tcl')

    chip.set('eda', tool, step, 'option', '-no_init')

    # exit automatically unless bkpt
    if (step not in chip.get('bkpt')):
         chip.add('eda', tool, step, 'option', '-exit')

    # enable programmatic pythonic floorplans
    if step == 'floorplan':
        floorplan_file = chip.get('asic', 'floorplan')

        if len(floorplan_file) == 0:
             return

        floorplan_file = schema_path(floorplan_file[-1])

        if os.path.splitext(floorplan_file)[-1] != '.py':
             return

        fp = Floorplan(chip)

        # Import user's floorplan file, call setup_floorplan to set up their
        # floorplan, and save it as an input DEF

        mod_name = os.path.splitext(os.path.basename(floorplan_file))[0]
        mod_spec = importlib.util.spec_from_file_location(mod_name, floorplan_file)
        module = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(module)
        setup_floorplan = getattr(module, "setup_floorplan")

        fp = setup_floorplan(fp, chip)

        topmodule = chip.get('design')[-1]
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
     exe = chip.get('eda', tool, step, 'exe')[-1]
     design = chip.get('design')[-1]
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
                    chip.set('metric', step, 'real', 'area_cells', str(round(float(area.group(1)),2)))
               elif tns:
                    chip.set('metric', step, 'real', 'setup_tns', str(round(float(tns.group(1)),2)))
               elif wirelength:
                    chip.set('metric', step, 'real', 'wirelength', str(round(float(wirelength.group(1)),2)))
               elif vias:
                    chip.set('metric', step, 'real', 'vias', str(round(float(vias.group(1)),2)))
               elif slack:
                    chip.set('metric', step, 'real', metric, str(round(float(slack.group(1)),2)))
               elif metric == "power":
                    if power:
                         powerlist = power.group(1).split()
                         leakage = powerlist[2]
                         total = powerlist[3]
                         chip.set('metric', step, 'real', 'power_total', total)
                         chip.set('metric', step, 'real', 'power_leakage',  leakage)


     #Setting Warnings and Errors
     chip.set('metric', step, 'real', 'errors', str(errors))
     chip.set('metric', step, 'real', 'warnings', str(warnings))

     #Temporary superhack!
     #Getting cell count and net number from DEF
     if errors == 0:
          with open("outputs/" + design + ".def") as f:
               for line in f:
                    cells = re.search(r'^COMPONENTS (\d+)', line)
                    nets = re.search(r'^NETS (\d+)',line)
                    pins = re.search(r'^PINS (\d+)',line)
                    if cells:
                         chip.set('metric', step, 'real', 'cells', cells.group(1))
                    elif nets:
                         chip.set('metric', step, 'real', 'nets', nets.group(1))
                    elif pins:
                         chip.set('metric', step, 'real', 'pins', pins.group(1))

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
