'''
Performs a sequence of layout operations on a stream file.

The sequence, and the arguments of each operation in it, come from the
operations task. See
:class:`~siliconcompiler.tools.klayout.operations.OperationsTask`.
'''
import pya
import sys

import os.path

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


# Keypath to the operations task variables, and the node being run.
# Filled in by the __main__ block below.
SC_OPS_ROOT: Optional[Tuple[str, ...]] = None
SC_STEP: Optional[str] = None
SC_INDEX: Optional[str] = None


def read_layout(stream_file: str) -> pya.Layout:
    '''
    Reads a stream file into a new layout.

    Args:
        stream_file (str): path to the stream file.

    Returns:
        The layout that was read.
    '''
    print(f"[INFO] Reading '{stream_file}'")
    layout = pya.Layout()
    layout.read(stream_file)

    return layout


def get_field(schema: Any, opname: str, field: str) -> Any:
    '''
    Returns the value of one field of one operation.

    The '.' joining the two is ``KLayoutOperation.SEPARATOR``, spelled out here
    because this script runs in KLayout's interpreter and cannot import
    SiliconCompiler.

    Args:
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation.
        field (str): name of the field.
    '''
    return schema.get(*SC_OPS_ROOT, f"{opname}.{field}", step=SC_STEP, index=SC_INDEX)


def __with_timestamps(schema: Any) -> bool:
    '''
    Returns whether streams should be written with timestamps.

    Args:
        schema (SafeSchema): manifest for this node.
    '''
    return schema.get(*SC_OPS_ROOT, 'timestamps', step=SC_STEP, index=SC_INDEX)


def __do_cell_swap(parent: pya.Cell, old_cell_idx: int, new_cell: pya.Cell,
                   checked: List[int]) -> int:
    '''
    Recursively repoints every instance of one cell at another.

    Args:
        parent (pya.Cell): cell to search.
        old_cell_idx (int): index of the cell being replaced.
        new_cell (pya.Cell): cell to replace it with.
        checked (list of int): indexes of the cells already visited.

    Returns:
        Number of instances that were repointed.
    '''
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


def swap_cells(base_layout: pya.Layout, oldcell: str, newcell: str) -> pya.Layout:
    '''
    Replaces every instance of a cell with another and deletes the original.

    Args:
        base_layout (pya.Layout): layout to modify.
        oldcell (str): name of the cell to replace.
        newcell (str): name of the cell to replace it with.

    Returns:
        The modified layout.
    '''
    top_cell = base_layout.top_cell()
    old_cell = base_layout.cell(oldcell)
    new_cell = base_layout.cell(newcell)

    if (old_cell is None):
        print(f"[WARNING] Unable to find '{oldcell}' to swap")
        return base_layout
    if (new_cell is None):
        print(f"[WARNING] Unable to find '{newcell}' to swap to")
        return base_layout

    checked = []
    replacements = __do_cell_swap(top_cell, old_cell.cell_index(), new_cell, checked)
    print(f"[INFO] Swapping '{old_cell.name}' to '{new_cell.name}' in "
          f"'{top_cell.name}': {replacements} occurrences")
    base_layout.delete_cell(old_cell.cell_index())

    return base_layout


def add_outline(base_layout: pya.Layout, layer: int) -> pya.Layout:
    '''
    Draws a box covering the top cell bounding box.

    Args:
        base_layout (pya.Layout): layout to modify.
        layer (int): index of the layer to draw on.

    Returns:
        The modified layout.
    '''
    top_cell = base_layout.top_cell()
    bbox = top_cell.bbox()

    layer_info = base_layout.get_info(layer)
    print(f"[INFO] Adding outline to '{top_cell.name}' on layer '{layer_info.to_s()}'")

    shapes = top_cell.shapes(layer)
    shapes.insert(pya.Box(bbox))

    return base_layout


def add_layout(base_layout: pya.Layout, layout: pya.Layout) -> pya.Layout:
    '''
    Copies another layout in as a new cell and instances it in the top cell.

    Args:
        base_layout (pya.Layout): layout to modify.
        layout (pya.Layout): layout to add.

    Returns:
        The modified layout.
    '''
    top_cell = base_layout.top_cell()

    other_layout_top = layout.top_cell()

    print(f"[INFO] Adding layout from '{other_layout_top.name}' to '{top_cell.name}'")
    new_cell = base_layout.create_cell(other_layout_top.name)
    new_cell.copy_tree(other_layout_top)

    cell_inst = pya.CellInstArray(new_cell.cell_index(), pya.Trans())
    top_cell.insert(cell_inst)

    return base_layout


def add_layout_to_top(base_layout: pya.Layout, new_top_cell_name: str) -> pya.Layout:
    '''
    Adds a new top cell holding an instance of the current top cell.

    Args:
        base_layout (pya.Layout): layout to modify.
        new_top_cell_name (str): name for the new top cell.

    Returns:
        The modified layout.
    '''
    top_cell = base_layout.top_cell()

    print(f"[INFO] Adding layout from '{top_cell.name}' to new top cell '{new_top_cell_name}'")
    new_cell = base_layout.create_cell(new_top_cell_name)

    cell_inst = pya.CellInstArray(top_cell.cell_index(), pya.Trans())
    new_cell.insert(cell_inst)

    return base_layout


def merge_layouts(layout1: pya.Layout, layout2: pya.Layout) -> pya.Layout:
    '''
    Merges the top cell of one layout into the top cell of another.

    Args:
        layout1 (pya.Layout): layout to merge into.
        layout2 (pya.Layout): layout to merge from.

    Returns:
        The modified layout.
    '''
    cell1 = layout1.top_cell()
    cell2 = layout2.top_cell()

    print(f"[INFO] Merging cells '{cell1.name}' and '{cell2.name}' into '{cell1.name}'")

    cell1.copy_tree(cell2)

    return layout1


def rotate_layout(base_layout: pya.Layout, angle: int) -> pya.Layout:
    '''
    Rotates the top cell about the lower left corner of its bounding box.

    Args:
        base_layout (pya.Layout): layout to modify.
        angle (int): rotation in degrees, one of 0, 90, 180 or 270.

    Returns:
        The modified layout.
    '''
    if angle == 0:
        print("[INFO] Skipping rotation of 0 degrees")
        return base_layout

    top_cell = base_layout.top_cell()
    bbox = top_cell.bbox()

    print(f"[INFO] Rotating layout '{top_cell.name}' {angle} degrees")

    rotations = {
        90: (pya.Trans.R270, pya.Vector(0, bbox.p2.x)),
        180: (pya.Trans.R180, pya.Vector(bbox.p2.x, bbox.p2.y)),
        270: (pya.Trans.R90, pya.Vector(bbox.p2.y, -bbox.p1.x))
    }
    rotation, displacement = rotations[angle]

    top_cell.transform(pya.Trans(rotation, displacement))

    return base_layout


def rename_top(base_layout: pya.Layout, new_name: str) -> pya.Layout:
    '''
    Renames the top cell.

    Args:
        base_layout (pya.Layout): layout to modify.
        new_name (str): new name for the top cell.

    Returns:
        The modified layout.
    '''
    top_cell = base_layout.top_cell()
    print(f"[INFO] Renaming '{top_cell.name}' to '{new_name}' layout: '{top_cell.name}'")
    top_cell.name = new_name
    return base_layout


def rename_cell(base_layout: pya.Layout, old_name: str, new_name: str) -> pya.Layout:
    '''
    Renames one cell, warning if it cannot be found.

    Args:
        base_layout (pya.Layout): layout to modify.
        old_name (str): name of the cell to rename.
        new_name (str): new name for the cell.

    Returns:
        The modified layout.
    '''
    cell = base_layout.cell(old_name)
    if not cell:
        print(f"[WARNING] Unable to find '{old_name}' to rename")
        return base_layout
    print(f"[INFO] Renaming '{cell.name}' to '{new_name}' layout: '{base_layout.top_cell().name}'")
    cell.name = new_name
    return base_layout


def write_stream(layout: pya.Layout, outfile: str, timestamps: bool) -> None:
    '''
    Writes a layout to a stream file.

    Args:
        layout (pya.Layout): layout to write.
        outfile (str): path to write to.
        timestamps (bool): whether to include timestamps in the stream.
    '''
    from klayout_utils import get_write_options

    print(f"[INFO] Writing layout: '{outfile}'")

    layout.write(outfile, get_write_options(outfile, timestamps))


def make_property_text(layout: pya.Layout, property_layer: int,
                       property_name: Union[int, str],
                       destination_layer: int) -> pya.Layout:
    '''
    Converts a stream property into text labels on the design.

    Args:
        layout (pya.Layout): layout to modify.
        property_layer (int): index of the layer holding the property.
        property_name (int or str): property number or name.
        destination_layer (int): index of the layer to write the labels to.

    Returns:
        The modified layout.
    '''
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


def delete_layers(layout: pya.Layout, layers: Sequence[int]) -> pya.Layout:
    '''
    Deletes every shape on the given layers, in every cell.

    Args:
        layout (pya.Layout): layout to modify.
        layers (sequence of int): indexes of the layers to clear.

    Returns:
        The modified layout.
    '''
    for cell in layout.each_cell():
        print(f'[INFO] Deleting layers from {cell.name}')
        for layer in layers:
            layer_info = layout.get_info(layer)
            print(f"[INFO] Deleting layer {layer_info.to_s()}")

            cell.shapes(layer).clear()

    return layout


def merge_shapes(layout: pya.Layout, layers: Sequence[int]) -> pya.Layout:
    '''
    Merges overlapping shapes on the given layers, in every cell.

    Args:
        layout (pya.Layout): layout to modify.
        layers (sequence of int): indexes of the layers to merge shapes on.

    Returns:
        The modified layout.
    '''
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

    return layout


def flatten(layout: pya.Layout) -> pya.Layout:
    '''
    Flattens the hierarchy of the top cell.

    Args:
        layout (pya.Layout): layout to modify.

    Returns:
        The modified layout.
    '''
    top_cell = layout.top_cell()

    print(f"[INFO] Flattening: {top_cell.name}")
    top_cell.flatten(True)

    return layout


###############################################################
# Operation handlers
###############################################################
def op_merge(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Merges the streams named by a ``merge`` operation into the layout.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    for op_file in __stream_sources(schema, opname):
        layout = merge_layouts(layout, read_layout(op_file))
    return layout


def op_add(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Adds the streams named by an ``add`` operation to the layout.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    for op_file in __stream_sources(schema, opname):
        layout = add_layout(layout, read_layout(op_file))
    return layout


def __stream_sources(schema: Any, opname: str) -> List[str]:
    '''
    Returns the streams a merge or add operation reads.

    Args:
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation.

    Raises:
        ValueError: if the operation names neither a file nor an input.
    '''
    files = get_field(schema, opname, "file")
    if files:
        return files

    input_file = get_field(schema, opname, "input")
    if not input_file:
        raise ValueError(f"'{opname}' requires a file or an input")
    return [os.path.join('inputs', input_file)]


def op_rotate(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Rotates the layout.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    return rotate_layout(layout, get_field(schema, opname, "angle"))


def op_flatten(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Flattens the hierarchy of the top cell.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    return flatten(layout)


def op_outline(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Draws a box around the top cell bounding box.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    layer, purpose = get_field(schema, opname, "layer")
    return add_outline(layout, layout.layer(layer, purpose))


def op_rename(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Renames the top cell.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    return rename_top(layout, get_field(schema, opname, "cellname"))


def op_add_top(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Adds a new top cell above the current one.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    return add_layout_to_top(layout, get_field(schema, opname, "cellname"))


def op_rename_cell(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Renames the cells named by the operation.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    for oldcell, newcell in get_field(schema, opname, "cells"):
        layout = rename_cell(layout, oldcell, newcell)
    return layout


def op_swap(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Replaces instances of the cells named by the operation.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    for oldcell, newcell in get_field(schema, opname, "cells"):
        layout = swap_cells(layout, oldcell, newcell)
    return layout


def op_delete_layers(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Deletes every shape on the layers named by the operation.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    layers = [layout.layer(layer, purpose)
              for layer, purpose in get_field(schema, opname, "layers")]
    return delete_layers(layout, layers)


def op_merge_shapes(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Merges overlapping shapes on the layers named by the operation.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    if get_field(schema, opname, "all"):
        layers = layout.layer_indexes()
    else:
        layers = [layout.layer(layer, purpose)
                  for layer, purpose in get_field(schema, opname, "layers")]
    return merge_shapes(layout, layers)


def op_convert_property(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Converts a stream property into text labels on the design.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    source = get_field(schema, opname, "source")
    dest = get_field(schema, opname, "dest")
    if not dest:
        dest = source

    prop_number = get_field(schema, opname, "property")
    if prop_number.isnumeric():
        prop_number = int(prop_number)

    return make_property_text(layout,
                              layout.layer(source[0], source[1]),
                              prop_number,
                              layout.layer(dest[0], dest[1]))


def op_write(layout: pya.Layout, schema: Any, opname: str) -> pya.Layout:
    '''
    Writes an intermediate copy of the layout.

    Args:
        layout (pya.Layout): layout to modify.
        schema (SafeSchema): manifest for this node.
        opname (str): name of the operation to read the arguments from.

    Returns:
        The modified layout.
    '''
    write_stream(layout,
                 os.path.join('outputs', get_field(schema, opname, "filename")),
                 __with_timestamps(schema))
    return layout


# Dispatch table, keyed on the operation type recorded in the task's list of
# operations. Every handler takes and returns the layout being operated on.
OPERATIONS: Dict[str, Callable[[pya.Layout, Any, str], pya.Layout]] = {
    "merge": op_merge,
    "add": op_add,
    "rotate": op_rotate,
    "flatten": op_flatten,
    "outline": op_outline,
    "rename": op_rename,
    "add_top": op_add_top,
    "rename_cell": op_rename_cell,
    "swap": op_swap,
    "delete_layers": op_delete_layers,
    "merge_shapes": op_merge_shapes,
    "convert_property": op_convert_property,
    "write": op_write
}


def parse_operations(schema: Any, base_layout: pya.Layout,
                     operations: Sequence[Tuple[str, str]]) -> pya.Layout:
    '''
    Performs a sequence of operations on a layout, in order.

    Args:
        schema (SafeSchema): manifest for this node.
        base_layout (pya.Layout): layout to modify.
        operations (sequence of tuple of str): (operation type, operation name)
            pairs naming the operations to perform.

    Raises:
        ValueError: if an operation type has no handler.

    Returns:
        The modified layout.
    '''
    for optype, opname in operations:
        if optype not in OPERATIONS:
            raise ValueError(f"Unknown operation: {optype}")

        base_layout = OPERATIONS[optype](base_layout, schema, opname)

    return base_layout


if __name__ == "__main__":
    # SC_ROOT provided by CLI
    sys.path.append(SC_KLAYOUT_ROOT)  # noqa: F821
    sys.path.append(SC_TOOLS_ROOT)  # noqa: F821
    sys.path.append(SC_ROOT)  # noqa: F821

    from klayout_utils import (
        technology,
        get_streams,
        get_schema,
        generate_metrics
    )

    schema = get_schema(manifest='sc_manifest.json')

    # Extract info from manifest
    SC_STEP = schema.get('arg', 'step')
    SC_INDEX = schema.get('arg', 'index')
    SC_OPS_ROOT = ('tool', 'klayout', 'task', 'operations', 'var')

    sc_ext = get_streams(schema)[0]

    design_name = schema.get('option', 'design')
    fileset = schema.get("option", "fileset")[0]
    design = schema.get("library", design_name, "fileset", fileset, "topmodule")
    if not design:
        design = design_name

    in_gds = os.path.join('inputs', f'{design}.{sc_ext}.gz')
    if not os.path.exists(in_gds):
        in_gds = os.path.join('inputs', f'{design}.{sc_ext}')
    if not os.path.exists(in_gds):
        in_gds = schema.get('input', 'layout', sc_ext)[0]
    out_gds = os.path.join('outputs', f'{design}.{sc_ext}.gz')

    tech = technology(design, schema)
    base_layout = read_layout(in_gds)
    base_layout.technology_name = tech.name

    sc_klayout_ops = schema.get(*SC_OPS_ROOT, 'operations', step=SC_STEP, index=SC_INDEX)
    base_layout = parse_operations(schema, base_layout, sc_klayout_ops)

    write_stream(base_layout, out_gds, __with_timestamps(schema))

    generate_metrics()
