from typing import Optional, Union

from siliconcompiler.tools.montage import ImageMagickTask


class ConvertTask(ImageMagickTask):
    '''
    Downsamples an input image and writes it out as a PNG or JPG.

    Useful for producing a lightweight, shareable preview from a large merged
    screenshot. The input image format is auto-detected from the file provided
    upstream (PNG is assumed when it cannot be determined); the output is
    ``<design>.<format>`` scaled by the configured resize geometry.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("resize", "str",
                           "ImageMagick resize geometry applied to the image, e.g. '50%' or "
                           "'2048x2048' (aspect ratio is preserved). Leave empty to only convert "
                           "the format without resizing.")
        self.add_parameter("format", f"<{','.join(ImageMagickTask.SUPPORTED_INPUT_FORMATS)}>",
                           "Output image format", defvalue="png")
        self.add_parameter("quality", "int", "Output image quality (1-100)")

    def set_convert_resize(self, resize: str,
                           step: Optional[str] = None,
                           index: Optional[Union[str, int]] = None):
        """
        Set the resize geometry applied to the image.

        Args:
            resize (str): ImageMagick resize geometry (e.g. '50%' or '2048x2048').
            step (Optional[str]): Flow step to set the parameter for. Defaults to None.
            index (Optional[Union[str, int]]): Index to set the parameter for. Defaults to None.
        """
        self.set("var", "resize", resize, step=step, index=index)

    def set_convert_format(self, image_format: str,
                           step: Optional[str] = None,
                           index: Optional[Union[str, int]] = None):
        """
        Set the output image format.

        Args:
            image_format (str): Output format, one of 'png', 'jpg', 'jpeg', 'webp',
                'gif', 'bmp', 'tif', 'tiff', 'ppm', 'svg'.
            step (Optional[str]): Flow step to set the parameter for. Defaults to None.
            index (Optional[Union[str, int]]): Index to set the parameter for. Defaults to None.
        """
        self.set("var", "format", image_format, step=step, index=index)

    def set_convert_quality(self, quality: int,
                            step: Optional[str] = None,
                            index: Optional[Union[str, int]] = None):
        """
        Set the output image quality.

        Args:
            quality (int): Output image quality (1-100).
            step (Optional[str]): Flow step to set the parameter for. Defaults to None.
            index (Optional[Union[str, int]]): Index to set the parameter for. Defaults to None.
        """
        self.set("var", "quality", quality, step=step, index=index)

    def task(self):
        return "convert"

    def _input_image(self):
        """
        Determine the input image filename, auto-detecting its format from the
        files provided by upstream nodes.

        Returns:
            str: The input filename (e.g. ``<design>.png``). Falls back to PNG
            when no supported image is found among the input files.
        """
        available = self.get_files_from_input_nodes()
        for ext in ImageMagickTask.SUPPORTED_INPUT_FORMATS:
            candidate = f'{self.design_topmodule}.{ext}'
            if candidate in available:
                return candidate

        return f'{self.design_topmodule}.{ImageMagickTask.SUPPORTED_INPUT_FORMATS[0]}'

    def setup(self):
        self.set_exe("convert", vswitch="-version")

        super().setup()

        self.add_required_key("var", "format")
        if self.get("var", "quality"):
            self.add_required_key("var", "quality")
        if self.get("var", "resize"):
            self.add_required_key("var", "resize")

        self.add_input_file(self._input_image())
        self.add_output_file(ext=self.get("var", "format"))

    def runtime_options(self):
        options = super().runtime_options()

        image_format = self.get("var", "format")

        options.append(f'inputs/{self._input_image()}')

        resize = self.get("var", "resize")
        if resize:
            self.add_required_key("var", "resize")
            options.append('-resize')
            options.append(resize)

        quality = self.get("var", "quality")
        if quality:
            options.append('-quality')
            options.append(str(quality))

        options.append(f'outputs/{self.design_topmodule}.{image_format}')
        return options
