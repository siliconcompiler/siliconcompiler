import sys
from typing import Tuple
import pya
import os.path


def png_to_gds(
    name: str,
    image_path: str,
    output_gds: str,
    technology,
    target_width_um: float,
    min_shape_um: float,
    layer_num: Tuple[int, int] = (1, 0),
    dark_is_solid: bool = True,
    invert: bool = False,
    timestamps: bool = True
):
    """
    Converts a PNG image to a GDSII layout using only KLayout's native API.

    :param image_path: Path to the input PNG image.
    :param output_gds: Path to the output GDS file.
    :param target_width_um: The desired total width of the image in the GDS (in microns).
    :param min_shape_um: The minimum allowable shape size (resolution limit) in microns.
    :param layer_num: The GDS layer number to draw the shapes on.
    :param dark_is_solid: Base logic - If True, dark pixels become GDS shapes.
    :param invert: Explicitly inverts the final polarity of the image.
    """
    from klayout_utils import get_write_options  # noqa E402

    # 1. Open the image using KLayout's native Image class
    print(f"Loading {image_path}...")
    img = pya.Image(image_path)

    if img.is_empty():
        raise ValueError("Image could not be loaded or is empty. Ensure it's a valid image.")

    orig_w = img.width()
    orig_h = img.height()

    # 2. Calculate pixel sizing and enforce minimum shape constraints
    raw_pixel_size = target_width_um / orig_w
    pixel_size_um = max(raw_pixel_size, min_shape_um)

    new_w = int(target_width_um / pixel_size_um)
    new_h = int((orig_h / orig_w) * new_w)

    print(f"Original resolution: {orig_w}x{orig_h}")
    print(f"Target GDS width: {target_width_um} µm")
    print(f"Effective pixel size: {pixel_size_um} µm")
    if new_w != orig_w or new_h != orig_h:
        print(f"Downsampling to {new_w}x{new_h} to respect minimum shape size...")

    # 3. Set up the KLayout database
    layout = pya.Layout()
    layout.dbu = technology.dbu
    top_cell = layout.create_cell(name)
    layer = layout.layer(layer_num[0], layer_num[1])

    # Use a Region to merge all individual pixel squares into optimized polygons.
    region = pya.Region()
    pixel_size_dbu = int(pixel_size_um / layout.dbu)

    # KLayout image properties
    is_color = img.is_color()

    # We set our binarization threshold at the 50% mark of the image's max value.
    # We fallback to 0.5 if max_value() returns 0 for any reason.
    threshold = (img.max_value / 2.0) if img.max_value > 0 else 0.5

    print("Generating GDS shapes...")
    # 4. Iterate through the target grid and sample the image
    for y_new in range(new_h):
        # Nearest-neighbor mapping back to original Y coordinate
        y_orig = int(y_new * orig_h / new_h)

        for x_new in range(new_w):
            # Nearest-neighbor mapping back to original X coordinate
            x_orig = int(x_new * orig_w / new_w)

            # Extract grayscale value from the native pya.Image
            if is_color:
                # Components: 0=R, 1=G, 2=B
                r = img.get_pixel(x_orig, y_orig, 0)
                g = img.get_pixel(x_orig, y_orig, 1)
                b = img.get_pixel(x_orig, y_orig, 2)
                # Standard luminance conversion
                val = 0.299 * r + 0.587 * g + 0.114 * b
            else:
                val = img.get_pixel(x_orig, y_orig)

            # Base binarization logic
            if dark_is_solid:
                is_solid = val < threshold
            else:
                is_solid = val >= threshold

            # Apply polarity inversion if requested
            if invert:
                is_solid = not is_solid

            # Insert a layout box if the pixel is solid
            if is_solid:
                # Image Y goes down, but GDS Y goes up. Flip Y to prevent upside-down layouts.
                x_dbu = x_new * pixel_size_dbu
                y_dbu = (new_h - 1 - y_new) * pixel_size_dbu

                box = pya.Box(x_dbu, y_dbu, x_dbu + pixel_size_dbu, y_dbu + pixel_size_dbu)
                region.insert(box)

    print("Merging adjacent pixels into optimized polygons...")
    region.merge()

    # 5. Insert the optimized region into the cell and save
    top_cell.shapes(layer).insert(region)
    layout.write(output_gds, get_write_options(output_gds, timestamps))
    print(f"GDS saved to {output_gds}")


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

    stream = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'stream',
                        step=sc_step, index=sc_index)
    format = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'imageformat',
                        step=sc_step, index=sc_index)
    minsize = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'minsize',
                         step=sc_step, index=sc_index)
    targetwidth = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'targetwidth',
                             step=sc_step, index=sc_index)
    layer = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'layer',
                       step=sc_step, index=sc_index)
    invert = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'invert',
                        step=sc_step, index=sc_index)
    darkissolid = schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'darkissolid',
                             step=sc_step, index=sc_index)

    sc_timestamps = schema.get('tool', 'klayout', 'task', "image2stream", 'var', 'timestamp',
                               step=sc_step, index=sc_index)

    in_image = f"inputs/{design}.{format}"
    if not os.path.exists(in_image):
        for fileset in schema.get("option", "fileset"):
            if schema.valid("library", design_name, "fileset", fileset, "file", format):
                in_image = schema.get("library", design_name, "fileset", fileset, "file", format)[0]
                break

    png_to_gds(
        name=design,
        image_path=in_image,
        output_gds=f"outputs/{design}.{stream}.gz",
        technology=technology(design, schema),
        target_width_um=targetwidth,
        min_shape_um=minsize,
        layer_num=layer,
        dark_is_solid=darkissolid,
        invert=invert,
        timestamps=sc_timestamps
    )


if __name__ == '__main__':
    main()
