from typing import Union, List, Optional

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGPLParameter

from siliconcompiler import TaskSkip


class MacroPlacementTask(APRTask, OpenROADSTAParameter, OpenROADGPLParameter):
    '''
    Macro placement
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("mpl_constraints", "[file]", "constraints script for macro placement")

        self.add_parameter("macro_place_halo", "(float,float)",
                           "macro halo to use when performing automated macro placement "
                           "([x, y] in microns)", unit="um")

        self.add_parameter("mpl_min_instances", "int",
                           "minimum number of instances to use while clustering for "
                           "macro placement")
        self.add_parameter("mpl_max_instances", "int",
                           "maximum number of instances to use while clustering for "
                           "macro placement")
        self.add_parameter("mpl_min_macros", "int",
                           "minimum number of macros to use while clustering for macro placement")
        self.add_parameter("mpl_max_macros", "int",
                           "maximum number of macros to use while clustering for macro placement")
        self.add_parameter("mpl_max_levels", "int",
                           "maximum depth of physical hierarchical tree")
        self.add_parameter("mpl_min_aspect_ratio", "float",
                           "Specifies the minimum aspect ratio of its width to height of a "
                           "standard cell cluster")
        self.add_parameter("mpl_fence", "(float,float,float,float)",
                           "Defines the global fence bounding box coordinates (llx, lly, urx, ury)",
                           unit="um")
        self.add_parameter("mpl_bus_planning", "bool",
                           "Flag to enable bus planning", defvalue=False)
        self.add_parameter("mpl_target_dead_space", "float",
                           "Specifies the target dead space percentage, which influences the "
                           "utilization of standard cell clusters")

        self.add_parameter("mpl_area_weight", "float",
                           "Weight for the area of current floorplan")
        self.add_parameter("mpl_outline_weight", "float",
                           "Weight for violating the fixed outline constraint, meaning that all "
                           "clusters should be placed within the shape of their parent cluster")
        self.add_parameter("mpl_wirelength_weight", "float",
                           "Weight for half-perimeter wirelength")
        self.add_parameter("mpl_guidance_weight", "float",
                           "Weight for guidance cost or clusters being placed near specified "
                           "regions if users provide such constraints")
        self.add_parameter("mpl_fence_weight", "float",
                           "Weight for fence cost, or how far the macro is from zero fence "
                           "violation")
        self.add_parameter("mpl_boundary_weight", "float",
                           "Weight for the boundary, or how far the hard macro clusters are from "
                           "boundaries. Note that mixed macro clusters are not pushed, thus not "
                           "considered in this cost.")
        self.add_parameter("mpl_blockage_weight", "float",
                           "Weight for the boundary, or how far the hard macro clusters are from "
                           "boundaries")
        self.add_parameter("mpl_notch_weight", "float",
                           "Weight for the notch, or the existence of dead space that cannot be "
                           "used for placement & routing")
        self.add_parameter("mpl_macro_blockage_weight", "float",
                           "Weight for macro blockage, or the overlapping instances of the macro")

    def add_openroad_mplconstraints(self, constraints: Union[str, List[str]],
                                    step: Optional[str] = None, index: Optional[str] = None,
                                    clobber: bool = False):
        """
        Adds constraints scripts for macro placement.

        Args:
            constraints (Union[str, List[str]]): The constraint file(s) to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "mpl_constraints", constraints, step=step, index=index)
        else:
            self.add("var", "mpl_constraints", constraints, step=step, index=index)

    def set_openroad_macroplacehalo(self, x: float, y: float,
                                    step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the macro halo to use when performing automated macro placement.

        Args:
            x (float): Halo in X direction (microns).
            y (float): Halo in Y direction (microns).
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "macro_place_halo", (x, y), step=step, index=index)

    def set_openroad_mplmininstances(self, count: int,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the minimum number of instances to use while clustering for macro placement.

        Args:
            count (int): The minimum instance count.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_min_instances", count, step=step, index=index)

    def set_openroad_mplmaxinstances(self, count: int,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the maximum number of instances to use while clustering for macro placement.

        Args:
            count (int): The maximum instance count.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_max_instances", count, step=step, index=index)

    def set_openroad_mplminmacros(self, count: int,
                                  step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the minimum number of macros to use while clustering for macro placement.

        Args:
            count (int): The minimum macro count.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_min_macros", count, step=step, index=index)

    def set_openroad_mplmaxmacros(self, count: int,
                                  step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the maximum number of macros to use while clustering for macro placement.

        Args:
            count (int): The maximum macro count.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_max_macros", count, step=step, index=index)

    def set_openroad_mplmaxlevels(self, levels: int,
                                  step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the maximum depth of the physical hierarchical tree.

        Args:
            levels (int): The maximum levels.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_max_levels", levels, step=step, index=index)

    def set_openroad_mplminaspectratio(self, ratio: float,
                                       step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the minimum aspect ratio of width to height of a standard cell cluster.

        Args:
            ratio (float): The minimum aspect ratio.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_min_aspect_ratio", ratio, step=step, index=index)

    def set_openroad_mplfence(self, llx: float, lly: float, urx: float, ury: float,
                              step: Optional[str] = None, index: Optional[str] = None):
        """
        Defines the global fence bounding box coordinates.

        Args:
            llx (float): Lower-left X coordinate (microns).
            lly (float): Lower-left Y coordinate (microns).
            urx (float): Upper-right X coordinate (microns).
            ury (float): Upper-right Y coordinate (microns).
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_fence", (llx, lly, urx, ury), step=step, index=index)

    def set_openroad_mplbusplanning(self, enable: bool,
                                    step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables bus planning.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_bus_planning", enable, step=step, index=index)

    def set_openroad_mpltargetdeadspace(self, percentage: float,
                                        step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the target dead space percentage.

        Args:
            percentage (float): The target dead space percentage.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_target_dead_space", percentage, step=step, index=index)

    def set_openroad_mplareaweight(self, weight: float,
                                   step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for the area of the current floorplan.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_area_weight", weight, step=step, index=index)

    def set_openroad_mploutlineweight(self, weight: float,
                                      step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for violating the fixed outline constraint.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_outline_weight", weight, step=step, index=index)

    def set_openroad_mplwirelengthweight(self, weight: float,
                                         step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for half-perimeter wirelength.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_wirelength_weight", weight, step=step, index=index)

    def set_openroad_mplguidanceweight(self, weight: float,
                                       step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for guidance cost.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_guidance_weight", weight, step=step, index=index)

    def set_openroad_mplfenceweight(self, weight: float,
                                    step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for fence cost.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_fence_weight", weight, step=step, index=index)

    def set_openroad_mplboundaryweight(self, weight: float,
                                       step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for the boundary cost.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_boundary_weight", weight, step=step, index=index)

    def set_openroad_mplblockageweight(self, weight: float,
                                       step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for the blockage cost.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_blockage_weight", weight, step=step, index=index)

    def set_openroad_mplnotchweight(self, weight: float,
                                    step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the weight for the notch cost.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_notch_weight", weight, step=step, index=index)

    def set_openroad_mplmacroblockageweight(self, weight: float,
                                            step: Optional[str] = None,
                                            index: Optional[str] = None):
        """
        Sets the weight for macro blockage cost.

        Args:
            weight (float): The weight value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mpl_macro_blockage_weight", weight, step=step, index=index)

    def task(self):
        return "macro_placement"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_macro_placement.tcl")

        self._set_reports([
            'setup',
            'unconstrained'
        ])

        self.set_asic_var("macro_place_halo", require=True, mainlib_key="macro_placement_halo")

        if self.get("var", "mpl_constraints"):
            self.add_required_key("var", "mpl_constraints")

        if self.get("var", "mpl_min_instances") is not None:
            self.add_required_key("var", "mpl_min_instances")
        if self.get("var", "mpl_max_instances") is not None:
            self.add_required_key("var", "mpl_max_instances")
        if self.get("var", "mpl_min_macros") is not None:
            self.add_required_key("var", "mpl_min_macros")
        if self.get("var", "mpl_max_macros") is not None:
            self.add_required_key("var", "mpl_max_macros")
        if self.get("var", "mpl_max_levels") is not None:
            self.add_required_key("var", "mpl_max_levels")
        if self.get("var", "mpl_min_aspect_ratio") is not None:
            self.add_required_key("var", "mpl_min_aspect_ratio")
        if self.get("var", "mpl_fence") is not None:
            self.add_required_key("var", "mpl_fence")
        self.add_required_key("var", "mpl_bus_planning")
        if self.get("var", "mpl_target_dead_space") is not None:
            self.add_required_key("var", "mpl_target_dead_space")
        if self.get("var", "mpl_area_weight") is not None:
            self.add_required_key("var", "mpl_area_weight")
        if self.get("var", "mpl_outline_weight") is not None:
            self.add_required_key("var", "mpl_outline_weight")
        if self.get("var", "mpl_wirelength_weight") is not None:
            self.add_required_key("var", "mpl_wirelength_weight")
        if self.get("var", "mpl_guidance_weight") is not None:
            self.add_required_key("var", "mpl_guidance_weight")
        if self.get("var", "mpl_fence_weight") is not None:
            self.add_required_key("var", "mpl_fence_weight")
        if self.get("var", "mpl_boundary_weight") is not None:
            self.add_required_key("var", "mpl_boundary_weight")
        if self.get("var", "mpl_blockage_weight") is not None:
            self.add_required_key("var", "mpl_blockage_weight")
        if self.get("var", "mpl_notch_weight") is not None:
            self.add_required_key("var", "mpl_notch_weight")
        if self.get("var", "mpl_macro_blockage_weight") is not None:
            self.add_required_key("var", "mpl_macro_blockage_weight")

    def pre_process(self):
        if all([
                self.schema_metric.get('macros', step=in_step, index=in_index) == 0
                for in_step, in_index in self.schema_record.get('inputnode',
                                                                step=self.step,
                                                                index=self.index)
                ]):
            raise TaskSkip('no macros to place.')

        super().pre_process()
