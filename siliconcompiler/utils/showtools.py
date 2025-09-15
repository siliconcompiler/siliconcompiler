from shutil import which

from siliconcompiler.tool import ShowTaskSchema, ScreenshotTaskSchema

from siliconcompiler.tools.klayout.show import ShowTask as KlayoutShow
from siliconcompiler.tools.klayout.screenshot import ScreenshotTask as KlayoutScreenshot

from siliconcompiler.tools.openroad.show import ShowTask as OpenROADShow
from siliconcompiler.tools.openroad.screenshot import ScreenshotTask as OpenROADScreenshot

from siliconcompiler.tools.graphviz.show import ShowTask as GraphvizShow
from siliconcompiler.tools.graphviz.screenshot import ScreenshotTask as GraphvizScreenshot

from siliconcompiler.tools.vpr.show import ShowTask as VPRShow
from siliconcompiler.tools.vpr.screenshot import ScreenshotTask as VPRSScreenshot

from siliconcompiler.tools.gtkwave.show import ShowTask as GTKWaveShow
from siliconcompiler.tools.surfer.show import ShowTask as SurferShow


def showtasks():
    ShowTaskSchema.register_task(KlayoutShow)
    ShowTaskSchema.register_task(OpenROADShow)
    ShowTaskSchema.register_task(GraphvizShow)
    ShowTaskSchema.register_task(VPRShow)
    if which('surfer') is not None:
        ShowTaskSchema.register_task(SurferShow)
    else:
        ShowTaskSchema.register_task(GTKWaveShow)

    ScreenshotTaskSchema.register_task(KlayoutScreenshot)
    ScreenshotTaskSchema.register_task(OpenROADScreenshot)
    ScreenshotTaskSchema.register_task(GraphvizScreenshot)
    ScreenshotTaskSchema.register_task(VPRSScreenshot)
