import shutil

import os.path

from typing import List

from siliconcompiler import OpenTask as BaseOpenTask
from siliconcompiler.tools.opensta.timing import TimingTask


class OpenTask(BaseOpenTask, TimingTask):
    '''
    Open a gate-level netlist in an interactive OpenSTA session.

    Reuses :class:`.TimingTask`'s input handling so the same liberty, SDC, SPEF
    and SDF selection is applied, then stops instead of reporting: the design is
    linked, the corners are defined and the path groups exist, and OpenSTA is
    left at its prompt.

    When a ``showfilepath`` is provided (e.g. via ``sc-show -open``) the netlist
    plus any sibling SDC and parasitics from the source node are copied into
    ``inputs`` at runtime, so the session sees the design as the node that wrote
    it did.
    '''
    def __init__(self):
        super().__init__()

    def setup(self):
        super().setup()

        # An interactive session produces no output artifacts
        self.unset("output")

        # If neither input-node files nor an explicit showfilepath are
        # available, require the user to supply a file.
        if not self.get("input") and not self.has_show_filepath():
            self.add_required_key("var", "showfilepath")

        # clobber: TimingTask already pointed the task at sc_timing.tcl
        self.set_script("sc_open.tcl", clobber=True)

        self.set("var", "showexit", False, clobber=False)

    def _add_netlist_inputs(self):
        if self.has_show_filepath():
            return
        super()._add_netlist_inputs()

    def get_supported_task_extentions(self) -> List[str]:
        return ["vg"]

    def _get_parasitic_extensions(self) -> List[str]:
        """Per-corner parasitic file extensions sc_read_design.tcl looks for.

        Ordered and deduplicated: several scenarios routinely share one
        ``pexcorner``, and the tcl reads each file once per scenario.
        """
        exts = []
        for scenario in self.project.constraint.timing.get_scenario().values():
            pexcorner = scenario.get("pexcorner")
            if pexcorner is None:
                continue
            for ext in (f"{pexcorner}.spef", f"{pexcorner}.sdf"):
                if ext not in exts:
                    exts.append(ext)
        return exts

    def _copy_show_files(self):
        if not self.has_show_filepath():
            return

        show_file = self.get_show_filepath()
        show_type = self.get_show_filetype()

        # copy source in to keep sc_read_design.tcl simple
        shutil.copy2(show_file, f"inputs/{self.design_topmodule}.{show_type}")

        show_workdir = self.get_show_workdir()
        if not show_workdir:
            return

        src_outputs = os.path.join(show_workdir, "outputs")

        # A netlist on its own only gets as far as link_design. Bring the source
        # node's constraints and parasitics along so the session reports the same
        # numbers that node did; sc_read_design.tcl prefers these over the
        # fileset SDC when they are present.
        for ext in ("sdc", *self._get_parasitic_extensions()):
            src_file = os.path.join(src_outputs, f"{self.design_topmodule}.{ext}")
            if os.path.exists(src_file):
                shutil.copy2(src_file, f"inputs/{self.design_topmodule}.{ext}")

    def pre_process(self):
        super().pre_process()
        self._copy_show_files()
