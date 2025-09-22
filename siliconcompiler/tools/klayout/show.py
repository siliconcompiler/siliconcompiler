import shutil

import os.path

from siliconcompiler import ShowTask
from siliconcompiler.tools.klayout import KLayoutTask


class ShowTask(ShowTask, KLayoutTask):
    '''
    Show a layout in kLayout
    '''
    def setup(self):
        super().setup()

        self.set_script("klayout_show.py")

        self.add_commandline_option(["-nc", "-rm"], clobber=True)

    def get_supported_show_extentions(self):
        return ["def", "lef", "gds", "oas", "lyrdb", "ascii"]

    def pre_process(self):
        super().pre_process()

        rel_path = os.path.dirname(self.get("var", "showfilepath"))
        for ext in ('lyt', 'lyp'):
            ext_file = os.path.join(rel_path, f'{self.design_topmodule}.{ext}')
            if ext_file and os.path.exists(ext_file):
                shutil.copy2(ext_file, f"inputs/{self.design_topmodule}.{ext}")
