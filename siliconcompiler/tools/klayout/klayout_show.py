import pya

import json
import os

# We read the manifest using the json library since KLayout bundles its own
# Python interpreter, and it's difficult to include third-party libraries.
with open('sc_manifest.json', 'r') as f:
    sc_cfg = json.load(f)

# Extract info from manifest
sc_design = sc_cfg["design"]["value"]
sc_step = sc_cfg['arg']['step']['value']
sc_index = sc_cfg['arg']['index']['value']
sc_filename = sc_cfg['tool']['klayout']['var'][sc_step][sc_index]['show_filepath']['value'][0]
sc_pdk = sc_cfg['option']['pdk']['value']
sc_stackup = sc_cfg['asic']['stackup']['value']
sc_mainlib = sc_cfg['asic']['logiclib']['value'][0]
sc_libtype = list(sc_cfg['library'][sc_mainlib]['asic']['footprint'].keys())[0]

sc_exit = sc_cfg['tool']['klayout']['var'][sc_step][sc_index]['show_exit']['value'][0] == "true"

# correct file path
sc_filename = "inputs/"+os.path.basename(sc_filename)

try:
    tech_file = sc_cfg['pdk'][sc_pdk]['layermap']['klayout']['def']['gds'][sc_stackup]['value'][0]
except KeyError:
    tech_file = None
try:
    lyp_path = sc_cfg['pdk'][sc_pdk]['display']['klayout'][sc_stackup]['value'][0]
except KeyError:
    lyp_path = None

macro_lefs = []
if 'macrolib' in sc_cfg['asic']:
    sc_macrolibs = sc_cfg['asic']['macrolib']['value']
    for lib in sc_macrolibs:
        macro_lefs.append(sc_cfg['library'][lib]['output'][sc_stackup]['lef']['value'][0])

# Tech / library LEF files are optional.
try:
    tech_lef = sc_cfg['pdk'][sc_pdk]['aprtech']['klayout'][sc_stackup][sc_libtype]['lef']['value'][0]
except KeyError:
    tech_lef = None
try:
    lib_lef = sc_cfg['library'][sc_mainlib]['output'][sc_stackup]['lef']['value'][0]
except KeyError:
    lib_lef = None

# Load KLayout technology file
tech = pya.Technology()
if tech_file and os.path.isfile(tech_file):
    tech.load(tech_file)
layoutOptions = tech.load_layout_options

lefs = []

lefs.extend(macro_lefs)

# Technology LEFs -- these are generally specified in the KLayout tech file, but
# we overwrite them with the paths in the manifest we don't have to worry if the
# paths in the tech file don't resolve right.
if tech_lef is not None:
    lefs.append(tech_lef)
if lib_lef is not None:
    lefs.append(lib_lef)

# Overwrite LEFs specified in tech file with the LEFs we took from the manifest.
layoutOptions.lefdef_config.lef_files = lefs

# These may be disabled in our KLayout tech file for reasons relating to GDS
# export, but for the purposes of viewing we'll hardcode them to True.
layoutOptions.lefdef_config.produce_blockages = True
layoutOptions.lefdef_config.produce_cell_outlines = True
layoutOptions.lefdef_config.produce_obstructions = True

# Always use LEF geometry even when LEF file contains FOREIGN statement.
layoutOptions.lefdef_config.macro_resolution_mode = 1

app = pya.Application.instance()

# Opinionated default KLayout configuration
# see ~/.klayout/klayoutrc for a list of configuration keys

# show all cells
app.set_config('full-hierarchy-new-cell', 'true')
# no tip pop-ups
app.set_config('tip-window-hidden', 'only-top-level-shown-by-default=3,editor-mode=4,editor-mode=0')
# hide text
app.set_config('text-visible', 'false')
# dark background
app.set_config('background-color', '#212121')

# Display the file!
cell_view = pya.MainWindow.instance().load_layout(sc_filename, layoutOptions, 0)
layout_view = cell_view.view()

if lyp_path:
    # Set layer properties -- setting second argument to True ensures things like
    # KLayout's extra outline, blockage, and obstruction layers appear.
    layout_view.load_layer_props(lyp_path, True)

# If 'screenshot' mode is set, save image and exit.
try:
    if sc_step == 'screenshot':
        # Save a screenshot. TODO: Get aspect ratio from sc_cfg?
        horizontal_resolution = int(sc_cfg['tool']['klayout']['var'][sc_step][sc_index]['show_horizontal_resolution']['value'][0])
        vertical_resolution = int(sc_cfg['tool']['klayout']['var'][sc_step][sc_index]['show_vertical_resolution']['value'][0])
        gds_img = layout_view.get_image(horizontal_resolution, vertical_resolution)
        gds_img.save(f'outputs/{sc_design}.png', 'PNG')
except Exception:
    # 'screenshot' var may not be defined.
    pass

if sc_exit:
    app.exit(0)
