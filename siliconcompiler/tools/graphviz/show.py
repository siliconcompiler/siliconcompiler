from PIL import Image
from siliconcompiler.tools.graphviz import screenshot


def setup(chip):
    '''
    Show a graphviz dot file
    '''

    screenshot.setup(chip)


def run(chip):
    screenshot_ret = screenshot.run(chip)
    if screenshot_ret != 0:
        return screenshot_ret

    Image.open(f"outputs/{chip.top()}.png").show()

    return 0
