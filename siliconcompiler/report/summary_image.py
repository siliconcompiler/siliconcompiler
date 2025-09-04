import os
import string

import os.path

from PIL import Image, ImageFont, ImageDraw

import siliconcompiler
from siliconcompiler.report.utils import _find_summary_image


def generate_summary_image(project, output_path, info):
    '''
    Takes a layout screenshot and generates a design summary image
    featuring a layout thumbnail and several metrics.
    '''

    img_path = _find_summary_image(project)
    if not img_path:
        return

    # Generate design
    WIDTH = 1024
    BORDER = 32
    LINE_SPACING = 8
    TEXT_INDENT = 16

    FONT_PATH = os.path.join(os.path.dirname(siliconcompiler.__file__),
                             'data', 'RobotoMono', 'RobotoMono-Regular.ttf')
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
    max_title_len = max([len(title) for title, _ in info])
    for title, value in info:
        line = f'{title:<{max_title_len}}: {value}'

        # shorten line till it fits
        cropped_line = line
        while True:
            line_width = font.getmask(cropped_line).getbbox()[2] + TEXT_INDENT
            if x + line_width < (WIDTH - BORDER):
                break
            cropped_line = cropped_line[:-1]

        if cropped_line != line:
            project.logger.warning(f'Cropped {line} to {cropped_line} to fit in design summary '
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
    project.logger.info(f'Generated summary image at {output_path}')


def _open_summary_image(image):
    Image.open(image).show()
