import pya

import json
import os

filename = os.environ['SC_FILENAME']

# We read the manifest using the json library since KLayout bundles its own
# Python interpreter, and it's difficult to include third-party libraries.
with open('sc_manifest.json', 'r') as f:
    sc_cfg = json.load(f)

# Extract info from manifest
sc_pdk = sc_cfg['option']['pdk']['value']
sc_stackup = sc_cfg['pdk'][sc_pdk]['stackup']['value'][0]
sc_mainlib = sc_cfg['asic']['logiclib']['value'][0]
sc_libtype = list(sc_cfg['library'][sc_mainlib]['asic']['footprint'].keys())[0]

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
        macro_lefs.append(sc_cfg['library'][lib]['model']['layout']['lef'][sc_stackup]['value'][0])

# Tech / library LEF files are optional.
try:
    tech_lef = sc_cfg['pdk'][sc_pdk]['aprtech']['klayout'][sc_stackup][sc_libtype]['lef']['value'][0]
except KeyError:
    tech_lef = None
try:
    lib_lef = sc_cfg['library'][sc_mainlib]['model']['layout']['lef'][sc_stackup]['value'][0]
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

app = pya.Application.instance()
# show all cells
app.set_config('full-hierarchy-new-cell', 'true')
# no tip pop-ups
app.set_config('tip-window-hidden', 'only-top-level-shown-by-default=3,editor-mode=4,editor-mode=0')
# hide text
app.set_config('text-visible', 'false')

# Display the file!
cell_view = pya.MainWindow.instance().load_layout(filename, layoutOptions, 0)
layout_view = cell_view.view()

if lyp_path:
    # Set layer properties -- setting second argument to True ensures things like
    # KLayout's extra outline, blockage, and obstruction layers appear.
    layout_view.load_layer_props(lyp_path, True)

# If 'screenshot' mode is set, save image and exit.
try:
    if screenshot:
        # Save a screenshot. TODO: Get aspect ratio from sc_cfg?
        gds_img = layout_view.get_image(int(scr_w), int(scr_h))
        design = sc_cfg["design"]["value"]
        jobname = sc_cfg["option"]["jobname"]["value"]
        gds_img.save(f'../{design}/{jobname}/{design}.png', 'PNG')
        # Done, exit.
        app.exit(0)
except:
    # 'screenshot' var may not be defined.
    pass
