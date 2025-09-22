from shutil import which

from siliconcompiler import ShowTask, ScreenshotTask

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
    ShowTask.register_task(KlayoutShow)
    ShowTask.register_task(OpenROADShow)
    ShowTask.register_task(GraphvizShow)
    ShowTask.register_task(VPRShow)
    if which('surfer') is not None:
        ShowTask.register_task(SurferShow)
    else:
        ShowTask.register_task(GTKWaveShow)

    ScreenshotTask.register_task(KlayoutScreenshot)
    ScreenshotTask.register_task(OpenROADScreenshot)
    ScreenshotTask.register_task(GraphvizScreenshot)
    ScreenshotTask.register_task(VPRSScreenshot)
