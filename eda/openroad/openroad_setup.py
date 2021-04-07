import os
import importlib

from siliconcompiler.floorplan import *

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
     chip.add('flow', step, 'option', '-no_init -exit')

def setup_options(chip, step):

     options = chip.get('flow', step, 'option')
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

        floorplan_file = make_abs_path(floorplan_file[-1])

        if os.path.splitext(floorplan_file)[-1] != '.py':
             return

        # Harcode tech lib
        # TODO: initialize floorplan by passing in the actual library files
        # and/or data

        # For now, check that we use freepdk45, because we're hardcoding for
        # this library
        if chip.get('target')[-1] != 'freepdk45':
             return

        # Initialize floorplan according to freepdk45 library, with equivalent
        # die/core size to GCD. Set scale factor fo 1, so all units are in
        # microns
        offset = (0.095 * 2000, 0.07 * 2000)
        layers = [
             {'name': 'metal1', 'offset': offset, 'pitch': 0.14 * 2000},
             {'name': 'metal2', 'offset': offset, 'pitch': 0.19 * 2000},
             {'name': 'metal3', 'offset': offset, 'pitch': 0.14 * 2000},
             {'name': 'metal4', 'offset': offset, 'pitch': 0.28 * 2000},
             {'name': 'metal5', 'offset': offset, 'pitch': 0.28 * 2000},
             {'name': 'metal6', 'offset': offset, 'pitch': 0.28 * 2000},
             {'name': 'metal7', 'offset': offset, 'pitch': 0.8 * 2000},
             {'name': 'metal8', 'offset': offset, 'pitch': 0.8 * 2000},
             {'name': 'metal9', 'offset': offset, 'pitch': 0.8 * 2000},
             {'name': 'metal10', 'offset': offset, 'pitch': 1.6 * 2000},
        ]

        fp = Floorplan(chip,
                        [(0, 0), (200260, 201600)],
                        [(20140, 22400), (180500, 182000)],
                        layers,
                        "FreePDK45_38x28_10R_NP_162NW_34O",
                        380,
                        2800,
                        1)

        # Import user's floorplan file, call setup_floorplan to set up their
        # floorplan, and save it as an input DEF

        mod_name = os.path.splitext(os.path.basename(floorplan_file))[0]
        mod_spec = importlib.util.spec_from_file_location(mod_name, floorplan_file)
        module = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(module)
        setup_floorplan = getattr(module, "setup_floorplan")

        fp = setup_floorplan(fp)
        fp.generate_rows()
        fp.generate_tracks()

        topmodule = chip.get('design')[-1]
        fp.save('inputs/' + topmodule + '.def')

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    pass

################################
# Utilities
################################

def make_abs_path(path):
    '''Helper for constructing absolute path, assuming `path` is relative to
    directory `sc` was run from
    '''

    if os.path.isabs(path):
        return path

    cwd = os.getcwd()
    run_dir = cwd + '/../../../' # directory `sc` was run from
    return os.path.join(run_dir, path)
