import pya

import os
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

    tech.load_layout_options = layoutOptions

    app = pya.Application.instance()
    main_window = pya.MainWindow.instance()
    if not main_window:
        print('[WARNING] unable to show layout as the main window is not available')
        return

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
    print(f"[INFO] Opening {input_path}")
    cell_view = main_window.load_layout(input_path, tech.name)
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
        xbins = int(schema.get('tool', 'klayout', 'task', task, 'var', 'xbins',
                               step=step, index=index)[0])
        ybins = int(schema.get('tool', 'klayout', 'task', task, 'var', 'ybins',
                               step=step, index=index)[0])

        if xbins == 1 and ybins == 1:
            __screenshot(schema, layout_view, output_path)
        else:
            __screenshot_montage(schema, layout_view, xbins, ybins)


def __screenshot(schema, layout_view, output_path):
    flow = schema.get('option', 'flow')
    step = schema.get('arg', 'step')
    index = schema.get('arg', 'index')
    task = schema.get('flowgraph', flow, step, index, 'task')

    # Save a screenshot. TODO: Get aspect ratio from sc_cfg?
    horizontal_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                           'show_horizontal_resolution',
                                           step=step, index=index)[0])
    vertical_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                         'show_vertical_resolution',
                                         step=step, index=index)[0])

    gds_img = layout_view.get_image(horizontal_resolution, vertical_resolution)
    print(f'[INFO] Saving screenshot to {output_path}')
    gds_img.save(output_path, 'PNG')


def __screenshot_montage(schema, view, xbins, ybins):
    flow = schema.get('option', 'flow')
    step = schema.get('arg', 'step')
    index = schema.get('arg', 'index')
    task = schema.get('flowgraph', flow, step, index, 'task')

    app = pya.Application.instance()
    options = (
        "grid-show-ruler",
        "grid-visible",
        "text-visible"
    )
    for option in options:
        app.set_config(option, "false")

    app.set_config("background-color", "#000000")  # Black

    design = schema.get('option', 'entrypoint')
    if not design:
        design = schema.get('design')

    horizontal_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                           'show_horizontal_resolution',
                                           step=step, index=index)[0])
    vertical_resolution = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                         'show_vertical_resolution',
                                         step=step, index=index)[0])
    margin = float(schema.get('tool', 'klayout', 'task', task, 'var',
                              'margin',
                              step=step, index=index)[0])
    linewidth = int(schema.get('tool', 'klayout', 'task', task, 'var',
                               'linewidth',
                               step=step, index=index)[0])
    oversampling = int(schema.get('tool', 'klayout', 'task', task, 'var',
                                  'oversampling',
                                  step=step, index=index)[0])

    view.zoom_fit()
    cell = view.active_cellview().cell

    view_box = cell.dbbox()
    view_box.left -= margin
    view_box.bottom -= margin
    view_box.right += margin
    view_box.top += margin

    x_incr = int(view_box.width() / xbins)
    y_incr = int(view_box.height() / ybins)

    if (view_box.width() > view_box.height()):
        y_px = vertical_resolution
        x_px = int((float(x_incr) / y_incr) * y_px)
    else:
        x_px = horizontal_resolution
        y_px = int((float(y_incr) / x_incr) * x_px)

    for x in range(xbins):
        for y in range(ybins):
            yidx = ybins - y - 1
            output_file = f"{design}_X{x}_Y{yidx}.png"

            x_start = view_box.left + x_incr * x
            y_start = view_box.bottom + y_incr * y

            subbox = pya.DBox(
                x_start,
                y_start,
                x_start + x_incr,
                y_start + y_incr)

            sub_img_spec = {
                "width": x_px,
                "height": y_px,
                "linewidth": linewidth,
                "oversampling": oversampling,
                "resolution": 0,
                "target_box": subbox,
                "monochrome": False
            }

            img_path = os.path.join('outputs', output_file)
            print(f'[INFO] Saving screenshot (({subbox.left}, {subbox.bottom}), '
                  f'({subbox.right}, {subbox.top})) to {img_path}')
            view.save_image_with_options(
                img_path,
                sub_img_spec["width"],
                sub_img_spec["height"],
                sub_img_spec["linewidth"],
                sub_img_spec["oversampling"],
                sub_img_spec["resolution"],
                sub_img_spec["target_box"],
                sub_img_spec["monochrome"]
            )


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

    if 'show_filepath' in schema.getkeys('tool', 'klayout', 'task', task, 'var') and \
       schema.get('tool', 'klayout', 'task', task, 'var', 'show_filepath',
                  step=step, index=index):
        sc_filename = schema.get('tool', 'klayout', 'task', task, 'var', 'show_filepath',
                                 step=step, index=index)[0]
    else:
        sc_fileext = schema.get('tool', 'klayout', 'task', task, 'var', 'show_filetype',
                                step=step, index=index)[0]
        sc_filename = f"inputs/{design}.{sc_fileext}"

    sc_exit = schema.get('tool', 'klayout', 'task', task, 'var', 'show_exit',
                         step=step, index=index) == ["true"]

    show(schema, technology(design, schema), sc_filename, f'outputs/{design}.png',
         screenshot=(step == 'screenshot'))

    if sc_exit:
        pya.Application.instance().exit(0)


if __name__ == '__main__':
    main()
