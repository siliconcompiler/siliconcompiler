from siliconcompiler import ScreenshotTaskSchema
from siliconcompiler.tools.graphviz.show import ShowTask


class ScreenshotTask(ShowTask, ScreenshotTaskSchema):
    '''
    Generate a screenshot of a dot file
    '''
    def run(self):
        return self._generate_screenshot()
