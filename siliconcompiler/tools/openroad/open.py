import shutil
import os

import os.path


from siliconcompiler import OpenTask as BaseOpenTask
from siliconcompiler.tools.openroad._apr import APRTask, OpenROADSTAParameter
from siliconcompiler.utils.paths import workdir


class OpenTask(BaseOpenTask, APRTask, OpenROADSTAParameter):
    '''
    Open a design in openroad.

    Reuses the APR input handling so the same odb/def/vg/sdc selection logic
    (including ``enablehier`` linking and ``load_sdcs``) is applied. When a
    ``showfilepath`` is provided (e.g. via ``sc-show -open``) the file plus any
    sibling ``vg``/``sdc`` files from the source node are copied into ``inputs``
    at runtime.
    '''
    def __init__(self):
        super().__init__()

    def setup(self):
        super().setup()

        # Open mode produces no output artifacts
        self.unset("output")

        # If neither input-node files nor an explicit showfilepath are
        # available, require the user to supply a file.
        if not self.get("input") and not self.get("var", "showfilepath"):
            self.add_required_key("var", "showfilepath")

        self.set_script("sc_open.tcl")

        self.set("var", "showexit", False, clobber=False)

    def pre_process(self):
        super().pre_process()
        self._copy_show_files()

    def get_supported_task_extentions(self):
        return ["odb", "def", "vg"]

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

        if not (show_step and show_index):
            return

        job_root = self.project
        if show_job:
            try:
                job_root = job_root.history(show_job)
            except KeyError:
                pass

        src_outputs = os.path.join(workdir(job_root, step=show_step, index=show_index),
                                   "outputs")

        # Copy companion verilog netlist when linking a placed/routed def with -hier
        if show_type in ("def", "def.gz"):
            for vg_ext in ("vg.gz", "vg"):
                vg_file = os.path.join(src_outputs, f"{self.design_topmodule}.{vg_ext}")
                if os.path.exists(vg_file):
                    shutil.copy2(vg_file, f"inputs/{self.design_topmodule}.{vg_ext}")
                    break

        # Copy SDCs when load_sdcs is enabled: prefer per-mode files, otherwise
        # fall back to the generic <top>.sdc.
        if not self.get("var", "load_sdcs"):
            return

        modes = self._get_modes()
        mode_sdcs = [
            (mode, os.path.join(src_outputs, f"{self.design_topmodule}.{mode}.sdc"))
            for mode in modes
        ]
        if mode_sdcs and all(os.path.exists(p) for _, p in mode_sdcs):
            for mode, sdc_file in mode_sdcs:
                shutil.copy2(sdc_file, f"inputs/{self.design_topmodule}.{mode}.sdc")
            return

        sdc_file = os.path.join(src_outputs, f"{self.design_topmodule}.sdc")
        if os.path.exists(sdc_file):
            shutil.copy2(sdc_file, f"inputs/{self.design_topmodule}.sdc")

    def runtime_options(self):
        options = super().runtime_options()
        try:
            options.remove("-exit")
        except ValueError:
            pass
        return options
