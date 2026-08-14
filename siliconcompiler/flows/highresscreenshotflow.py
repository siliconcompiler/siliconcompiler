from siliconcompiler import Flowgraph

from siliconcompiler.tools.builtin import importfiles
from siliconcompiler.tools.klayout import operations
from siliconcompiler.tools.klayout import screenshot
from siliconcompiler.tools.montage import tile


class HighResScreenshotFlow(Flowgraph):
    '''A high resolution screenshot flow.

    This flow is designed to generate a high resolution design image from a GDS
    or OAS file by preparing the layout, taking tiled screenshots, and merging
    them into a single image.

    The ``prepare`` node removes itself from the flow unless
    :class:`~siliconcompiler.tools.klayout.operations.OperationsTask` has been
    given operations to perform, so a layout that needs no preparation costs
    nothing.
    '''

    def __init__(self, name: str = "screenshotflow"):
        super().__init__(name)

        self.node('import', importfiles.ImportFilesTask())
        self.node('prepare', operations.OperationsTask())
        self.node('screenshot', screenshot.ScreenshotTask())
        self.node('merge', tile.TileTask())

        self.edge('import', 'prepare')
        self.edge('prepare', 'screenshot')
        self.edge('screenshot', 'merge')
