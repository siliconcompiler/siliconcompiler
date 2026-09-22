from shutil import which

from siliconcompiler import OpenTask, ShowTask, ScreenshotTask

from siliconcompiler.tools.klayout.show import ShowTask as KlayoutShow
from siliconcompiler.tools.klayout.screenshot import ScreenshotTask as KlayoutScreenshot

from siliconcompiler.tools.openroad.open import OpenTask as OpenROADOpen
from siliconcompiler.tools.openroad.open import Open3DBloxTask as OpenROADOpen3DBlox
from siliconcompiler.tools.openroad.show import ShowTask as OpenROADShow
from siliconcompiler.tools.openroad.show import Show3DBloxTask as OpenROADShow3DBlox
from siliconcompiler.tools.openroad.show import WebTask as OpenROADWeb
from siliconcompiler.tools.openroad.show import Show3DBloxWebTask as OpenROADShow3DBloxWeb
from siliconcompiler.tools.openroad.screenshot import ScreenshotTask as OpenROADScreenshot

from siliconcompiler.tools.yosys.open import OpenTask as YosysOpen
from siliconcompiler.tools.opensta.open import OpenTask as OpenSTAOpen

from siliconcompiler.tools.graphviz.show import ShowTask as GraphvizShow
from siliconcompiler.tools.graphviz.screenshot import ScreenshotTask as GraphvizScreenshot

from siliconcompiler.tools.vpr.show import ShowTask as VPRShow
from siliconcompiler.tools.vpr.screenshot import ScreenshotTask as VPRSScreenshot

from siliconcompiler.tools.gtkwave.show import ShowTask as GTKWaveShow
from siliconcompiler.tools.surfer.show import ShowTask as SurferShow


def showtasks():
    """
    Registers show and screenshot tasks in a stable order.

    Later registrations take precedence when multiple tools support the same
    extension, so this reads lowest priority first. The layout viewers are
    registered last, which puts them at the top of ``sc-show -list`` and ahead
    of the waveform and FPGA viewers on any tie in
    :meth:`~siliconcompiler.OpenTask.get_extension_map`. They share no
    extension with those tools, so this decides presentation and tie-breaks
    only -- nothing changes hands.
    """
    # Register Open tasks
    # All three of openroad, yosys and opensta read a vg. opensta is registered
    # last so it wins that extension; openroad still owns odb and def, and yosys
    # stays reachable through "-tool yosys".
    #
    # This order also breaks ties in get_extension_map(), but nothing here has
    # to be arranged to keep odb ahead of vg: openroad/open lists vg last of the
    # three formats it reads, and that is what demotes it.
    OpenTask.register_task(OpenROADOpen)
    OpenTask.register_task(OpenROADOpen3DBlox)
    OpenTask.register_task(YosysOpen)
    OpenTask.register_task(OpenSTAOpen)

    # Register Show tasks - graph and FPGA viewers first
    ShowTask.register_task(GraphvizShow)
    ShowTask.register_task(VPRShow)

    # Register VCD viewer - prefer surfer if available, otherwise fall back to gtkwave
    if which('surfer') is not None:
        ShowTask.register_task(GTKWaveShow)
        ShowTask.register_task(SurferShow)
    elif which('gtkwave') is not None:
        ShowTask.register_task(SurferShow)
        ShowTask.register_task(GTKWaveShow)
    else:
        ShowTask.register_task(GTKWaveShow)
        ShowTask.register_task(SurferShow)

    # Register the layout viewers last, so they lead. klayout stays ahead of
    # openroad within this group: def is the only extension they share, and
    # registering klayout first is what hands it to openroad.
    ShowTask.register_task(KlayoutShow)
    ShowTask.register_task(OpenROADWeb)
    ShowTask.register_task(OpenROADShow)
    ShowTask.register_task(OpenROADShow3DBloxWeb)
    ShowTask.register_task(OpenROADShow3DBlox)

    # Register Screenshot tasks - same order as Show tasks
    ScreenshotTask.register_task(GraphvizScreenshot)
    ScreenshotTask.register_task(VPRSScreenshot)
    ScreenshotTask.register_task(KlayoutScreenshot)
    ScreenshotTask.register_task(OpenROADScreenshot)
