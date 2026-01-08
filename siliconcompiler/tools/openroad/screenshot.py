from typing import Optional, Union

from siliconcompiler import ScreenshotTask
from siliconcompiler.tools.openroad.show import ShowTask


class ScreenshotTask(ScreenshotTask, ShowTask):
    '''
    Generate a PNG file from a layout file
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("show_vertical_resolution", "int",
                           "Vertical resolution of the screenshot image",
                           defvalue=1024)
        self.add_parameter("include_report_images", "bool",
                           "true/false, include the images in reports/", defvalue=False)

    def set_openroad_verticalresolution(self, value: int,
                                        step: Optional[str] = None,
                                        index: Optional[Union[int, str]] = None):
        """
        Set the vertical resolution for OpenROAD screenshots.

        Args:
            value (int): The vertical resolution in pixels.
            step (Optional[str]): The step in the flow where this setting applies.
            index (Optional[Union[int, str]]): The index for multiple runs or configurations.
        """
        self.set("var", "show_vertical_resolution", value, step=step, index=index)

    def set_openroad_includereportimages(self, value: bool,
                                         step: Optional[str] = None,
                                         index: Optional[Union[int, str]] = None):
        """
        Set whether to include report images in the output.

        Args:
            value (bool): Whether to include report images.
            step (Optional[str]): The step in the flow where this setting applies.
            index (Optional[Union[int, str]]): The index for multiple runs or configurations.
        """
        self.set("var", "include_report_images", value, step=step, index=index)

    def setup(self):
        super().setup()

        self.add_output_file(ext="png", clobber=True)

        self.set_script("sc_show.tcl")

        self.set("var", "showexit", True)

        # No need for the GUI to open
        self.set_environmentalvariable("QT_QPA_PLATFORM", "offscreen")

        self._set_reports([
            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'ir_drop',
            'clock_placement',
            'clock_trees',
            'optimization_placement'
        ])

        self.add_required_key("var", "show_vertical_resolution")
        self.add_required_key("var", "include_report_images")
