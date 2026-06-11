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

import os

import psutil

from typing import Dict

from siliconcompiler import Task


class ImageMagickTask(Task):
    '''
    Base class for ImageMagick based tasks.

    Provides the common version handling and, more importantly, generates a
    private ImageMagick ``policy.xml`` whose pixel-cache resource ceilings are
    scaled to the host running the task.

    This is necessary because ImageMagick's command-line ``-limit`` options (and
    the ``MAGICK_*_LIMIT`` environment variables) can only *lower* a resource
    below the ceiling defined in the system ``policy.xml`` -- they can never
    raise it. A stock ``policy.xml`` typically caps ``area`` at 256MP, which a
    large image easily exceeds, failing with "cache resources exhausted". By
    writing our own ``policy.xml`` and pointing ``MAGICK_CONFIGURE_PATH`` at it,
    we fully replace those ceilings with host-appropriate values.
    '''

    # Input image formats recognized from upstream nodes, in preference order.
    # PNG is first so it is also the assumed default when none can be detected.
    SUPPORTED_INPUT_FORMATS = (
        "png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff", "ppm", "svg",
    )

    def tool(self):
        return "montage"

    def parse_version(self, stdout):
        first_line = stdout.splitlines()[0]
        return first_line.split(' ')[2]

    def setup(self):
        super().setup()

        self.add_version(">=6.9.0")

        # ImageMagick montage/convert run single-threaded here; declare that to
        # the scheduler so it does not reserve unused cores for these tasks.
        self.set_threads(1)

    def get_runtime_environmental_variables(self, include_path: bool = True) -> Dict[str, str]:
        envvars = super().get_runtime_environmental_variables(include_path=include_path)

        # Direct ImageMagick at the private policy.xml written by pre_process() so
        # the host-sized resource ceilings replace the restrictive system policy.
        envvars["MAGICK_CONFIGURE_PATH"] = self.nodeworkdir

        return envvars

    def _resource_limits(self):
        '''
        Compute ImageMagick pixel-cache resource limits scaled to this host,
        balancing "big enough to process the image" against "small enough not to
        exhaust the host".

        Returns:
            list[tuple[str, str]]: (resource name, ImageMagick value) pairs.
        '''
        total_mem = psutil.virtual_memory().total
        free_disk = psutil.disk_usage(self.nodeworkdir).free

        # Cap heap usage at half of RAM so processing cannot OOM the machine, and
        # let the memory-mapped/disk-backed pixel cache grow into the scratch
        # space (leaving headroom for the inputs and the written output).
        mem_budget = int(total_mem * 0.5)
        disk_budget = int(free_disk * 0.8)

        # ImageMagick backs a pixel cache with a single tier (heap -> mmap ->
        # disk), so the largest tier (disk) sets the maximum processable image.
        # Size "area" to that budget assuming a worst-case Q16 RGBA pixel
        # (8 bytes/pixel); a Q8 build simply gets extra headroom.
        bytes_per_pixel = 8
        area = disk_budget // bytes_per_pixel

        def gib(num_bytes):
            return f"{max(1, num_bytes // 1024 ** 3)}GiB"

        def mp(num_pixels):
            return f"{max(1, num_pixels // 1000 ** 2)}MP"

        return [
            ("memory", gib(mem_budget)),
            ("map", gib(disk_budget)),
            ("disk", gib(disk_budget)),
            ("width", "128KP"),
            ("height", "128KP"),
            ("area", mp(area)),
        ]

    def pre_process(self):
        super().pre_process()

        # Write a private policy.xml that raises ImageMagick's resource ceilings
        # to host-appropriate values; MAGICK_CONFIGURE_PATH points ImageMagick
        # here, fully overriding the restrictive system policy.xml.
        policy = ['<policymap>']
        for name, value in self._resource_limits():
            policy.append(f'  <policy domain="resource" name="{name}" value="{value}"/>')
        policy.append('</policymap>')
        policy.append('')

        with open(os.path.join(self.nodeworkdir, "policy.xml"), "w") as f:
            f.write("\n".join(policy))
