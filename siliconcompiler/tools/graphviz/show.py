import graphviz

import os.path

from PIL import Image

from siliconcompiler import sc_open
from siliconcompiler import ShowTask


class ShowTask(ShowTask):
    '''
    Show a graphviz dot file
    '''
    def tool(self):
        return "graphviz"

    def get_supported_show_extentions(self):
        return ["dot", "xdot"]

    def setup(self):
        super().setup()

        self.set_threads(1)

        if f"{self.design_topmodule}.dot" in self.get_files_from_input_nodes():
            self.add_input_file(ext="dot")
        elif f"{self.design_topmodule}.xdot" in self.get_files_from_input_nodes():
            self.add_input_file(ext="xdot")
        else:
            self.add_required_key("var", "showfilepath")

        self.add_output_file(ext="png")

    def _generate_screenshot(self):
        if os.path.exists(f'inputs/{self.design_topmodule}.dot'):
            file = f'inputs/{self.design_topmodule}.dot'
        elif os.path.exists(f'inputs/{self.design_topmodule}.xdot'):
            file = f'inputs/{self.design_topmodule}.xdot'
        else:
            file = self.find_files('var', 'showfilepath')

        with sc_open(file) as dot:
            dot_content = dot.read()

        try:
            dot = graphviz.Source(dot_content, format="png")
            dot.render(filename=f"outputs/{self.design_topmodule}", cleanup=True)
        except graphviz.ExecutableNotFound:
            return 1

        return 0

    def run(self):
        ret = self._generate_screenshot()
        if ret:
            return ret

        Image.open(f"outputs/{self.design_topmodule}.png").show()

        return 0
