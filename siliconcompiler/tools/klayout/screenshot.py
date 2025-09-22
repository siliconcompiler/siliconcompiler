from siliconcompiler import ScreenshotTask, Task
from siliconcompiler.tools.klayout.show import ShowTask


class ScreenshotParams(Task):
    '''
    Generate a PNG file from a layout file
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("show_resolution", "(int,int)",
                           "Horizontal and vertical resolution in pixels",
                           defvalue=(4096, 4096), unit="px")
        self.add_parameter("show_bins", "(int,int)",
                           "If greater than 1, splits the image into multiple segments along "
                           "x-axis and y-axis", defvalue=(1, 1))
        self.add_parameter("show_margin", "float",
                           "Margin around design in microns", defvalue=10, unit="um")
        self.add_parameter("show_linewidth", "int",
                           "Width of lines in detailed screenshots", defvalue=0, unit="px")
        self.add_parameter("show_oversampling", "int",
                           "Image oversampling used in detailed screenshots'", defvalue=2)

    def setup(self):
        super().setup()

        self.add_required_key("var", "show_resolution")
        self.add_required_key("var", "show_bins")
        self.add_required_key("var", "show_margin")
        self.add_required_key("var", "show_linewidth")
        self.add_required_key("var", "show_oversampling")

        if self.get("var", "show_bins") == (1, 1):
            self.add_output_file(ext="png")
        else:
            xbins, ybins = self.get("var", "show_bins")
            for x in range(xbins):
                for y in range(ybins):
                    self.add_output_file(f"{self.design_topmodule}_X{x}_Y{y}.png")


class ScreenshotTask(ShowTask, ScreenshotTask, ScreenshotParams):
    def setup(self):
        super().setup()

        self.add_commandline_option(['-nc', '-z', '-rm'], clobber=True)
