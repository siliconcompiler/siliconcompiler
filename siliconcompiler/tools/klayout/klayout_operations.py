import pya

import sys
import os


def read_layout(stream_file):
    print(f"[INFO] Reading '{stream_file}'")
    layout = pya.Layout()
    layout.read(stream_file)

    return layout


def __with_timestamps(schema):
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')

    return schema.get('tool', 'klayout', 'task', 'operations', 'var', 'timestamps',
                      step=sc_step, index=sc_index) == ['true']


def __get_keypath_step_index(schema, *keypath):
    ret = {
        'step': schema.get('arg', 'step'),
        'index': schema.get('arg', 'index')
    }
    pernode = schema.get(*keypath, field='pernode')
    if pernode == 'never':
        ret['step'] = None
        ret['index'] = None

    return ret


def __do_cell_swap(parent, old_cell_idx, new_cell, checked):
    if (parent.cell_index() in checked):
        return 0

    checked.append(parent.cell_index())
    replacements = 0
    for inst in parent.each_inst():
        if (inst.cell_index == old_cell_idx):
            inst.cell = new_cell
            replacements += 1
        else:
            replacements += __do_cell_swap(inst.cell, old_cell_idx, new_cell, checked)
    return replacements


def swap_cells(base_layout, oldcell, newcell):
    top_cell = base_layout.top_cell()
    old_cell = base_layout.cell(oldcell)
    new_cell = base_layout.cell(newcell)

    if (old_cell is None):
        return base_layout
    if (new_cell is None):
        return base_layout

    checked = []
    replacements = __do_cell_swap(top_cell, old_cell.cell_index(), new_cell, checked)
    print(f"[INFO] Swapping '{old_cell.name}' to '{new_cell.name}' in "
          f"'{top_cell.name}': {replacements} occurrences")
    base_layout.delete_cell(old_cell.cell_index())

    return base_layout


def add_outline(base_layout, layer):
    top_cell = base_layout.top_cell()
    bbox = top_cell.bbox()

    layer_info = base_layout.get_info(layer)
    print(f"[INFO] Adding outline to '{top_cell.name}' on layer '{layer_info.to_s()}'")

    shapes = top_cell.shapes(layer)
    shapes.insert(pya.Box(bbox))

    return base_layout


def add_layout(base_layout, layout):
    top_cell = base_layout.top_cell()

    other_layout_top = layout.top_cell()

    print(f"[INFO] Adding layout from '{other_layout_top.name}' to '{top_cell.name}'")
    new_cell = base_layout.create_cell(other_layout_top.name)
    new_cell.copy_tree(other_layout_top)

    cell_inst = pya.CellInstArray(new_cell.cell_index(), pya.Trans())
    top_cell.insert(cell_inst)

    return base_layout


def add_layout_to_top(base_layout, new_top_cell_name):
    top_cell = base_layout.top_cell()

    print(f"[INFO] Adding layout from '{top_cell.name}' to new top cell '{new_top_cell_name}'")
    new_cell = base_layout.create_cell(new_top_cell_name)

    cell_inst = pya.CellInstArray(top_cell.cell_index(), pya.Trans())
    new_cell.insert(cell_inst)

    return base_layout


def merge_layouts(layout1, layout2):
    cell1 = layout1.top_cell()
    cell2 = layout2.top_cell()

    print(f"[INFO] Merging cells '{cell1.name}' and '{cell2.name}' into '{cell1.name}'")

    cell1.copy_tree(cell2)

    return layout1


def rotate_layout(base_layout):
    top_cell = base_layout.top_cell()
    bbox = top_cell.bbox()

    print(f"[INFO] Rotating layout '{top_cell.name}' 90 degrees")

    transform = pya.Trans.R270
    transform = pya.Trans(transform, pya.Vector(0, bbox.p2.x))

    top_cell.transform(transform)

    return base_layout


def rename_top(base_layout, new_name):
    top_cell = base_layout.top_cell()
    print(f"[INFO] Renaming '{top_cell.name}' to '{new_name}' layout: '{top_cell.name}'")
    top_cell.name = new_name
    return base_layout


def write_stream(layout, outfile, timestamps):
    print(f"[INFO] Writing layout: '{outfile}'")

    write_options = pya.SaveLayoutOptions()
    write_options.gds2_write_timestamps = timestamps

    layout.write(outfile, write_options)


def make_property_text(layout, property_layer, property_name, destination_layer):
    property_layer_info = layout.get_info(property_layer)
    destination_layer_info = layout.get_info(destination_layer)
    print(f"[INFO] Generating properties from {property_layer_info.to_s()} "
          f"/ {property_name} on {destination_layer_info.to_s()}")

    top_cell = layout.top_cell()
    # Generate list of text objects
    source_shapes_itr = top_cell.begin_shapes_rec(property_layer)
    dest_shapes = []
    while (not source_shapes_itr.at_end()):
        shape = source_shapes_itr.shape()
        shape_prop = shape.property(property_name)
        if (shape_prop is not None and (shape.is_box() or shape.is_polygon())):
            shape_center = shape.bbox().center()
            dest_shapes.append(pya.Text(shape_prop, shape_center.x, shape_center.y))
        source_shapes_itr.next()

    # Insert objects
    dest_shapes_layer = top_cell.shapes(destination_layer)
    for shape in dest_shapes:
        dest_shapes_layer.insert(shape)

    print(f"[INFO] Generated {len(dest_shapes)} text shapes.")

    return layout


def delete_layers(layout, layers):
    for cell in layout.each_cell():
        print(f'[INFO] Deleting layers from {cell.name}')
        for layer in layers:
            layer_info = layout.get_info(layer)
            print(f"[INFO] Deleting layer {layer_info.to_s()}")

            cell.shapes(layer).clear()

    return layout


def merge_shapes(layout, layers):
    if layers == ['all']:
        layers = layout.layer_indexes()

    for cell in layout.each_cell():
        print(f"[INFO] Merging shapes in {cell.name}")
        for layer in layers:
            layer_info = layout.get_info(layer)
            print(f"[INFO] Merging shapes on layer {layer_info.to_s()}")

            shape_proc = pya.ShapeProcessor()
            output_shapes = pya.Shapes()

            cell_layout = cell.layout()
            print("  Shape count (old):", cell.shapes(layer).size())
            shape_proc.boolean(cell_layout,
                               cell,
                               layer,
                               cell_layout,
                               cell,
                               layer,
                               output_shapes,
                               pya.EdgeProcessor.ModeOr,
                               True,
                               True,
                               True)
            print("  Shape count (new):", output_shapes.size())
            cell.shapes(layer).clear()
            cell.shapes(layer).insert(output_shapes)


def flatten(layout):
    top_cell = layout.top_cell()

    print(f"[INFO] Flattening: {top_cell.name}")
    top_cell.flatten(True)

    return layout


def parse_operations(schema, base_layout, steps):
    for step in steps:
        step = step.split(":")
        step_name = step[0]
        step_args = ":".join(step[1:])
        args_key = step_args.split(',')

        if (step_name == "merge" or step_name == "add"):
            files = []
            if len(args_key) > 1:
                if 'file' not in schema.get(*args_key, field='type'):
                    raise ValueError(f'{step_name} requires {args_key} be a file type')
                files = schema.get(*args_key, **__get_keypath_step_index(schema, *args_key))
            else:
                files = [f'inputs/{step_args}']
            for op_file in files:
                if step_name == "add":
                    base_layout = add_layout(base_layout, read_layout(op_file))
                else:
                    base_layout = merge_layouts(base_layout, read_layout(op_file))
        elif (step_name == "rotate"):
            base_layout = rotate_layout(base_layout)
        elif (step_name == "outline"):
            outline_layer = [int(layer) for layer in schema.get(
                *args_key, **__get_keypath_step_index(schema, *args_key))]
            if len(outline_layer) != 2:
                raise ValueError('outline layer requires two entries for layer and purpose, '
                                 f'received: {len(outline_layer)}')
            base_layout = add_outline(base_layout,
                                      base_layout.layer(outline_layer[0], outline_layer[1]))
        elif (step_name == "convert_property"):
            options = schema.get(*args_key, **__get_keypath_step_index(schema, *args_key))
            if len(options) != 3 and len(options) != 5:
                raise ValueError(f'{step_name} requires 3 or 5 arguments in {args_key}')
            prop_layer = [int(layer) for layer in options[0:2]]
            prop_number = options[2]
            if prop_number.isnumeric():
                prop_number = int(prop_number)
            if (len(options) == 5):
                dest_layer = [int(layer) for layer in options[3:]]
            else:
                dest_layer = prop_layer
            base_layout = make_property_text(base_layout,
                                             base_layout.layer(prop_layer[0], prop_layer[1]),
                                             prop_number,
                                             base_layout.layer(dest_layer[0], dest_layer[1]))
        elif (step_name == "rename"):
            new_name = schema.get(*args_key, **__get_keypath_step_index(schema, *args_key))[0]
            base_layout = rename_top(base_layout, new_name)
        elif (step_name == "swap"):
            for swapset in schema.get(*args_key, **__get_keypath_step_index(schema, *args_key)):
                oldcell, newcell = swapset.split("=")
                base_layout = swap_cells(base_layout, oldcell, newcell)
        elif (step_name == "add_top"):
            new_name = schema.get(*args_key, **__get_keypath_step_index(schema, *args_key))[0]
            base_layout = add_layout_to_top(base_layout, new_name)
        elif (step_name == "write"):
            write_stream(base_layout, f'outputs/{step_args}', __with_timestamps(schema))
        elif (step_name == "flatten"):
            base_layout = flatten(base_layout)
        elif (step_name == "delete_layers"):
            layers = []
            for layer in schema.get(*args_key, **__get_keypath_step_index(schema, *args_key)):
                layer_num = None
                layer_purpose = None
                if '/' in layer:
                    layer_num, layer_purpose = layer.split('/')
                elif ' ' in layer:
                    layer_num, layer_purpose = layer.split(' ')
                elif ':' in layer:
                    layer_num, layer_purpose = layer.split(':')
                else:
                    raise ValueError(f'Unable to determine layer purpose pair for {layer}')
                layers.append(base_layout.layer(int(layer_num), int(layer_purpose)))
            base_layout = delete_layers(base_layout, layers)
        elif (step_name == "merge_shapes"):
            layers = schema.get(*args_key, **__get_keypath_step_index(schema, *args_key))
            base_layout = merge_shapes(base_layout, layers)
        else:
            raise ValueError(f"Unknown step: {step_name}")


if __name__ == "__main__":
    # SC_ROOT provided by CLI
    sys.path.append(SC_ROOT)  # noqa: F821

    from schema import Schema
    from tools.klayout.klayout_utils import technology, get_streams

    schema = Schema(manifest='sc_manifest.json')

    # Extract info from manifest
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_tool = 'klayout'
    sc_task = 'operations'

    sc_ext = get_streams(schema)[0]
    design = schema.get('option', 'entrypoint')
    if not design:
        design = schema.get('design')

    in_gds = os.path.join('inputs', f'{design}.{sc_ext}')
    if not os.path.exists(in_gds):
        in_gds = schema.get('input', 'layout', sc_ext)[0]
    out_gds = os.path.join('outputs', f'{design}.{sc_ext}')

    tech = technology(design, schema)
    base_layout = read_layout(in_gds)
    base_layout.technology_name = tech.name

    sc_klayout_ops = schema.get('tool', sc_tool, 'task', sc_task, 'var', 'operations',
                                step=sc_step, index=sc_index)
    parse_operations(schema, base_layout, sc_klayout_ops)

    write_stream(base_layout, out_gds, __with_timestamps(schema))
