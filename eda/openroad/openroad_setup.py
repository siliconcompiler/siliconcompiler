import os
import importlib

from siliconcompiler.floorplan import *
from siliconcompiler.schema import schema_path

################################
# Tool Setup
################################

def setup_tool(chip, step):

     #Shared setting for all openroad tools
     refdir = 'eda/openroad'
     chip.add('flow', step, 'threads', '4')
     chip.add('flow', step, 'copy', 'true')
     chip.add('flow', step, 'refdir', refdir)
     chip.add('flow', step, 'script', refdir + '/sc_'+step+'.tcl')
     
     chip.add('flow', step, 'format', 'tcl')
     chip.add('flow', step, 'vendor', 'openroad')
     chip.add('flow', step, 'exe', 'openroad')
     chip.add('flow', step, 'option', '-no_init')

def setup_options(chip, step):

     options = chip.get('flow', step, 'option')
     if (not chip.get('noexit')[-1] == 'true') and (not '-exit' in options):
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
        fp.save('inputs/' + topmodule + '.def')

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    pass
