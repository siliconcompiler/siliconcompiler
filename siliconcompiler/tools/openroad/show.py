import shutil
import os

import os.path


from siliconcompiler import ShowTask
from siliconcompiler.tools.openroad._apr import APRTask, OpenROADSTAParameter
from siliconcompiler.utils.paths import workdir


class ShowTask(ShowTask, APRTask, OpenROADSTAParameter):
    '''
    Show a design in openroad
    '''
    def __init__(self):
        super().__init__()

    def setup(self):
        super().setup()

        self.unset("input")
        self.unset("output")

        # Add input file requirements
        if f"{self.design_topmodule}.odb" in self.get_files_from_input_nodes():
            self.add_input_file(ext="odb")
        elif f"{self.design_topmodule}.def" in self.get_files_from_input_nodes():
            self.add_input_file(ext="def")
        else:
            self.add_required_key("var", "showfilepath")
        if f"{self.design_topmodule}.sdc" in self.get_files_from_input_nodes():
            self.add_input_file(ext="sdc")

        self.set_script("sc_show.tcl")

        self.set("var", "showexit", False, clobber=False)

    def pre_process(self):
        super().pre_process()
        self._copy_show_files()

    def get_supported_show_extentions(self):
        return ["odb", "def"]

    def _copy_show_files(self):
        if not self.get("var", "showfilepath"):
            return

        show_file = self.find_files('var', 'showfilepath')
        show_type = self.get('var', 'showfiletype')

        show_job, show_step, show_index = (None, None, None)
        show_node = self.get("var", "shownode")
        if show_node:
            show_job, show_step, show_index = show_node

        # copy source in to keep sc_apr.tcl simple
        dst_file = f"inputs/{self.design_topmodule}.{show_type}"
        shutil.copy2(show_file, dst_file)

        job_root = self.project
        if show_job:
            try:
                job_root = job_root.history(show_job)
            except KeyError:
                pass

        if show_step and show_index:
            sdc_file = os.path.join(workdir(job_root, step=show_step, index=show_index),
                                    "output",
                                    f"{self.design_topmodule}.sdc")
            if sdc_file and os.path.exists(sdc_file):
                shutil.copy2(sdc_file, f"inputs/{self.design_topmodule}.sdc")

    def runtime_options(self):
        options = super().runtime_options()
        try:
            options.remove("-exit")
        except KeyError:
            pass
        options.append("-gui")
        return options
