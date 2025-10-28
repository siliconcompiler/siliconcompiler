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

        if f"{self.design_topmodule}.gds.gz" in self.get_files_from_input_nodes():
            self.add_input_file(ext="gds.gz")
        elif f"{self.design_topmodule}.gds" in self.get_files_from_input_nodes():
            self.add_input_file(ext="gds")
        elif f"{self.design_topmodule}.oas.gz" in self.get_files_from_input_nodes():
            self.add_input_file(ext="oas.gz")
        elif f"{self.design_topmodule}.oas" in self.get_files_from_input_nodes():
            self.add_input_file(ext="oas")
        else:
            self.add_required_key("var", "showfilepath")

        self.add_commandline_option(["-nc", "-rm"], clobber=True)

    def get_supported_show_extentions(self):
        return ["def", "lef", "gds", "oas", "lyrdb", "ascii"]

    def pre_process(self):
        super().pre_process()

        if self.get("var", "showfilepath"):
            rel_path = os.path.dirname(self.get("var", "showfilepath"))
            for ext in ('lyt', 'lyp'):
                ext_file = os.path.join(rel_path, f'{self.design_topmodule}.{ext}')
                if ext_file and os.path.exists(ext_file):
                    shutil.copy2(ext_file, f"inputs/{self.design_topmodule}.{ext}")
