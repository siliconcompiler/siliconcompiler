import shutil

from typing import List

from siliconcompiler import OpenTask as BaseOpenTask
from siliconcompiler.tools.yosys.syn_asic import _ASICTask


class OpenTask(BaseOpenTask, _ASICTask):
    '''
    Open a gate-level netlist in an interactive yosys shell.

    Reuses the ASIC liberty handling, so the same per-corner liberty files
    synthesis would have used are prepared and read, then reads the netlist and
    stops: no synthesis, no techmapping, no outputs. The design is elaborated
    against the standard cell library and yosys is left at its shell.

    When a ``showfilepath`` is provided (e.g. via ``sc-show -open``) it is copied
    into ``inputs`` at runtime.
    '''
    def __init__(self):
        super().__init__()

    def setup(self):
        super().setup()

        # An interactive session produces no output artifacts
        self.unset("output")

        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        elif not self.has_show_filepath():
            # Neither a previous node nor sc-show supplied a netlist, and unlike
            # synthesis this task has no RTL path to fall back on.
            self.add_required_key("var", "showfilepath")

        self.set_script("sc_open.tcl")

        self.set("var", "showexit", False, clobber=False)

    def get_supported_task_extentions(self) -> List[str]:
        return ["vg"]

    def runtime_options(self):
        options = super().runtime_options()

        # -C (enter the shell after the script) is added by YosysTask.setup,
        # because OpenTask.has_breakpoint() is unconditionally true. showexit has
        # to be answered by removing it again: once -C is on, a Tcl `exit` at the
        # end of sc_open.tcl ends the script without stopping yosys from entering
        # the shell, which is how the other open tasks honor the flag.
        if self.get("var", "showexit"):
            try:
                options.remove("-C")
            except ValueError:
                pass

        return options

    def _copy_show_files(self):
        if not self.has_show_filepath():
            return

        # copy source in to keep sc_open.tcl simple
        shutil.copy2(self.get_show_filepath(),
                     f"inputs/{self.design_topmodule}.{self.get_show_filetype()}")

    def pre_process(self):
        super().pre_process()
        self._copy_show_files()
