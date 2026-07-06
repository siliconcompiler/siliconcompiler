import re

from typing import Optional, Tuple, Union

from siliconcompiler import TaskSkip
from siliconcompiler.tools.montage import ImageMagickTask


class TileTask(ImageMagickTask):
    '''
    Tiles input images into a single output image.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("bins", "(int<1->>,int<1->>)",
                           "Number of bins along the (x, y)-axis. If left unset, the grid size is "
                           "auto-detected from the incoming tile images.")

    def set_montage_bins(self, xbins: int, ybins: int,
                         step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Set the number of bins for Montage tiling.

        Args:
            xbins (int): Number of bins along the x-axis.
            ybins (int): Number of bins along the y-axis.
            step (Optional[str]): Flow step to set the parameter for. Defaults to None.
            index (Optional[Union[str, int]]): Index to set the parameter for. Defaults to None.
        """
        self.set("var", "bins", (xbins, ybins), step=step, index=index)

    def _detect_montage_bins(self) -> Optional[Tuple[int, int]]:
        """
        Determine the tiling grid size from the incoming tile images, whose
        names follow the ``<topmodule>_X<x>_Y<y>.png`` convention.

        Returns:
            Optional[Tuple[int, int]]: ``(xbins, ybins)`` if tile images are
            found among the input files, otherwise ``None``.
        """
        pattern = re.compile(rf"^{re.escape(self.design_topmodule)}_X(\d+)_Y(\d+)\.png$")

        xvals = set()
        yvals = set()
        for file in self.get_files_from_input_nodes():
            match = pattern.match(file)
            if match:
                xvals.add(int(match.group(1)))
                yvals.add(int(match.group(2)))

        if not xvals or not yvals:
            return None

        return (max(xvals) + 1, max(yvals) + 1)

    def task(self):
        return "tile"

    def setup(self):
        self.set_exe("montage", vswitch="-version")

        super().setup()

        if f"{self.design_topmodule}.png" in self.get_files_from_input_nodes():
            raise TaskSkip("Input provides a single image; skipping tiling.")

        self.add_required_key("var", "bins")
        # Auto-detect the grid size from the incoming files when the user has
        # not explicitly set it.
        if self.get("var", "bins") is None:
            bins = self._detect_montage_bins()
            if bins is None:
                return
            self.set_montage_bins(*bins)

        xbins, ybins = self.get("var", "bins")
        for x in range(xbins):
            for y in range(ybins):
                self.add_input_file(f'{self.design_topmodule}_X{x}_Y{y}.png')

        self.add_output_file(ext="png")

    def runtime_options(self):
        options = super().runtime_options()

        xbins, ybins = self.get("var", "bins")
        for y in range(ybins):
            for x in range(xbins):
                options.append(f'inputs/{self.design_topmodule}_X{x}_Y{y}.png')

        options.append('-tile')
        options.append(f'{xbins}x{ybins}')
        options.append('-geometry')
        options.append('+0+0')
        options.append(f'outputs/{self.design_topmodule}.png')
        return options
