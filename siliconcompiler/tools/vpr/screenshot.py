from siliconcompiler.tools.vpr.show import ShowTask
from siliconcompiler import ScreenshotTask


class ScreenshotTask(ScreenshotTask, ShowTask):
    '''
    Screenshot placed and/or routed designs
    '''
    def setup(self):
        super().setup()
        self.add_output_file(ext="png")

    def runtime_options(self):
        '''
        Screenshot placed and/or routed designs
        '''
        options = super().runtime_options()
        options = options[0:-2]  # remove disp

        showtype = self.get("var", "showtype")
        if showtype == 'route':
            screenshot_command_str = ("set_draw_block_text 0; " +
                                      "set_draw_block_outlines 0; " +
                                      "set_routing_util 1; " +
                                      f"save_graphics outputs/{self.design_topmodule}.png;")
        elif showtype == 'place':
            screenshot_command_str = ("set_draw_block_text 1; " +
                                      "set_draw_block_outlines 1; " +
                                      f"save_graphics outputs/{self.design_topmodule}.png;")
        else:
            raise ValueError(f"Incorrect file type {showtype}")

        options.append("--graphics_commands")
        options.append(screenshot_command_str)

        return options
