import os
import importlib
import re
import sys

from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Tool Setup
################################

def setup_tool(chip, step):

     #Shared setting for all openroad tools
     refdir = 'eda/openroad'
     chip.add('flow', step, 'threads', '4')
     chip.add('flow', step, 'copy', 'false')
     chip.add('flow', step, 'refdir', refdir)
     chip.add('flow', step, 'script', refdir + '/sc_apr.tcl')
     
     chip.add('flow', step, 'format', 'tcl')
     chip.add('flow', step, 'vendor', 'openroad')
     chip.add('flow', step, 'exe', 'openroad')
     chip.add('flow', step, 'option', '-no_init')

def setup_options(chip, step):

     options = chip.get('flow', step, 'option')
     if (step not in chip.get('bkpt')) and (not '-exit' in options):
          options.append('-exit')
     return options
  
################################
# Pre/Post Processing
################################

def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
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

def post_process(chip, step, status):
     ''' Tool specific function to run after step execution
     '''

     #Check log file for errors and statistics
     error = 0
     exe = chip.get('flow',step,'exe')[-1]
     design = chip.get('design')[-1]
     with open(exe + ".log") as f:
          for line in f:
               errmatch = re.match(r'^Error:', line)
               area = re.search(r'^Design area (\d+)', line)
               tns = re.search(r'^tns (.*)',line)
               wns = re.search(r'^wns (.*)',line)
               power = re.search(r'^Total(.*)',line)
               vias = re.search(r'^total number of vias = (.*)',line)
               wirelength = re.search(r'^total wire length = (.*) um',line)
               if errmatch:
                    error = 1
               elif area:
                    chip.set('real', step, 'area_cells', str(round(float(area.group(1)),2)))
               elif tns:
                    chip.set('real', step, 'setup_tns', str(round(float(tns.group(1)),2)))
               elif wns:
                    chip.set('real', step, 'setup_wns', str(round(float(wns.group(1)),2)))
               elif power:                    
                    powerlist = power.group(1).split()
                    leakage = powerlist[2]
                    total = powerlist[3] 
                    chip.set('real', step, 'power_total', total)
                    chip.set('real', step, 'power_leakage',  leakage)
               elif wirelength:
                    chip.set('real', step, 'wirelength', str(round(float(wirelength.group(1)),2)))
               elif vias:
                    chip.set('real', step, 'vias', str(round(float(vias.group(1)),2)))
                    
     #Temporary superhack!
     #Getting cell count and net number from DEF
     if error == 0:
          with open("outputs/" + design + ".def") as f:
               for line in f:
                    cells = re.search(r'^COMPONENTS (\d+)', line)
                    nets = re.search(r'^NETS (\d+)',line)
                    pins = re.search(r'^PINS (\d+)',line)
                    if cells:
                         chip.set('real', step, 'cells', cells.group(1))
                    elif nets:
                         chip.set('real', step, 'nets', nets.group(1))               
                    elif pins:
                         chip.set('real', step, 'pins', pins.group(1))

     #TODO: implement stronger error checking
     return status
