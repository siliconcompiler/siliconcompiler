import pya

import sys


def show(schema, tech, input_path, output_path, screenshot=False):
    # Extract info from manifest
    flow = schema.get('option', 'flow')
    step = schema.get('arg', 'step')
    index = schema.get('arg', 'index')
    task = schema.get('flowgraph', flow, step, index, 'task')

    if 'hide_layers' in schema.getkeys('tool', 'klayout', 'task', task, 'var'):
        sc_hide_layers = schema.get('tool', 'klayout', 'task', task, 'var', 'hide_layers',
                                    step=step, index=index)
    else:
        sc_hide_layers = []

    # Load KLayout technology file
    layoutOptions = tech.load_layout_options

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
    app.set_config('tip-window-hidden', ','.join(['only-top-level-shown-by-default=3',
                                                  'editor-mode=4',
                                                  'editor-mode=0']))
    # hide text
    app.set_config('text-visible', 'false')
    # dark background
    app.set_config('background-color', '#212121')

    # Display the file!
    cell_view = pya.MainWindow.instance().load_layout(input_path, layoutOptions, 0)
    cell_view.technology = tech.name
    layout_view = cell_view.view()

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
        horizontal_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                               'show_horizontal_resolution',
                                               step=step, index=index)[0])
        vertical_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                             'show_vertical_resolution',
                                             step=step, index=index)[0])

        gds_img = layout_view.get_image(horizontal_resolution, vertical_resolution)
        gds_img.save(output_path, 'PNG')


def main():
    # SC_ROOT provided by CLI, and is only accessible when this is main module
    sys.path.append(SC_ROOT)  # noqa: F821

    from tools.klayout.klayout_utils import technology
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
        sc_filename = schema.get('tool', 'klayout', 'task', task, 'var', 'show_filepath',
                                 step=step, index=index)[0]
    else:
        sc_fileext = schema.get('tool', 'klayout', 'task', task, 'var', 'show_filetype',
                                step=step, index=index)[0]
        sc_filename = f"inputs/{design}.{sc_fileext}"

    sc_exit = schema.get('tool', 'klayout', 'task', task, 'var', 'show_exit',
                         step=step, index=index) == ["true"]

    show(schema, technology(schema), sc_filename, f'outputs/{design}.png',
         screenshot=(step == 'screenshot'))

    if sc_exit:
        pya.Application.instance().exit(0)


if __name__ == '__main__':
    main()
