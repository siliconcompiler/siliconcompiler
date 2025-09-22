from siliconcompiler import ScreenshotTask
from siliconcompiler.tools.graphviz.show import ShowTask


class ScreenshotTask(ShowTask, ScreenshotTask):
    '''
    Generate a screenshot of a dot file
    '''
    def run(self):
        return self._generate_screenshot()
