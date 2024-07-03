from siliconcompiler import Flow

from siliconcompiler.tools.klayout import operations
from siliconcompiler.tools.klayout import screenshot
from siliconcompiler.tools.montage import tile


def setup(chip, flowname='screenshotflow'):
    '''
    Flow to generate a high resolution design image from a GDS or OAS file.

    The 'screenshotflow' includes the stages below.

    * **prepare**: Prepare the stream file, such as flattening design, removing layers, and merging shapes
    * **screenshot**: Generate a set of screenshots tiled across the design
    * **merge**: Merge tiled images into a single image
    '''  # noqa E501

    pipe = [
        ('prepare', operations),
        ('screenshot', screenshot),
        ('merge', tile)
    ]

    flow = Flow(chip, flowname)

    prevstep = None
    for step, task in pipe:
        flow.node(flowname, step, task)
        if prevstep:
            flow.edge(flowname, prevstep, step)
        prevstep = step

    return flow
