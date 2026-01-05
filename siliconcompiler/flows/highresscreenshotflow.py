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
    '''
    def __init__(self, name: str = "screenshotflow", add_prepare: bool = True):
        super().__init__(name)

        self.node('import', importfiles.ImportFilesTask())
        if add_prepare:
            self.node('prepare', operations.OperationsTask())
        self.node('screenshot', screenshot.ScreenshotTask())
        self.node('merge', tile.TileTask())

        if add_prepare:
            self.edge('import', 'prepare')
            self.edge('prepare', 'screenshot')
        else:
            self.edge('import', 'screenshot')
        self.edge('screenshot', 'merge')

    @classmethod
    def make_docs(cls):
        return [
            cls(add_prepare=True),
            cls(add_prepare=False)
        ]
