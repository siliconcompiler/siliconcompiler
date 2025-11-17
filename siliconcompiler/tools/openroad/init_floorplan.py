from typing import Union, List, Optional

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPPLParameter


class InitFloorplanTask(APRTask,
                        OpenROADSTAParameter,
                        OpenROADPPLParameter):
    """
    Perform floorplanning and initial pin placements.

    This task handles the initialization of the floorplan, including macro placement
    snapping strategies, cleaning up synthesis artifacts (buffers/dead logic),
    and defining padring or bumpmap configurations.
    """
    def __init__(self):
        super().__init__()

        self.add_parameter("ifp_snap_strategy", "<none,site,grid>",
                           "Snapping strategy to use when placing macros.", defvalue="site")
        self.add_parameter("remove_synth_buffers", "bool",
                           "remove buffers inserted by synthesis", defvalue=True)
        self.add_parameter("remove_dead_logic", "bool",
                           "remove logic which does not drive a primary output", defvalue=True)

        self.add_parameter("padringfileset", "[str]", "filesets to generate a padring")
        self.add_parameter("bumpmapfileset", "[str]", "filesets to generate a bumpmap")

    def set_openroad_snapstrategy(self, snap: str,
                                  step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the snapping strategy for macro placement.

        Args:
            snap: The snapping mode. Options are typically 'none', 'site', or 'grid'.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "ifp_snap_strategy", snap, step=step, index=index)

    def set_openroad_removebuffers(self, enable: bool,
                                   step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables the removal of buffers inserted during synthesis.

        Args:
            enable: True to remove synthesis buffers, False to keep them.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "remove_synth_buffers", enable, step=step, index=index)

    def set_openroad_removedeadlogic(self, enable: bool,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables the removal of logic that does not drive a primary output.

        Args:
            enable: True to remove dead logic, False to keep it.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "remove_dead_logic", enable, step=step, index=index)

    def add_openroad_padringfileset(self, fileset: Union[str, List[str]],
                                    step: Optional[str] = None, index: Optional[str] = None,
                                    clobber: bool = False):
        """
        Adds fileset(s) used to generate the I/O pad ring.

        Args:
            fileset: A string name or list of names representing the padring filesets.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
            clobber: If True, overwrites the existing padring fileset list.
                     If False, appends to the existing list.
        """
        if clobber:
            self.set("var", "padringfileset", fileset, step=step, index=index)
        else:
            self.add("var", "padringfileset", fileset, step=step, index=index)

    def add_openroad_bumpmapfileset(self, fileset: Union[str, List[str]],
                                    step: Optional[str] = None, index: Optional[str] = None,
                                    clobber: bool = False):
        """
        Adds fileset(s) used to generate the bump map for flip-chip or 3D designs.

        Args:
            fileset: A string name or list of names representing the bumpmap filesets.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
            clobber: If True, overwrites the existing bumpmap fileset list.
                     If False, appends to the existing list.
        """
        if clobber:
            self.set("var", "bumpmapfileset", fileset, step=step, index=index)
        else:
            self.add("var", "bumpmapfileset", fileset, step=step, index=index)

    def task(self):
        return "init_floorplan"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_init_floorplan.tcl")

        # if chip.valid('input', 'asic', 'floorplan') and \
        #    chip.get('input', 'asic', 'floorplan', step=step, index=index):
        #     chip.add('tool', tool, 'task', task, 'require',
        #              ",".join(['input', 'asic', 'floorplan']),
        #              step=step, index=index)

        # if f'{design}.vg' in input_provides(chip, step, index):
        #     chip.add('tool', tool, 'task', task, 'input', f'{design}.vg',
        #              step=step, index=index)
        # else:
        #     chip.add('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
        #              step=step, index=index)
        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        else:
            pass

        self._set_reports([
            'check_setup',
            'setup',
            'unconstrained',
            'power'
        ])

        self.add_required_key("var", "ifp_snap_strategy")
        self.add_required_key("var", "remove_synth_buffers")
        self.add_required_key("var", "remove_dead_logic")

        if self.get("var", "padringfileset"):
            self.add_required_key("var", "padringfileset")

            for fileset in self.get("var", "padringfileset"):
                self.add_required_key(self.project.design, "fileset", fileset, "file", "tcl")

        if self.get("var", "bumpmapfileset"):
            self.add_required_key("var", "bumpmapfileset")

            for fileset in self.get("var", "bumpmapfileset"):
                self.add_required_key(self.project.design, "fileset", fileset, "file", "bmap")

        # Mark requires for components, pin, and floorplan placements
        for component in self.project.constraint.component.get_component().values():
            self.add_required_key(component, "placement")
            self.add_required_key(component, "rotation")
            if component.get_partname(step=self.step, index=self.index):
                self.add_required_key(component, "partname")

        for pin in self.project.constraint.pin.get_pinconstraint().values():
            if pin.get_placement(step=self.step, index=self.index) is not None:
                self.add_required_key(pin, "placement")
            if pin.get_layer(step=self.step, index=self.index) is not None:
                self.add_required_key(pin, "layer")
            if pin.get_side(step=self.step, index=self.index) is not None:
                self.add_required_key(pin, "side")
            if pin.get_order(step=self.step, index=self.index) is not None:
                self.add_required_key(pin, "order")

        self.add_required_key(self.mainlib, "asic", "site")
        if self.project.constraint.area.get_diearea(step=self.step, index=self.index) and \
                self.project.constraint.area.get_corearea(step=self.step, index=self.index):
            self.add_required_key(self.project.constraint.area, "diearea")
            self.add_required_key(self.project.constraint.area, "corearea")
        else:
            self.add_required_key(self.project.constraint.area, "aspectratio")
            self.add_required_key(self.project.constraint.area, "density")
            self.add_required_key(self.project.constraint.area, "coremargin")

        if self.mainlib.get("tool", "openroad", "tracks"):
            self.add_required_key(self.mainlib, "tool", "openroad", "tracks")
