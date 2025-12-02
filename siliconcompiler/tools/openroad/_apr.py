import os
import json

from typing import List, Union, Optional

from siliconcompiler import sc_open
from siliconcompiler import utils
from siliconcompiler.asic import CellArea


from siliconcompiler.tools.openroad import OpenROADTask


class OpenROADSTAParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("sta_early_timing_derate", "float",
                           "timing derating factor to use for hold corners", defvalue=0.0)
        self.add_parameter("sta_late_timing_derate", "float",
                           "timing derating factor to use for setup corners", defvalue=0.0)
        self.add_parameter("sta_top_n_paths", "int",
                           "number of paths to report timing for", defvalue=10)
        self.add_parameter("sta_define_path_groups", "bool",
                           "if true will generate path groups for timing reporting", defvalue=True)
        self.add_parameter("sta_unique_path_groups_per_clock", "bool",
                           "if true will generate separate path groups per clock", defvalue=False)

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")
        self.add_parameter("opensta_generic_sdc", "file", "generic opensta SDC file",
                           defvalue="tools/_common/sdc/sc_constraints.sdc",
                           dataroot="siliconcompiler")

    def setup(self):
        super().setup()

        self.add_required_key("var", "sta_early_timing_derate")
        self.add_required_key("var", "sta_late_timing_derate")
        self.add_required_key("var", "sta_top_n_paths")
        self.add_required_key("var", "sta_define_path_groups")
        self.add_required_key("var", "sta_unique_path_groups_per_clock")
        self.add_required_key("var", "opensta_generic_sdc")


class OpenROADPSMParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("psm_enable", "bool",
                           "true/false, when true enables IR drop analysis", defvalue=True)
        self.add_parameter("psm_skip_nets", "[str]", "list of nets to skip power grid analysis on")

    def setup(self):
        super().setup()

        self.add_required_key("var", "psm_enable")
        if self.get("var", "psm_skip_nets"):
            self.add_required_key("var", "psm_skip_nets")


class OpenROADPPLLayersParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("pin_layer_horizontal", "[str]", "layers to use for horizontal pins")
        self.add_parameter("pin_layer_vertical", "[str]", "layers to use for vertical pins")

    def setup(self):
        super().setup()

        self.set_asic_var("pin_layer_horizontal", require=True)
        self.set_asic_var("pin_layer_vertical", require=True)


class OpenROADPPLParameter(OpenROADPPLLayersParameter):
    def __init__(self):
        super().__init__()

        self.add_parameter("ppl_arguments", "[str]",
                           "additional arguments to pass along to the pin placer.")
        self.add_parameter("ppl_constraints", "[file]", "pin placement constraints scripts.")

    def setup(self):
        super().setup()

        if self.get("var", "ppl_arguments"):
            self.add_required_key("var", "ppl_arguments")

        if self.get("var", "ppl_constraints"):
            self.add_required_key("var", "ppl_constraints")


class OpenROADGPLParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("gpl_enable_skip_io", "bool", "true/false, when enabled a global "
                           "placement is performed without considering the impact of the pin "
                           "placements",
                           defvalue=True)
        self.add_parameter("gpl_enable_skip_initial_place", "bool",
                           "true/false, when enabled a global placement skips the initial "
                           "placement, before the main global placement pass.", defvalue=False)
        self.add_parameter("gpl_uniform_placement_adjustment", "float",
                           "percent of remaining area density to apply above uniform density "
                           "(0.00 - 0.99)", defvalue=0.0)
        self.add_parameter("gpl_timing_driven", "bool",
                           "true/false, when true global placement will consider the timing "
                           "performance of the design", defvalue=True)
        self.add_parameter("gpl_routability_driven", "bool",
                           "true/false, when true global placement will consider the routability "
                           "of the design", defvalue=True)

        self.add_parameter("place_density", "float",
                           "global placement density (0.0 - 1.0)")
        self.add_parameter("pad_global_place", "int",
                           "global placement cell padding in number of sites", defvalue=0)

    def setup(self):
        super().setup()

        self.add_required_key("var", "gpl_enable_skip_io")
        self.add_required_key("var", "gpl_enable_skip_initial_place")
        self.add_required_key("var", "gpl_uniform_placement_adjustment")
        self.add_required_key("var", "gpl_timing_driven")
        self.add_required_key("var", "gpl_routability_driven")

        self.set_asic_var("place_density", require=True)
        self.set_asic_var("pad_global_place", check_pdk=False, mainlib_key="global_cell_padding")


class OpenROADRSZDRVParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("rsz_cap_margin", "float",
                           "specifies the amount of margin to apply to max capacitance repairs in "
                           "percent (0 - 100)", defvalue=0.0)
        self.add_parameter("rsz_slew_margin", "float",
                           "specifies the amount of margin to apply to max slew repairs in percent "
                           "(0 - 100)", defvalue=0.0)

    def setup(self):
        super().setup()

        self.add_required_key("var", "rsz_cap_margin")
        self.add_required_key("var", "rsz_slew_margin")


class OpenROADRSZTimingParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("rsz_setup_slack_margin", "float",
                           "specifies the margin to apply when performing setup repair",
                           defvalue=0.0, unit="ns")
        self.add_parameter("rsz_hold_slack_margin", "float",
                           "specifies the margin to apply when performing hold repair",
                           defvalue=0.0, unit="ns")

        self.add_parameter("rsz_skip_pin_swap", "bool",
                           "true/false, skip pin swap optimization", defvalue=True)
        self.add_parameter("rsz_skip_gate_cloning", "bool",
                           "true/false, skip gate cloning optimization", defvalue=True)
        self.add_parameter("rsz_repair_tns", "float",
                           "percentage of violating nets to attempt to repair (0 - 100)",
                           defvalue=100)
        self.add_parameter("rsz_recover_power", "float",
                           "percentage of paths to attempt to recover power (0 - 100)",
                           defvalue=100)

    def setup(self):
        super().setup()

        self.add_required_key("var", "rsz_setup_slack_margin")
        self.add_required_key("var", "rsz_hold_slack_margin")
        self.add_required_key("var", "rsz_skip_pin_swap")
        self.add_required_key("var", "rsz_skip_gate_cloning")
        self.add_required_key("var", "rsz_repair_tns")
        self.add_required_key("var", "rsz_recover_power")


class OpenROADDPLParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("pad_detail_place", "int",
                           "detailed placement cell padding in number of sites", defvalue=0)
        self.add_parameter("dpl_max_displacement", "(float,float)",
                           "maximum cell movement in detailed placement in microns, 0 will result "
                           "in the tool default maximum displacement", defvalue=(0, 0))

    def setup(self):
        super().setup()

        self.add_required_key("var", "pad_detail_place")
        self.add_required_key("var", "dpl_max_displacement")


class OpenROADFillCellsParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("dpl_use_decap_fillers", "bool",
                           "true/false, use decap fillers along with non-decap fillers",
                           defvalue=True)

    def setup(self):
        super().setup()

        self.add_required_key("var", "dpl_use_decap_fillers")


class OpenROADDPOParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("dpo_enable", "bool",
                           "true/false, when true the detailed placement optimization will be "
                           "performed", defvalue=True)
        self.add_parameter("dpo_max_displacement", "(float,float)",
                           "maximum cell movement in detailed placement optimization in microns, "
                           "0 will result in the tool default maximum displacement", unit="um",
                           defvalue=(5, 5))

    def setup(self):
        super().setup()

        self.add_required_key("var", "dpo_enable")
        self.add_required_key("var", "dpo_max_displacement")


class OpenROADCTSParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("cts_distance_between_buffers", "float",
                           "maximum distance between buffers during clock tree synthesis in "
                           "microns", defvalue=100, unit="um")
        self.add_parameter("cts_cluster_diameter", "float",
                           "clustering distance to use during clock tree synthesis in microns",
                           defvalue=100, unit="um")
        self.add_parameter("cts_cluster_size", "int",
                           "number of instances in a cluster to use during clock tree synthesis",
                           defvalue=30)
        self.add_parameter("cts_balance_levels", "bool",
                           "perform level balancing in clock tree synthesis", defvalue=True)
        self.add_parameter("cts_obstruction_aware", "bool",
                           "make clock tree synthesis aware of obstructions", defvalue=True)

    def setup(self):
        super().setup()

        self.add_required_key("var", "cts_distance_between_buffers")
        self.add_required_key("var", "cts_cluster_diameter")
        self.add_required_key("var", "cts_cluster_size")
        self.add_required_key("var", "cts_balance_levels")
        self.add_required_key("var", "cts_obstruction_aware")


class OpenROADGRTGeneralParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("grt_macro_extension", "int",
                           "macro extension distance in number of gcells, this can be useful when "
                           "the detailed router needs additional space to avoid DRCs", defvalue=0)
        self.add_parameter("grt_signal_min_layer", "str",
                           "minimum layer to use for global routing of signals")
        self.add_parameter("grt_signal_max_layer", "str",
                           "maximum layer to use for global routing of signals")
        self.add_parameter("grt_clock_min_layer", "str",
                           "minimum layer to use for global routing of clock nets")
        self.add_parameter("grt_clock_max_layer", "str",
                           "maximum layer to use for global routing of clock nets")

    def setup(self):
        super().setup()

        min_layer = self.project.get("asic", "minlayer")
        if not min_layer:
            min_layer = self.pdk.get("pdk", "minlayer")
        max_layer = self.project.get("asic", "maxlayer")
        if not max_layer:
            max_layer = self.pdk.get("pdk", "maxlayer")

        self.set("var", "load_grt_setup", True, clobber=False)
        self.set("var", "grt_signal_min_layer", min_layer, clobber=False)
        self.set("var", "grt_clock_min_layer", min_layer, clobber=False)
        self.set("var", "grt_signal_max_layer", max_layer, clobber=False)
        self.set("var", "grt_clock_max_layer", max_layer, clobber=False)

        self.add_required_key("var", "grt_macro_extension")
        self.add_required_key("var", "grt_signal_min_layer")
        self.add_required_key("var", "grt_clock_min_layer")
        self.add_required_key("var", "grt_signal_max_layer")
        self.add_required_key("var", "grt_clock_max_layer")


class OpenROADGRTParameter(OpenROADGRTGeneralParameter):
    def __init__(self):
        super().__init__()

        self.add_parameter("grt_allow_congestion", "bool",
                           "true/false, when true allow global routing to finish with congestion",
                           defvalue=False)
        self.add_parameter("grt_overflow_iter", "int",
                           "maximum number of iterations to use in global routing when attempting "
                           "to solve overflow", defvalue=100)

    def setup(self):
        super().setup()

        self.add_required_key("var", "grt_allow_congestion")
        self.add_required_key("var", "grt_overflow_iter")


class OpenROADANTParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("ant_iterations", "int",
                           "maximum number of repair iterations to use during antenna repairs",
                           defvalue=3)
        self.add_parameter("ant_margin", "float", "adds a margin to the antenna ratios (0 - 100)",
                           defvalue=0)

    def setup(self):
        super().setup()

        self.add_required_key("var", "ant_iterations")
        self.add_required_key("var", "ant_margin")


class _OpenROADDRTCommonParameter(OpenROADTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("drt_process_node", "str",
                           "when set this specifies to the detailed router the specific process "
                           "node")
        self.add_parameter("detailed_route_default_via", "[str]",
                           "list of default vias to use for detail routing")
        self.add_parameter("detailed_route_unidirectional_layer", "[str]",
                           "list of layers to treat as unidirectional regardless of what the tech "
                           "lef specifies")

    def setup(self):
        super().setup()

        if not self.get("var", "drt_process_node"):
            if self.pdk.get("tool", "openroad", "drt_process_node"):
                self.add_required_key(self.pdk, "tool", "openroad", "drt_process_node")
                self.set("var", "drt_process_node",
                         self.pdk.get("tool", "openroad", "drt_process_node"))

        if self.get("var", "drt_process_node"):
            self.add_required_key("var", "drt_process_node")
        if self.get("var", "detailed_route_default_via"):
            self.add_required_key("var", "detailed_route_default_via")
        if self.get("var", "detailed_route_unidirectional_layer"):
            self.add_required_key("var", "detailed_route_unidirectional_layer")


class OpenROADDRTPinAccessParameter(_OpenROADDRTCommonParameter):
    def __init__(self):
        super().__init__()


class OpenROADDRTParameter(_OpenROADDRTCommonParameter):
    def __init__(self):
        super().__init__()

        self.add_parameter("drt_disable_via_gen", "bool",
                           "true/false, when true turns off via generation in detailed router "
                           "and only uses the specified tech vias", defvalue=False)
        self.add_parameter("drt_via_in_pin_bottom_layer", "str", "TODO")
        self.add_parameter("drt_via_in_pin_top_layer", "str", "TODO")
        self.add_parameter("drt_repair_pdn_vias", "str", "TODO")

        self.add_parameter("drt_report_interval", "int",
                           "reporting interval in steps for generating a DRC report.", defvalue=5)
        self.add_parameter("drt_end_iteration", "int",
                           "end iteration for detailed routing")

    def setup(self):
        super().setup()

        if not self.get("var", "drt_disable_via_gen"):
            if self.pdk.get("tool", "openroad", "drt_disable_via_gen"):
                self.add_required_key(self.pdk, "tool", "openroad", "drt_disable_via_gen")
                self.set("var", "drt_disable_via_gen",
                         self.pdk.get("tool", "openroad", "drt_disable_via_gen"))

        if not self.get("var", "drt_repair_pdn_vias"):
            if self.pdk.get("tool", "openroad", "drt_repair_pdn_vias"):
                self.add_required_key(self.pdk, "tool", "openroad", "drt_repair_pdn_vias")
                self.set("var", "drt_repair_pdn_vias",
                         self.pdk.get("tool", "openroad", "drt_repair_pdn_vias"))

        self.add_required_key("var", "drt_disable_via_gen")
        if self.get("var", "drt_via_in_pin_bottom_layer"):
            self.add_required_key("var", "drt_via_in_pin_bottom_layer")
        if self.get("var", "drt_via_in_pin_top_layer"):
            self.add_required_key("var", "drt_via_in_pin_top_layer")
        if self.get("var", "drt_repair_pdn_vias"):
            self.add_required_key("var", "drt_repair_pdn_vias")
        if self.get("var", "drt_end_iteration"):
            self.add_required_key("var", "drt_end_iteration")
        self.add_required_key("var", "drt_report_interval")


class APRTask(OpenROADTask):
    """
    Base class for OpenROAD-based Automatic Place and Route (APR) tasks.

    This task initializes specific configurations for OpenROAD, including
    report filtering, image generation settings, heatmap binning, and
    power analysis corners.
    """

    def __init__(self):
        super().__init__()

        supported = (
            "setup",
            "hold",
            "unconstrained",
            "clock_skew",
            "drv_violations",
            "fmax",
            "power",
            "check_setup",
            "report_buffers",
            "placement_density",
            "routing_congestion",
            "power_density",
            "ir_drop",
            "clock_placement",
            "clock_trees",
            "optimization_placement",
            "module_view"
        )
        self.add_parameter("reports", f"{{<{','.join(supported)}>}}",
                           "list of reports and images to generate, auto generated")
        self.add_parameter("skip_reports", f"{{<{','.join(supported)}>}}",
                           "list of reports and images skip")

        self.add_parameter("ord_enable_images", "bool",
                           "true/false, enable generating images of the design at the end "
                           "of the task", defvalue=True)
        self.add_parameter("ord_heatmap_bins", "(int,int)",
                           "number of (X, Y) bins to use for heatmap image generation",
                           defvalue=(16, 16))

        self.add_parameter("rsz_parasitics", "file",
                           "file used to specify the parasitics for estimation", copy=False)
        self.add_parameter("power_corner", "str",
                           "corner to use for power analysis")

        self.add_parameter("load_grt_setup", "bool",
                           "used to indicate if global routing information should be loaded",
                           defvalue=False)

        self.add_parameter("global_connect_fileset", "[(str,str)]",
                           "list of libraries and filesets to generate connects from")

    def add_openroad_skipreport(self, report_type: Union[List[str], str],
                                step: Optional[str] = None, index: Optional[str] = None,
                                clobber: bool = False) -> None:
        """
        Adds or sets report types to be skipped during OpenROAD execution.

        Args:
            report_type: The name of the report(s) to skip (e.g., 'routing_congestion').
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
            clobber: If True, overwrites the existing list of skipped reports.
                     If False, appends to the existing list.
        """
        if clobber:
            self.set("var", "skip_reports", report_type, step=step, index=index)
        else:
            self.add("var", "skip_reports", report_type, step=step, index=index)

    def set_openroad_enableimages(self, enable: bool,
                                  step: Optional[str] = None, index: Optional[str] = None) -> None:
        """
        Enables or disables the generation of design images at the end of the task.

        Args:
            enable: True to generate images, False to disable.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "ord_enable_images", enable, step=step, index=index)

    def set_openroad_heatmapbins(self, x: int, y: int,
                                 step: Optional[str] = None, index: Optional[str] = None) -> None:
        """
        Configures the resolution of the heatmap images.

        Args:
            x: The number of bins in the X direction.
            y: The number of bins in the Y direction.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "ord_heatmap_bins", (x, y), step=step, index=index)

    def set_openroad_powercorner(self, corner: str,
                                 step: Optional[str] = None, index: Optional[str] = None) -> None:
        """
        Sets the specific process corner used for power analysis.

        Args:
            corner: The name of the timing/power corner.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "power_corner", corner, step=step, index=index)

    def add_openroad_globalconnectfileset(self, library: str, fileset: str,
                                          step: Optional[str] = None, index: Optional[str] = None,
                                          clobber: bool = False):
        """
        Adds a library and fileset pair to the global connect configuration.

        Args:
            library: The name of the library.
            fileset: The name of the fileset.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
            clobber: If True, overwrites the existing global connect settings.
                     If False, appends to the existing settings.
        """
        if clobber:
            self.set("var", "global_connect_fileset", (library, fileset), step=step, index=index)
        else:
            self.add("var", "global_connect_fileset", (library, fileset), step=step, index=index)

    def setup(self):
        """
        Configure APRTask prerequisites and required project keys for an OpenROAD run.

        Performs task-wide setup: configures threading, declares PNR inputs and outputs, sets the
        default power corner from timing constraints (without clobbering existing values), and
        declares required variables and file dependencies used later in the flow. Specifically, it:
        - Ensures ord_enable_images, ord_heatmap_bins, and load_grt_setup are present as
            required keys.
        - Adds reports and skip_reports as required keys when they are present in the
            project variables.
        - Imports and registers global_connect_fileset entries when absent or present, and declares
            per-library fileset TCL file requirements for each entry.
        - Aggregates libcorner names from timing scenarios and, for each ASIC library and matching
            delay model, declares required libcorner filesets and per-fileset liberty file
            requirements.

        Side effects:
        - Mutates the task/project state by setting variables, adding required keys, and
            possibly importing global connect filesets.
        """
        super().setup()

        self.set_threads()

        self._add_pnr_inputs()
        self._add_pnr_outputs()

        # Set power corner
        self.set("var", "power_corner", self._get_constraint_by_check("power"), clobber=False)

        if self.get("var", "reports"):
            self.add_required_key("var", "reports")
        if self.get("var", "skip_reports"):
            self.add_required_key("var", "skip_reports")

        self.add_required_key("var", "ord_enable_images")
        self.add_required_key("var", "ord_heatmap_bins")
        self.add_required_key("var", "load_grt_setup")

        if not self.get("var", "global_connect_fileset"):
            self.__import_globalconnect_filesets()

        if self.get("var", "global_connect_fileset"):
            self.add_required_key("var", "global_connect_fileset")
            for lib, fileset in self.get("var", "global_connect_fileset"):
                self.add_required_key("library", lib, "fileset", fileset, "file", "tcl")

        libcorners = set()
        for scenario in self.project.constraint.timing.get_scenario().values():
            libcorners.update(scenario.get_libcorner(self.step, self.index))
        delay_model = self.project.get("asic", "delaymodel")
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get("library", asiclib, field="schema")
            for corner in libcorners:
                if not lib.valid("asic", "libcornerfileset", corner, delay_model):
                    continue
                self.add_required_key(lib, "asic", "libcornerfileset", corner, delay_model)
                for fileset in lib.get("asic", "libcornerfileset", corner, delay_model):
                    self.add_required_key(lib, "fileset", fileset, "file", "liberty")

    def pre_process(self):
        super().pre_process()
        self._build_pex_estimation_file()

    def __import_globalconnect_filesets(self):
        for lib in self.project.get("asic", "asiclib"):
            libobj = self.project.get("library", lib, field="schema")
            if libobj.valid("tool", "openroad", "global_connect_fileset"):
                for fileset in libobj.get("tool", "openroad", "global_connect_fileset"):
                    self.add_openroad_globalconnectfileset(lib, fileset)

    def _set_reports(self, task_reports: List[str]):
        self.set("var", "reports", set(task_reports).difference(self.get("var", "skip_reports")))

        if "power" in self.get("var", "reports"):
            self.add_required_key("var", "power_corner")

    def _add_pnr_inputs(self):
        if f"{self.design_topmodule}.sdc" in self.get_files_from_input_nodes():
            self.add_input_file(ext="sdc")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="sdc"):
                    self.add_required_key(lib, "fileset", fileset, "file", "sdc")

        if f"{self.design_topmodule}.odb" in self.get_files_from_input_nodes():
            self.add_input_file(ext="odb")
        elif f"{self.design_topmodule}.def" in self.get_files_from_input_nodes():
            self.add_input_file(ext="def")
        else:
            pass

    def _add_pnr_outputs(self):
        self.add_output_file(ext="sdc")
        self.add_output_file(ext="vg")
        self.add_output_file(ext="def")
        self.add_output_file(ext="odb")

    def _get_pex_mapping(self):
        corners = {}
        for constraint in self.project.getkeys('constraint', 'timing'):
            pexcorner = self.project.get('constraint', 'timing', constraint, 'pexcorner',
                                         step=self.step, index=self.index)
            if pexcorner:
                corners[constraint] = pexcorner

        return corners

    def _get_constraint_by_check(self, check: str) -> str:
        for constraint in self.project.getkeys('constraint', 'timing'):
            if check in self.project.get('constraint', 'timing', constraint, 'check',
                                         step=self.step, index=self.index):
                return constraint

        # if not specified, just pick the first constraint available
        return self.project.getkeys('constraint', 'timing')[0]

    def _build_pex_estimation_file(self):
        corners = self._get_pex_mapping()

        default_corner = self._get_constraint_by_check("setup")
        if default_corner in corners:
            corners[None] = corners[default_corner]

        path = os.path.join(self.nodeworkdir, "inputs", "sc_parasitics.tcl")
        self.set("var", "rsz_parasitics", path)

        with open(path, 'w') as f:
            for constraint, pexcorner in corners.items():
                if self.pdk.valid("pdk", "pexmodelfileset", "openroad", pexcorner):
                    pex_source_file = None
                    for fileset in self.pdk.get("pdk", "pexmodelfileset", "openroad", pexcorner):
                        if self.pdk.valid("fileset", fileset, "file", "tcl"):
                            pex_source_file = self.pdk.get_file(fileset, "tcl")[0]
                            break
                    if not pex_source_file:
                        continue

                    corner_pex_template = utils.get_file_template(pex_source_file)
                    pex_template = utils.get_file_template(
                        'pex.tcl',
                        root=os.path.join(os.path.dirname(__file__), 'templates'))

                    if not pex_template:
                        continue

                    if constraint is None:
                        constraint = "default"
                        corner_specification = ""
                    else:
                        corner_specification = f"-corner {constraint}"

                    f.write(pex_template.render(
                        constraint=constraint,
                        pexcorner=pexcorner,
                        source=pex_source_file,
                        pex=corner_pex_template.render({"corner": corner_specification})
                    ))
                    f.write('\n')

    def post_process(self):
        super().post_process()

        self._extract_metrics()

    def _extract_metrics(self):
        '''
        Extract metrics
        '''

        metric_reports = {
            "setuptns": [
                "timing/total_negative_slack.rpt",
                "timing/setup.rpt",
                "timing/setup.histogram.rpt",
                "images/timing/setup.histogram.png"
            ],
            "setupslack": [
                "timing/worst_slack.setup.rpt",
                "timing/setup.rpt",
                "timing/setup.topN.rpt",
                "timing/setup.histogram.rpt",
                "images/timing/setup.histogram.png"
            ],
            "setupskew": [
                "timing/skew.setup.rpt",
                "timing/worst_slack.setup.rpt",
                "timing/setup.rpt",
                "timing/setup.topN.rpt"
            ],
            "setuppaths": [
                "timing/setup.rpt",
                "timing/setup.topN.rpt",
                "timing/setup.histogram.rpt",
                "images/timing/setup.histogram.png"
            ],
            "holdslack": [
                "timing/worst_slack.hold.rpt",
                "timing/hold.rpt",
                "timing/hold.topN.rpt",
                "timing/hold.histogram.rpt",
                "images/timing/hold.histogram.png"
            ],
            "holdskew": [
                "timing/skew.hold.rpt",
                "timing/worst_slack.hold.rpt",
                "timing/hold.rpt",
                "timing/hold.topN.rpt"
            ],
            "holdpaths": [
                "timing/hold.rpt",
                "timing/hold.topN.rpt",
                "timing/hold.histogram.rpt",
                "images/timing/hold.histogram.png"
            ],
            "unconstrained": [
                "timing/unconstrained.rpt",
                "timing/unconstrained.topN.rpt"
            ],
            "peakpower": [
                *[f"power/{corner}.rpt"
                  for corner in self.project.getkeys('constraint', 'timing')],
                *[f"images/heatmap/power_density/{corner}.png"
                    for corner in self.project.getkeys('constraint', 'timing')]
            ],
            "drvs": [
                "timing/drv_violators.rpt",
                "floating_nets.rpt",
                "overdriven_nets.rpt",
                "overdriven_nets_with_parallel.rpt",
                f"{self.design_topmodule}_antenna.rpt",
                f"{self.design_topmodule}_antenna_post_repair.rpt"
            ],
            "drcs": [
                f"{self.design_topmodule}_drc.rpt",
                f"markers/{self.design_topmodule}.drc.rpt",
                f"markers/{self.design_topmodule}.drc.json",
                f"images/markers/{self.design_topmodule}.DRC.png"
            ],
            "utilization": [
                "images/heatmap/placement_density.png"
            ],
            "wirelength": [
                f"images/{self.design_topmodule}.routing.png"
            ]
        }
        metric_reports["leakagepower"] = metric_reports["peakpower"]

        metrics_file = "reports/metrics.json"

        if not os.path.exists(metrics_file):
            self.logger.warning("OpenROAD metrics file is missing")
            return

        def get_metric_sources(metric):
            metric_sources = [metrics_file]
            if metric in metric_reports:
                for metric_file in metric_reports[metric]:
                    metric_path = f'reports/{metric_file}'
                    if os.path.exists(metric_path):
                        metric_sources.append(metric_path)
            return metric_sources

        # parsing log file
        with sc_open(metrics_file) as f:
            try:
                metrics = json.load(f)
            except json.decoder.JSONDecodeError as e:
                self.logger.error(f'Unable to parse metrics from OpenROAD: {e}')
                metrics = {}

            self._generate_cell_area_report(metrics)

            or_units = {}
            for unit, or_unit in [
                    ('time', 'run__flow__platform__time_units'),
                    ('capacitance', 'run__flow__platform__capacitance_units'),
                    ('resistance', 'run__flow__platform__resistance_units'),
                    ('volt', 'run__flow__platform__voltage_units'),
                    ('amp', 'run__flow__platform__current_units'),
                    ('power', 'run__flow__platform__power_units'),
                    ('distance', 'run__flow__platform__distance_units')]:
                if or_unit in metrics:
                    # Remove first digit
                    metric_unit = metrics[or_unit][1:]
                    or_units[unit] = metric_unit

            or_units['distance'] = 'um'  # always microns
            or_units['power'] = 'W'  # always watts
            or_units['area'] = f"{or_units['distance']}^2"
            or_units['frequency'] = 'Hz'  # always hertz

            has_timing = True
            if 'sc__metric__timing__clocks' in metrics:
                has_timing = metrics['sc__metric__timing__clocks'] > 0

            for metric, or_metric, or_use, or_unit in [
                ('vias', 'sc__step__global_route__vias', True, None),
                ('vias', 'sc__step__route__vias', True, None),
                ('wirelength', 'sc__step__global_route__wirelength', True, 'distance'),
                ('wirelength', 'sc__step__route__wirelength', True, 'distance'),
                ('cellarea', 'sc__metric__design__instance__area', True, 'area'),
                ('stdcellarea', 'sc__metric__design__instance__area__stdcell', True, 'area'),
                ('macroarea', 'sc__metric__design__instance__area__macros', True, 'area'),
                ('padcellarea', 'sc__metric__design__instance__area__padcells', True, 'area'),
                ('totalarea', 'sc__metric__design__die__area', True, 'area'),
                ('utilization', 'sc__metric__design__instance__utilization', True, 100.0),
                ('setuptns', 'sc__metric__timing__setup__tns', has_timing, 'time'),
                ('holdtns', 'sc__metric__timing__hold__tns', has_timing, 'time'),
                ('setupslack', 'sc__metric__timing__setup__ws', has_timing, 'time'),
                ('holdslack', 'sc__metric__timing__hold__ws', has_timing, 'time'),
                ('setupskew', 'sc__metric__clock__skew__setup', has_timing, 'time'),
                ('holdskew', 'sc__metric__clock__skew__hold', has_timing, 'time'),
                ('fmax', 'sc__metric__timing__fmax', has_timing, 'frequency'),
                ('setuppaths', 'sc__metric__timing__drv__setup_violation_count', True, None),
                ('holdpaths', 'sc__metric__timing__drv__hold_violation_count', True, None),
                ('unconstrained', 'sc__metric__timing__unconstrained', True, None),
                ('peakpower', 'sc__metric__power__total', True, 'power'),
                ('leakagepower', 'sc__metric__power__leakage__total', True, 'power'),
                ('pins', 'sc__metric__design__io', True, None),
                ('cells', 'sc__metric__design__instance__count', True, None),
                ('macros', 'sc__metric__design__instance__count__macros', True, None),
                ('nets', 'sc__metric__design__nets', True, None),
                ('registers', 'sc__metric__design__registers', True, None),
                ('inverters', 'sc__metric__design__inverters', True, None),
                ('buffers', 'sc__metric__design__buffers', True, None),
                ('logicdepth', 'sc__metric__design__logic__depth', True, None)
            ]:
                if or_metric in metrics:
                    value = metrics[or_metric]

                    # Check for INF timing
                    if or_unit == 'time' and abs(value) > 1e24:
                        or_use = False

                    if or_unit:
                        if or_unit in or_units:
                            or_unit = or_units[or_unit]
                        else:
                            value *= or_unit
                            or_unit = None

                    if or_use:
                        self.record_metric(metric, value, source_file=get_metric_sources(metric),
                                           source_unit=or_unit)

            ir_drop = None
            for or_metric, value in metrics.items():
                if or_metric.startswith("sc__step__design_powergrid__drop__worst__net") or \
                        or_metric.startswith("sc__image__design_powergrid__drop__worst__net"):
                    if not ir_drop:
                        ir_drop = value
                    else:
                        ir_drop = max(value, ir_drop)

            if ir_drop is not None:
                self.record_metric("irdrop", ir_drop, source_file=get_metric_sources('irdrop'),
                                   source_unit="V")

            # setup wns and hold wns can be computed from setup slack and hold slack
            if 'sc__metric__timing__setup__ws' in metrics and \
                    has_timing and \
                    self.schema_metric.get('setupslack', step=self.step, index=self.index) \
                    is not None:
                wns = min(0.0, self.schema_metric.get('setupslack',
                                                      step=self.step, index=self.index))
                wns_units = self.schema_metric.get('setupslack', field='unit')
                self.record_metric("setupwns", wns, source_file=get_metric_sources('setupslack'),
                                   source_unit=wns_units)

            if 'sc__metric__timing__hold__ws' in metrics and \
                    has_timing and \
                    self.schema_metric.get('holdslack', step=self.step, index=self.index) \
                    is not None:
                wns = min(0.0, self.schema_metric.get('holdslack',
                                                      step=self.step, index=self.index))
                wns_units = self.schema_metric.get('holdslack', field='unit')
                self.record_metric("holdwns", wns, source_file=get_metric_sources('holdslack'),
                                   source_unit=wns_units)

            drvs = None
            for metric in [
                    'sc__metric__timing__drv__max_slew',
                    'sc__metric__timing__drv__max_cap',
                    'sc__metric__timing__drv__max_fanout',
                    'sc__metric__timing__drv__max_fanout',
                    'sc__metric__timing__drv__floating__nets',
                    'sc__metric__timing__drv__floating__pins',
                    'sc__metric__timing__drv__overdriven__nets',
                    'sc__metric__antenna__violating__nets',
                    'sc__metric__antenna__violating__pins']:
                if metric in metrics:
                    if drvs is None:
                        drvs = int(metrics[metric])
                    else:
                        drvs += int(metrics[metric])

            if drvs is not None:
                self.record_metric("drvs", drvs, source_file=get_metric_sources('drvs'))

            if 'sc__step__route__drc_errors' in metrics:
                self.record_metric("drcs", int(metrics['sc__step__route__drc_errors']),
                                   source_file=get_metric_sources('drcs'))

    def _generate_cell_area_report(self, ord_metrics):
        cellarea_report = CellArea()

        prefix = "sc__cellarea__design__instance"

        filtered_data = {}
        for key, value in ord_metrics.items():
            if key.startswith(prefix):
                filtered_data[key[len(prefix)+2:]] = value

        modules = set()
        modules.add("")
        for key in filtered_data.keys():
            if "__in_module:" in key:
                module = key[key.find("__in_module:"):]
                modules.add(module)

        def process_cell(group):
            data = {}
            for key, value in filtered_data.items():
                if (group != "" and key.endswith(group)):
                    key = key[:key.find("__in_module:")]
                    data[key] = value
                elif (group == "" and "__in_module" not in key):
                    data[key] = value

            cell_type = None
            cell_name = None

            if not group:
                cell_type = self.design_topmodule
                cell_name = self.design_topmodule
            else:
                cell_type = group[len("__in_module:"):]

            cellarea = None
            cellcount = None

            macroarea = None
            macrocount = None

            stdcell_types = (
                'tie_cell',
                'standard_cell',
                'buffer',
                'clock_buffer',
                'timing_repair_buffer',
                'inverter',
                'clock_inverter',
                'timing_Repair_inverter',
                'clock_gate_cell',
                'level_shifter_cell',
                'sequential_cell',
                'multi_input_combinational_cell',
                'other'
                )

            stdcell_info_area = []
            stdcell_info_count = []
            stdcellarea = None
            stdcellcount = None

            for key, value in data.items():
                if key == 'name':
                    cell_name = value
                elif key == 'count':
                    cellcount = value
                elif key == 'area':
                    cellarea = value
                elif key.startswith('count__class'):
                    _, cell_class = key.split(':')
                    if cell_class == 'macro':
                        macrocount = value
                    elif cell_class in stdcell_types:
                        stdcell_info_count.append(value)
                elif key.startswith('area__class'):
                    _, cell_class = key.split(':')
                    if cell_class == 'macro':
                        macroarea = value
                    elif cell_class in stdcell_types:
                        stdcell_info_area.append(value)

            if stdcell_info_count:
                stdcellcount = sum(stdcell_info_count)
            if stdcell_info_area:
                stdcellarea = sum(stdcell_info_area)

            cellarea_report.add_cell(
                name=cell_name,
                module=cell_type,
                cellarea=cellarea,
                cellcount=cellcount,
                macroarea=macroarea,
                macrocount=macrocount,
                stdcellarea=stdcellarea,
                stdcellcount=stdcellcount)

            if filtered_data:
                return True
            return False

        for module in modules:
            process_cell(module)

        if cellarea_report.size() > 0:
            cellarea_report.write_report("reports/hierarchical_cell_area.json")
