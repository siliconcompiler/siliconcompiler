import pya

import os

import siliconcompiler

chip = siliconcompiler.Chip('')
chip.read_manifest('sc_manifest.json')

# Extract info from manifest
sc_design = chip.get('design')
flow = chip.get('option', 'flow')
step = chip.get('arg', 'step')
index = chip.get('arg', 'index')
task = chip.get('flowgraph', flow, step, index, 'task')

if 'hide_layers' in chip.getkeys('tool', 'klayout', 'task', task, 'var', step, index):
    sc_hide_layers = chip.get('tool', 'klayout', 'task', task, 'var', step, index, 'hide_layers')
else:
    sc_hide_layers = []

if 'show_filepath' in chip.getkeys('tool', 'klayout', 'task', task, 'var', step, index):
    sc_filename = chip.get('tool', 'klayout', 'task', task, 'var', step, index, 'show_filepath')[0]
else:
    sc_fileext = chip.get('tool', 'klayout', 'task', task, 'var', step, index, 'show_filetype')[0]
    sc_filename = f"inputs/{sc_design}.{sc_fileext}"
sc_pdk = chip.get('option', 'pdk')
sc_stackup = chip.get('option', 'stackup')
sc_mainlib = chip.get('asic', 'logiclib')[0]
sc_libtype = chip.get('library', sc_mainlib, 'asic', 'libarch')

sc_exit = chip.get('tool', 'klayout', 'task', task, 'var', step, index, 'show_exit') == ["true"]

tech_file = chip.get('pdk', sc_pdk, 'layermap', 'klayout', 'def', 'gds', sc_stackup)
if tech_file:
    tech_file = tech_file[0]
else:
    tech_file = None

lyp_path = chip.get('pdk', sc_pdk, 'display', 'klayout', sc_stackup)
if lyp_path:
    lyp_path = lyp_path[0]
else:
    lyp_path = None

macro_lefs = []
if 'macrolib' in chip.getkeys('asic'):
    sc_macrolibs = chip.get('asic', 'macrolib')
    for lib in sc_macrolibs:
        macro_lefs.extend(chip.get('library', lib, 'output', sc_stackup, 'lef'))

# Tech / library LEF files are optional.
tech_lefs = chip.get('pdk', sc_pdk, 'aprtech', 'klayout', sc_stackup, sc_libtype, 'lef')

# Need to check validity since there are no "default" placeholders within the
# library schema that would allow chip.get() to get a default value.
if chip.valid('library', sc_mainlib, 'output', sc_stackup, 'lef'):
    lib_lefs = chip.get('library', sc_mainlib, 'output', sc_stackup, 'lef')
else:
    lib_lefs = []

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
lefs.extend(tech_lefs)
lefs.extend(lib_lefs)

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

# Hide layers that shouldn't be shown in the screenshot.
for layer in layout_view.each_layer():
    layer_name = f'{layer.source_layer}/{layer.source_datatype}'
    if layer_name in sc_hide_layers:
        layer.visible = False

# If 'screenshot' mode is set, save image and exit.
if step == 'screenshot':
    # Save a screenshot. TODO: Get aspect ratio from sc_cfg?
    horizontal_resolution = int(chip.get('tool', 'klayout', 'task', task, 'var', step, index, 'show_horizontal_resolution')[0])
    vertical_resolution = int(chip.get('tool', 'klayout', 'task', task, 'var', step, index, 'show_vertical_resolution')[0])
    gds_img = layout_view.get_image(horizontal_resolution, vertical_resolution)
    gds_img.save(f'outputs/{sc_design}.png', 'PNG')

if sc_exit:
    app.exit(0)
