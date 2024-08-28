from siliconcompiler import Chip, Flow

from siliconcompiler.tools.klayout import operations
from siliconcompiler.tools.klayout import screenshot
from siliconcompiler.tools.montage import tile


def make_docs(chip):
    chip.set('input', 'layout', 'gds', 'test')
    chip.set('tool', 'klayout', 'task', 'screenshot', 'var', 'xbins', 2)
    chip.set('tool', 'klayout', 'task', 'screenshot', 'var', 'ybins', 2)
    chip.set('tool', 'montage', 'task', 'tile', 'var', 'xbins', 2)
    chip.set('tool', 'montage', 'task', 'tile', 'var', 'ybins', 2)
    return setup()


def setup(flowname='screenshotflow'):
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

    flow = Flow(flowname)

    prevstep = None
    for step, task in pipe:
        flow.node(flowname, step, task)
        if prevstep:
            flow.edge(flowname, prevstep, step)
        prevstep = step

    return flow


##################################################
if __name__ == "__main__":
    chip = Chip('design')
    flow = make_docs(chip)
    chip.use(flow)
    chip.write_flowgraph(f"{flow.top()}.png", flow=flow.top())
