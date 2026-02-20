"""
KLayout script to convert a GDS/OASIS stream file into a LEF file.

This script is designed to be run in KLayout's batch mode. It reads a
design's stream file (GDS or OASIS) and a layermap, and generates a
corresponding LEF macro file. It extracts pin information from text labels
on specified layers and defines obstruction geometries.
"""
import pya
import fnmatch
import os
import sys

from typing import Dict, List, Optional, Set, Tuple


def get_pins(cell: pya.Cell, layers: Dict[str, Set[Tuple[int, int]]]) -> \
        Dict[str, Dict[str, List[pya.Shape]]]:
    """
    Finds pin shapes in a cell based on text labels.

    This function iterates through specified layers, looking for text shapes.
    When a text shape is found, it identifies other shapes on the same layer
    that are touching the center of the text shape. These touching shapes
    are considered part of the pin.

    Args:
        cell (pya.Cell): The KLayout cell to search for pins.
        layers (Dict[str, Set[Tuple[int, int]]]): A dictionary mapping layer names
            to a set of (layer_number, datatype) tuples.

    Returns:
        Dict[str, Dict[str, List[pya.Shape]]]: A dictionary where keys are pin names (from text).
            The values are another dictionary mapping layer names to a list of pin shapes.
    """
    pins: Dict[str, Dict[str, List[pya.Shape]]] = {}
    for layer_name, datatypes in layers.items():
        for layer_number, datatype in datatypes:
            layer = cell.layout().layer(layer_number, datatype)
            for shape in cell.shapes(layer):
                if shape.is_text():
                    center = shape.dbbox().center()
                    for check_shape in cell.begin_shapes_rec_touching(layer,
                                                                      pya.DBox(center, center)):
                        if shape == check_shape.shape():
                            continue
                        pins.setdefault(shape.text_string,
                                        {}).setdefault(layer_name,
                                                       []).append(check_shape.shape())
    return pins


def get_obs(cell: pya.Cell, layers: Dict[str, Set[Tuple[int, int]]], datatype: int) -> \
        Dict[str, List[pya.Shape]]:
    """
    Extracts obstruction shapes from a cell.

    This function iterates through specified layers and collects all shapes
    on those layers with a specific datatype, treating them as obstructions.

    Args:
        cell (pya.Cell): The KLayout cell to search for obstructions.
        layers (Dict[str, Set[Tuple[int, int]]]): A dictionary mapping layer names
            to a set of (layer_number, datatype) tuples. The datatype in this
            dictionary is ignored.
        datatype (int): The datatype to use for identifying obstruction layers.

    Returns:
        Dict[str, List[pya.Shape]]: A dictionary mapping layer names to a list
            of obstruction shapes.
    """
    obs: Dict[str, List[pya.Shape]] = {}
    layout = cell.layout()
    for layer_name, layer_data in layers.items():
        layer_number, _ = list(layer_data)[0]
        for shape in cell.shapes(layout.layer(layer_number, datatype)):
            obs.setdefault(layer_name, []).append(shape)
    return obs


def print_shape(prefix: str, shape: pya.Shape, file) -> None:
    """
    Prints a KLayout shape to a file in LEF format.

    Supports boxes, polygons, and paths (which are converted to polygons).

    Args:
        prefix (str): A string prefix for each line (e.g., for indentation).
        shape (pya.Shape): The KLayout shape to print.
        file: The file object to write to.
    """
    if shape.is_box():
        box = shape.dbox
        print(f"{prefix}RECT {box.left:.4f} {box.bottom:.4f} {box.right:.4f} {box.top:.4f} ;",
              file=file)
    elif shape.is_polygon():
        points = []
        for pt in shape.dpolygon.each_point_hull():
            points.append(f"{pt.x:.4f} {pt.y:.4f}")
        points = " ".join(points)
        print(f"{prefix}POLYGON {points} ;", file=file)
    elif shape.is_path():
        points = []
        for pt in shape.dpath.simple_polygon.each_point_hull():
            points.append(f"{pt.x:.4f} {pt.y:.4f}")
        points = " ".join(points)
        print(f"{prefix}POLYGON {points} ;", file=file)


def cleanup_cell(cell: pya.Cell, layers: Dict[str, Set[Tuple[int, int]]], layer_type: int):
    """
    Merges shapes on specified layers for LEF generation.

    This function prepares a cell for LEF export by:
    1.  Creating merged obstruction layers: For each layer/datatype pair defined
        in `layers`, it merges all shapes and copies the result to a new layer.
        This new layer has the same layer number but a new `layer_type`.
    2.  Merging the newly created obstruction layers: It performs a second merge
        pass on the obstruction layers to combine shapes that might have been
        generated from different original datatypes but map to the same
        obstruction layer.

    Args:
        cell (pya.Cell): The KLayout cell to process.
        layers (Dict[str, Set[Tuple[int, int]]]): A dictionary mapping layer names
            to a set of (layer_number, datatype) tuples.
        layer_type (int): The new datatype to use for the merged obstruction layers.
    """
    shape_proc = pya.ShapeProcessor()
    layout = cell.layout()
    for _, layer_data in layers.items():
        for layer_number, datatype in layer_data:
            output_shapes = pya.Shapes()
            shape_proc.boolean(
                layout,
                cell,
                layout.layer(layer_number, datatype),
                layout,
                cell,
                layout.layer(layer_number, datatype),
                output_shapes,
                pya.EdgeProcessor.ModeOr,
                True,
                True,
                True)
            cell.shapes(layout.layer(layer_number, layer_type)).insert(output_shapes)

    for _, layer_data in layers.items():
        output_shapes = pya.Shapes()

        layer_number, _ = list(layer_data)[0]
        layer = layout.layer(layer_number, layer_type)

        shape_proc.boolean(
            layout,
            cell,
            layer,
            layout,
            cell,
            layer,
            output_shapes,
            pya.EdgeProcessor.ModeOr,
            True,
            True,
            True)
        cell.shapes(layer).clear()
        cell.shapes(layer).insert(output_shapes)


def parse_layermap(file_path: str) -> List[Tuple[str, str, int, int]]:
    """
    Parses a GDSII/OASIS layermap file.

    Args:
        file_path (str): Path to the layermap file.

    Returns:
        list of tuples: Each tuple contains (LayerName, Purpose, StreamNumber, DataType).
                        Example: [('V0', 'PIN', 18, 251), ...]
    """
    layer_map_data = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace from the start and end
            line = line.strip()

            # Skip empty lines or lines starting with comments (#)
            if not line or line.startswith('#'):
                continue

            # Split the line by whitespace (handles tabs, spaces, and non-breaking spaces)
            parts = line.split()

            # Ensure there are at least 4 columns (Layer, Purpose, Stream, Datatype)
            if len(parts) >= 4:
                layer_name = parts[0]
                purpose = parts[1]

                try:
                    stream_number = int(parts[2])
                    datatype = int(parts[3])

                    # Add to list as a tuple
                    layer_map_data.append((layer_name, purpose, stream_number, datatype))
                except ValueError:
                    print(f"Warning: Skipping line {line_num} due to "
                          f"non-integer ID/Datatype: {line}")
                    continue

    return layer_map_data


def to_lef(gds_path: str, out_file: str, layers: Dict[str, Set[Tuple[int, int]]],
           ignore_cells: Set[str],
           class_name: str,
           site: Optional[str] = None,
           symmetry: Optional[List[str]] = None):
    layout = pya.Layout()
    layout.read(gds_path)

    for cell in layout.each_cell():
        for inst in cell.each_inst():
            inst.flatten()
    layout.cleanup()

    # Find the next available layer type for the cleanup shapes
    all_datatype = set()
    for layer in layout.layer_infos():
        all_datatype.add(layer.datatype)

    layer_type = 1
    while layer_type in all_datatype:
        layer_type += 1

    with open(out_file, "w") as file:
        for top_cell in layout.top_cells():
            if ignore_cells and any(fnmatch.fnmatch(top_cell.name, ignore)
                                    for ignore in ignore_cells):
                print(f"[INFO] Skipping cell '{top_cell.name}' as it matches ignore pattern")
                continue

            cleanup_cell(top_cell, layers, layer_type)

            bbox = top_cell.dbbox()
            origin_x = 0.0
            origin_y = 0.0
            if bbox.left != 0:
                origin_x = -bbox.left
            if bbox.bottom != 0:
                origin_y = -bbox.bottom

            macroname = top_cell.name.split("$")[0]

            print("MACRO " + macroname, file=file)
            print(f"  CLASS {class_name} ;", file=file)
            print(f"  ORIGIN {origin_x:.4f} {origin_y:.4f} ;", file=file)
            print(f"  FOREIGN {top_cell.name} {-origin_x:.4f} {-origin_y:.4f} ;", file=file)
            print(f"  SIZE {bbox.width():.4f} BY {bbox.height():.4f} ;", file=file)
            if not symmetry:
                symmetry = ["X", "Y", "R90"]
            print(f"  SYMMETRY {' '.join(symmetry)} ;", file=file)
            if site:
                print(f"  SITE {site} ;", file=file)

            for pin_name, pin_data in get_pins(top_cell, layers).items():
                print("  PIN " + pin_name, file=file)
                print("    DIRECTION INOUT ;", file=file)
                print("    USE SIGNAL ;", file=file)
                for layer_name, pin_shapes in pin_data.items():
                    for shape in pin_shapes:
                        print("    PORT", file=file)
                        print("      LAYER " + layer_name + " ;", file=file)
                        print_shape("      ", shape, file)
                        print("    END", file=file)
                print("  END " + pin_name, file=file)

            print("  OBS", file=file)
            for layer_name, osb_shapes in get_obs(top_cell, layers, datatype=layer_type).items():
                print(f"    LAYER {layer_name} ;", file=file)
                for obs in osb_shapes:
                    print_shape("      ", obs, file=file)
            print("  END", file=file)

            print(f"END {macroname}", file=file)


def main():
    """
    Main function for the stream-to-LEF conversion script.

    This script is executed by KLayout in batch mode. It parses command-line
    arguments, reads a SiliconCompiler schema, and then uses the `to_lef`
    function to perform the GDS/OASIS to LEF conversion.
    """
    # SC_ROOT provided by CLI, and is only accessible when this is main module
    sys.path.append(SC_KLAYOUT_ROOT)  # noqa: F821
    sys.path.append(SC_TOOLS_ROOT)  # noqa: F821
    sys.path.append(SC_ROOT)  # noqa: F821

    from klayout_utils import (
        technology,
        get_schema
    )

    schema = get_schema(manifest='sc_manifest.json')

    # Extract info from manifest
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')

    design_name = schema.get('option', 'design')
    fileset = schema.get("option", "fileset")[0]
    design = schema.get("library", design_name, "fileset", fileset, "topmodule")
    if not design:
        design = design_name

    sc_tech = technology(design, schema)

    load_options = sc_tech.load_layout_options
    map_file = load_options.lefdef_config.map_file
    if not map_file:
        print("[ERROR] No layermap file specified in technology. Cannot proceed with LEF export.")
        sys.exit(1)

    layers = {}
    for layer_name, layer_purpose, stream_number, datatype in parse_layermap(map_file):
        if layer_name == "NAME":
            layer_name = layer_purpose.split("/")[0]
        layers.setdefault(layer_name, set()).add((stream_number, datatype))

    ignore_cells = schema.get('tool', 'klayout', 'task', 'stream2lef', 'var', 'ignore_cells',
                              step=sc_step, index=sc_index)

    stream = schema.get('tool', 'klayout', 'task', 'stream2lef', 'var', 'stream',
                        step=sc_step, index=sc_index)

    in_gds = f"inputs/{design}.{stream}"
    if not os.path.exists(in_gds):
        for fileset in schema.get("option", "fileset"):
            if schema.valid("library", design_name, "fileset", fileset, "file", stream):
                in_gds = schema.get("library", design_name, "fileset", fileset, "file", stream)[0]
                break

    if not os.path.exists(in_gds):
        print(f"[ERROR] No GDS file found for design '{design}'. Cannot proceed with LEF export.")
        sys.exit(1)

    site = schema.get('tool', 'klayout', 'task', 'stream2lef', 'var', 'site',
                      step=sc_step, index=sc_index)
    class_name = schema.get('tool', 'klayout', 'task', 'stream2lef', 'var', 'class_name',
                            step=sc_step, index=sc_index)
    symmetry = schema.get('tool', 'klayout', 'task', 'stream2lef', 'var', 'symmetry',
                          step=sc_step, index=sc_index)

    to_lef(in_gds,
           f"outputs/{design}.lef",
           layers,
           ignore_cells,
           class_name,
           site,
           symmetry)


if __name__ == '__main__':
    main()
