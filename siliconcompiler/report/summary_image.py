import os
import string
from PIL import Image, ImageFont, ImageDraw

from siliconcompiler import units
from siliconcompiler.report.utils import _find_summary_image, _find_summary_metrics


def _generate_summary_image(chip, output_path):
    '''
    Takes a layout screenshot and generates a design summary image
    featuring a layout thumbnail and several metrics.
    '''

    img_path = _find_summary_image(chip)
    if not img_path:
        return

    # Extract metrics for display
    metrics = {
        'Chip': chip.design,
    }

    pdk = chip.get('option', 'pdk')
    if pdk:
        metrics['Node'] = pdk
    else:
        fpga_partname = chip.get('fpga', 'partname')
        if fpga_partname:
            metrics['FPGA'] = fpga_partname

    def format_area(value, unit):
        prefix = units.get_si_prefix(unit)
        mm_area = units.convert(value, from_unit=prefix, to_unit='mm^2')
        if mm_area < 10:
            return units.format_si(value, 'um') + 'um^2'
        else:
            return units.format_si(mm_area, 'mm') + 'mm^2'

    def format_freq(value, unit):
        value = units.convert(value, from_unit=unit)
        return units.format_si(value, 'Hz') + 'Hz'

    metrics.update(_find_summary_metrics(chip, {
        'Area': ('totalarea', format_area),
        'LUTs': ('luts', None),
        'Fmax': ('fmax', format_freq)}))

    # Generate design

    WIDTH = 1024
    BORDER = 32
    LINE_SPACING = 8
    TEXT_INDENT = 16

    FONT_PATH = os.path.join(chip.scroot, 'data', 'RobotoMono', 'RobotoMono-Regular.ttf')
    FONT_SIZE = 40

    # matches dark gray background color configured in klayout_show.py
    BG_COLOR = (33, 33, 33)

    # near-white
    TEXT_COLOR = (224, 224, 224)

    original_layout = Image.open(img_path)
    orig_width, orig_height = original_layout.size

    aspect_ratio = orig_height / orig_width

    # inset by border left and right
    thumbnail_width = WIDTH - 2 * BORDER
    thumbnail_height = round(thumbnail_width * aspect_ratio)
    layout_thumbnail = original_layout.resize((thumbnail_width, thumbnail_height))

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Get max height of any ASCII character in font, so we can consistently space each line
    _, descent = font.getmetrics()
    _, bb_top, _, bb_bottom = font.getmask(string.printable).getbbox()
    line_height = (bb_bottom - bb_top) + descent

    text = []
    x = BORDER + TEXT_INDENT
    y = thumbnail_height + 2 * BORDER
    for metric, value in metrics.items():
        line = f'{metric}: {value}'

        # shorten line till it fits
        cropped_line = line
        while True:
            line_width = font.getmask(cropped_line).getbbox()[2] + TEXT_INDENT
            if x + line_width < (WIDTH - BORDER):
                break
            cropped_line = cropped_line[:-1]

        if cropped_line != line:
            chip.logger.warning(f'Cropped {line} to {cropped_line} to fit in design summary '
                                'image')

        # Stash line to write and coords to write it at
        text.append(((x, y), cropped_line))

        y += line_height + LINE_SPACING

    design_summary = Image.new('RGB', (WIDTH, y + BORDER), color=BG_COLOR)
    design_summary.paste(layout_thumbnail, (BORDER, BORDER))

    draw = ImageDraw.Draw(design_summary)
    for coords, line in text:
        draw.text(coords, line, TEXT_COLOR, font=font)

    design_summary.save(output_path)
    chip.logger.info(f'Generated summary image at {output_path}')


def _open_summary_image(image):
    Image.open(image).show()
