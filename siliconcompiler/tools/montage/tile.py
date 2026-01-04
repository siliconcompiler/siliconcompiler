from typing import Optional, Union
from siliconcompiler import Task, TaskSkip


class TileTask(Task):
    '''
    Tiles input images into a single output image.

    Notes:
        Need to make ensure that /etc/ImageMagick-6/policy.xml
        <policy domain="resource" name="memory" value="8GiB"/>
        <policy domain="resource" name="map" value="8GiB"/>
        <policy domain="resource" name="width" value="32KP"/>
        <policy domain="resource" name="height" value="32KP"/>
        <policy domain="resource" name="area" value="1GP"/>
        <policy domain="resource" name="disk" value="8GiB"/>
        This ensures there are enough resources available to generate
        the final image.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("bins", "(int,int)", "Number of bins along the (x, y)-axis",
                           defvalue=(2, 2))

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

    def tool(self):
        return "montage"

    def task(self):
        return "tile"

    def parse_version(self, stdout):
        first_line = stdout.splitlines()[0]
        return first_line.split(' ')[2]

    def setup(self):
        super().setup()

        self.set_exe("montage", vswitch="-version")
        self.add_version(">=6.9.0")

        xbins, ybins = self.get("var", "bins")

        if f"{self.design_topmodule}.png" in self.get_files_from_input_nodes():
            raise TaskSkip("Input provides a single image; skipping tiling.")

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
