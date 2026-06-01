import sys

from typing import Optional
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
    timestamps: bool = True,
    outline_layer: Optional[Tuple[int, int]] = None
):
    """
    Converts a PNG image to a GDSII layout using KLayout's native API.

    :param image_path: Path to the input PNG image.
    :param output_gds: Path to the output GDS file.
    :param target_width_um: The desired total width of the image in the GDS (in microns).
    :param min_shape_um: The minimum allowable shape size (resolution limit) in microns.
    :param layer_num: The GDS layer number to draw the shapes on.
    :param dark_is_solid: Base logic - If True, dark pixels become GDS shapes.
    :param invert: Explicitly inverts the final polarity of the image.
    """
    from PIL import Image as PILImage  # noqa E402
    from klayout_utils import get_write_options  # noqa E402

    # 1. Load image with PIL — handles RGBA correctly (pya.Image drops the alpha channel)
    print(f"Loading {image_path}...")

    pil_img = PILImage.open(image_path)

    orig_w, orig_h = pil_img.size
    if orig_w == 0 or orig_h == 0:
        raise ValueError("Image is empty. Ensure it's a valid image.")

    # Convert to grayscale; composite RGBA over white so transparent→light, opaque→dark.
    if pil_img.mode == 'RGBA':
        _, _, _, alpha = pil_img.split()
        gray_img = PILImage.new('L', pil_img.size, 255)
        gray_img.paste(pil_img.convert('L'), mask=alpha)
    else:
        gray_img = pil_img.convert('L')

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

    gray_pixels = gray_img.load()
    threshold = 128  # midpoint of [0, 255]

    print("Generating GDS shapes...")
    # 4. Iterate through the target grid and sample the image
    for y_new in range(new_h):
        # Nearest-neighbor mapping back to original Y coordinate
        y_orig = int(y_new * orig_h / new_h)

        for x_new in range(new_w):
            # Nearest-neighbor mapping back to original X coordinate
            x_orig = int(x_new * orig_w / new_w)

            val = gray_pixels[x_orig, y_orig]

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

    print("Boolean Kissing-Corner Resolution...")

    pass_count = 1
    while True:
        # Generate shifted regions to detect neighborhood states
        r_up = region.moved(pya.Vector(0, pixel_size_dbu))
        r_right = region.moved(pya.Vector(pixel_size_dbu, 0))
        r_left = region.moved(pya.Vector(-pixel_size_dbu, 0))
        r_up_right = region.moved(pya.Vector(pixel_size_dbu, pixel_size_dbu))
        r_up_left = region.moved(pya.Vector(-pixel_size_dbu, pixel_size_dbu))

        # --- KISS TYPE 1: (\) Diagonal ---
        bridges_1 = (r_right & r_up) - region - r_up_right

        # --- KISS TYPE 2: (/) Diagonal ---
        bridges_2 = (r_left & r_up) - region - r_up_left

        # Check for fixed point: if no new bridges are needed, terminate the loop
        if bridges_1.is_empty() and bridges_2.is_empty():
            print(f"Kissing-corner resolution converged after {pass_count - 1} additions.")
            break

        # Add the perfectly sized pixel bridges back to the main region
        region = region + bridges_1 + bridges_2

        # Merge to dissolve the bridges into the main polygons before the next pass
        region.merge()
        pass_count += 1

    # 5. Insert the optimized region into the cell and save
    top_cell.shapes(layer).insert(region)

    if outline_layer is not None:
        ol = layout.layer(outline_layer[0], outline_layer[1])
        outline_box = pya.Box(0, 0, new_w * pixel_size_dbu, new_h * pixel_size_dbu)
        top_cell.shapes(ol).insert(outline_box)

    layout.write(output_gds, get_write_options(output_gds, timestamps))
    print(f"GDS saved to {output_gds}")


def main():
    """
    Main function for converting an image to gds
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
    sc_step: str = schema.get('arg', 'step')
    sc_index: str = schema.get('arg', 'index')

    design_name = schema.get('option', 'design')
    fileset: str = schema.get("option", "fileset")[0]
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

    outline_layer = None
    if schema.valid('tool', 'klayout', 'task', 'image2stream', 'var', 'outline_layer') and \
            schema.get('tool', 'klayout', 'task', 'image2stream', 'var', 'outline_layer',
                       step=sc_step, index=sc_index):
        outline_layer = schema.get('tool', 'klayout', 'task', 'image2stream', 'var',
                                   'outline_layer', step=sc_step, index=sc_index)

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
        timestamps=sc_timestamps,
        outline_layer=outline_layer
    )


if __name__ == '__main__':
    main()
