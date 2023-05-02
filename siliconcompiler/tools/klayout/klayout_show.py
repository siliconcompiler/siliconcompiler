import pya

import os
import sys


def show(schema, input_path, output_path, screenshot=False):
    # Extract info from manifest
    flow = schema.get('option', 'flow')
    step = schema.get('arg', 'step')
    index = schema.get('arg', 'index')
    task = schema.get('flowgraph', flow, step, index, 'task')

    if 'hide_layers' in schema.getkeys('tool', 'klayout', 'task', task, 'var'):
        sc_hide_layers = schema.get('tool', 'klayout', 'task', task, 'var', 'hide_layers', step=step, index=index)
    else:
        sc_hide_layers = []
    sc_pdk = schema.get('option', 'pdk')
    sc_stackup = schema.get('option', 'stackup')
    sc_mainlib = schema.get('asic', 'logiclib', step=step, index=index)[0]
    sc_libtype = schema.get('library', sc_mainlib, 'asic', 'libarch', step=step, index=index)

    tech_file = schema.get('pdk', sc_pdk, 'layermap', 'klayout', 'def', 'gds', sc_stackup)
    if tech_file:
        tech_file = tech_file[0]
    else:
        tech_file = None

    lyp_path = schema.get('pdk', sc_pdk, 'display', 'klayout', sc_stackup)
    if lyp_path:
        lyp_path = lyp_path[0]
    else:
        lyp_path = None

    macro_lefs = []
    if 'macrolib' in schema.getkeys('asic'):
        sc_macrolibs = schema.get('asic', 'macrolib', step=step, index=index)
        for lib in sc_macrolibs:
            macro_lefs.extend(schema.get('library', lib, 'output', sc_stackup, 'lef', step=step, index=index))

    # Tech / library LEF files are optional.
    tech_lefs = schema.get('pdk', sc_pdk, 'aprtech', 'klayout', sc_stackup, sc_libtype, 'lef')

    # Need to check validity since there are no "default" placeholders within the
    # library schema that would allow schema.get() to get a default value.
    if schema.valid('library', sc_mainlib, 'output', sc_stackup, 'lef'):
        lib_lefs = schema.get('library', sc_mainlib, 'output', sc_stackup, 'lef', step=step, index=index)
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
    cell_view = pya.MainWindow.instance().load_layout(input_path, layoutOptions, 0)
    layout_view = cell_view.view()

    if lyp_path:
        # Set layer properties -- setting second argument to True ensures things like
        # KLayout's extra outline, blockage, and obstruction layers appear.
        layout_view.load_layer_props(lyp_path, True)

    # Hide layers that shouldn't be shown in the current view.
    for layer in layout_view.each_layer():
        layer_break = layer.name.find(' - ')
        layer_name = layer.name[:layer_break]
        layer_ldt = layer.name[(layer_break + 3):]
        if (layer_name in sc_hide_layers) or (layer_ldt in sc_hide_layers):
            layer.visible = False

    # If 'screenshot' mode is set, save image and exit.
    if screenshot:
        # Save a screenshot. TODO: Get aspect ratio from sc_cfg?
        horizontal_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var', 'show_horizontal_resolution', step=step, index=index)[0])
        vertical_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var', 'show_vertical_resolution', step=step, index=index)[0])

        gds_img = layout_view.get_image(horizontal_resolution, vertical_resolution)
        gds_img.save(output_path, 'PNG')


def main():
    # SC_ROOT provided by CLI, and is only accessible when this is main module
    sys.path.append(SC_ROOT)  # noqa: F821
    from schema import Schema

    schema = Schema(manifest='sc_manifest.json')

    flow = schema.get('option', 'flow')
    step = schema.get('arg', 'step')
    index = schema.get('arg', 'index')
    task = schema.get('flowgraph', flow, step, index, 'task')

    design = schema.get('option', 'entrypoint')
    if not design:
        design = schema.get('design')

    if 'show_filepath' in schema.getkeys('tool', 'klayout', 'task', task, 'var'):
        sc_filename = schema.get('tool', 'klayout', 'task', task, 'var', 'show_filepath', step=step, index=index)[0]
    else:
        sc_fileext = schema.get('tool', 'klayout', 'task', task, 'var', 'show_filetype', step=step, index=index)[0]
        sc_filename = f"inputs/{design}.{sc_fileext}"

    sc_exit = schema.get('tool', 'klayout', 'task', task, 'var', 'show_exit', step=step, index=index) == ["true"]

    show(schema, sc_filename, f'outputs/{design}.png', screenshot=(step == 'screenshot'))

    if sc_exit:
        pya.Application.instance().exit(0)


if __name__ == '__main__':
    main()
