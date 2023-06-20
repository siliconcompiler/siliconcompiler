
'''
ImageMagick® is a free and open-source software suite for displaying, converting, and editing raster
image and vector image files.
It can read and write over 200 image file formats, and can support a wide range of image
manipulation operations, such as resizing, cropping, and color correction.
Use the montage program to create a composite image by combining several separate images.
The images are tiled on the composite image optionally adorned with a border, frame, image name,
and more

Documentation: https://imagemagick.org/

Sources: https://github.com/ImageMagick/ImageMagick

Installation: https://github.com/ImageMagick/ImageMagick
'''


def setup(chip):
    exe = 'montage'

    chip.set('tool', 'montage', 'exe', exe)
    chip.set('tool', 'montage', 'vswitch', '-version')
    chip.set('tool', 'montage', 'version', '>=6.9.0')


def parse_version(stdout):
    first_line = stdout.splitlines()[0]

    return first_line.split(' ')[2]
