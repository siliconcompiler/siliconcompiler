import json

import os.path

from typing import Optional, Union, List

from siliconcompiler.tools.yosys.prepareLib import process_liberty_file
from siliconcompiler import sc_open
from siliconcompiler import utils
from siliconcompiler.asic import CellArea, ASICTask


from siliconcompiler.tools.yosys import YosysTask


class _ASICTask(ASICTask, YosysTask):
    def __init__(self):
        super().__init__()

        self.add_parameter(
            "synthesis_libraries",
            "[file]",
            "generated liberty files for use with synthesis for standard cell libraries",
            copy=False
        )
        self.add_parameter(
            "synthesis_corner",
            "{str}",
            "Timing corners to use for synthesis")

    def setup(self):
        super().setup()

        self.add_required_key("var", "synthesis_corner")
        self._determine_synthesis_corner()

        self.add_required_key("asic", "delaymodel")
        self.add_required_key("asic", "asiclib")

        delaymodel = self.project.get("asic", "delaymodel")
        for lib in self.project.get("asic", "asiclib"):
            lib_obj = self.project.get_library(lib)
            for corner in self.get("var", "synthesis_corner"):
                if lib_obj.get("asic", "libcornerfileset", corner, delaymodel):
                    self.add_required_key(lib_obj, "asic", "libcornerfileset", corner, delaymodel)
                    for fileset in lib_obj.get("asic", "libcornerfileset", corner, delaymodel):
                        self.add_required_key(lib_obj, "fileset", fileset, "file", "liberty")

    def _determine_synthesis_corner(self):
        if self.get("var", "synthesis_corner"):
            return

        # determine corner based on setup corner from constraints
        scenarios = self.project.get("constraint", "timing", field="schema")
        for scenario in scenarios.get_scenario().values():
            if not scenario.get_libcorner():
                continue
            if "setup" in scenario.get_check():
                self.add_yosys_synthesiscorner(scenario.get_libcorner())
                return

        if scenarios:
            # try getting it from first constraint with a valid libcorner
            for scenario in scenarios.get_scenario().values():
                if scenario.get_libcorner():
                    self.add_yosys_synthesiscorner(scenario.get_libcorner())
                    return

    def pre_process(self):
        super().pre_process()
        self._prepare_synthesis_libraries()

    def _prepare_synthesis_libraries(self):
        """
        mark cells dont use and format liberty files for yosys and abc
        """

        self.unset("var", "synthesis_libraries")
        delaymodel = self.project.get("asic", "delaymodel")

        # Generate synthesis_libraries for Yosys use
        fileset_map = []
        for lib in self.project.get("asic", "asiclib"):
            lib_obj = self.project.get_library(lib)
            for corner in self.get("var", "synthesis_corner"):
                for fileset in lib_obj.get("asic", "libcornerfileset", corner, delaymodel):
                    fileset_map.append((lib_obj, fileset))

        lib_file_map = {}
        processed = set()
        for lib, fileset in fileset_map:
            if (lib, fileset) in processed:
                continue
            processed.add((lib, fileset))
            lib_content = {}
            lib_map = {}
            # Mark dont use
            for lib_file in lib.find_files("fileset", fileset, "file", "liberty"):
                # Ensure a unique name is used for library
                lib_file_name_base = os.path.basename(lib_file)
                if lib_file_name_base.lower().endswith('.gz'):
                    lib_file_name_base = lib_file_name_base[0:-3]
                if lib_file_name_base.lower().endswith('.lib'):
                    lib_file_name_base = lib_file_name_base[0:-4]

                lib_file_name = lib_file_name_base
                unique_ident = 0
                while lib_file_name in lib_content:
                    lib_file_name = f'{lib_file_name_base}_{unique_ident}'
                    unique_ident += 1

                lib_content[lib_file_name] = process_liberty_file(
                    lib_file,
                    logger=self.logger
                )
                lib_map[lib_file_name] = lib_file

            if not lib_content:
                continue

            for file, content in lib_content.items():
                output_file = os.path.join(
                    self.nodeworkdir,
                    'inputs',
                    f'sc_{lib.name}_{file}.lib'
                )
                lib_file_map[lib_map[file]] = output_file

                with open(output_file, 'w') as f:
                    f.write(content)

                self.add("var", 'synthesis_libraries', output_file)

    def add_synthesis_corner(self, corner, step=None, index=None, clobber=True):
        """Deprecated"""
        import warnings
        warnings.warn(
            "add_synthesis_corner is deprecated. "
            "Please use add_yosys_synthesiscorner instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.add_yosys_synthesiscorner(corner, step=step, index=index, clobber=clobber)

    def add_yosys_synthesiscorner(self, corner: str,
                                  step: Optional[str] = None, index: Optional[str] = None,
                                  clobber: bool = False):
        """
        Adds a timing corner to use for synthesis.

        Args:
            corner (str): The name of the corner.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "synthesis_corner", corner, step=step, index=index)
        else:
            self.add("var", "synthesis_corner", corner, step=step, index=index)

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, ASIC
        from siliconcompiler.scheduler import SchedulerNode
        from siliconcompiler.targets import freepdk45_demo
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = ASIC(design)
        proj.add_fileset("docs")
        freepdk45_demo(proj)
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task


class ASICSynthesis(_ASICTask, YosysTask):
    '''
    Perform ASIC synthesis
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter(
            "use_slang",
            "bool",
            "true/false, if true will attempt to use the slang frontend",
            False)
        self.add_parameter(
            "autoname",
            "bool",
            "true/false, call autoname to rename wires based on registers",
            True)
        self.add_parameter(
            "add_buffers",
            "bool",
            "true/false, flag to indicate whether to add buffers or not.",
            True)
        self.add_parameter(
            "tie_undef",
            "<high,low,none>",
            "Flag to indicate how to handle undefined signals in netlist",
            "low")
        self.add_parameter(
            "add_tieoffs",
            "bool",
            "true/false, flag to indicate add tie high and tie low cells.",
            True)
        self.add_parameter(
            "opt_undriven",
            "bool",
            "true/false, flag to indicate if optimizations should mark undriven nets",
            True)

        self.__init_techmapping_parameter()
        self.__init_hierarchy_parameter()
        self.__init_moosic_parameter()
        self.__init_clockgates_parameter()
        self.__init_abc_parameter()

    def __init_techmapping_parameter(self):
        self.add_parameter(
            "map_adders",
            "bool",
            "true/false, techmap adders in Yosys")
        self.add_parameter(
            "memory_libmap",
            "file",
            "File used to map memories with yosys")
        self.add_parameter(
            "memory_techmap",
            "file",
            "File used to techmap memories with yosys")

        self.set_dataroot("yosys-techmaps", __file__)
        self.add_parameter(
            "synth_extra_map",
            "[file]",
            "Files used in synthesis to perform additional techmapping",
            "techmaps/lcu_kogge_stone.v",
            dataroot="yosys-techmaps")

    def __init_hierarchy_parameter(self):
        self.add_parameter(
            "preserve_modules",
            "[str]",
            "List of modules in input files to prevent flatten from \"flattening\"")
        self.add_parameter(
            "blackbox_modules",
            "[str]",
            "List of modules in input files to exclude from synthesis by replacing "
            "them with empty blackboxes")

        self.add_parameter(
            "flatten",
            "bool",
            "true/false, invoke synth with the -flatten option",
            True)
        self.add_parameter(
            "auto_flatten",
            "bool",
            "true/false, attempt to determine how to flatten the design",
            True)
        self.add_parameter(
            "hier_threshold",
            "int",
            "Instance limit for the number of cells in a module to preserve.",
            1000)
        self.add_parameter(
            "hierarchy_separator",
            "str",
            "control the hierarchy separator used during design flattening",
            "/")

    def __init_abc_parameter(self):
        self.add_parameter(
            "strategy",
            "<DELAY0,DELAY1,DELAY2,DELAY3,DELAY4,AREA0,AREA1,AREA2,AREA3>",
            "ABC synthesis strategy")
        self.add_parameter(
            "abc_constraint_driver",
            "str",
            "Buffer that drives the abc techmapping, defaults to first buffer specified")
        self.add_parameter(
            "abc_constraint_file",
            "file",
            "File used to pass in constraints to abc",
            copy=False)
        self.add_parameter(
            "abc_clock_period",
            "float",
            "Clock period to use for synthesis in ps, if more than one clock is specified, the "
            "smallest period is used.",
            unit="ps")
        self.add_parameter(
            "abc_constraint_load",
            "float",
            "Capacitive load for the abc techmapping in fF, if not specified it will not be used.",
            unit="fF")
        self.add_parameter(
            "abc_clock_derating",
            "float",
            "Derating to apply to the clock period for abc synthesis",
            defvalue=0
        )

    def __init_clockgates_parameter(self):
        self.add_parameter(
            "map_clockgates",
            "bool",
            "Map clockgates during synthesis.",
            False)
        self.add_parameter(
            "min_clockgate_fanout",
            "int",
            "Minimum clockgate fanout.",
            8)

    def __init_moosic_parameter(self):
        self.add_parameter(
            "lock_design",
            "bool",
            "true/false, if true will attempt to lock the design with moosic",
            False)
        self.add_parameter(
            "lock_design_key",
            "str",
            "lock locking key")
        self.add_parameter(
            "lock_design_port",
            "str",
            "lock locking port name")

    def set_yosys_useslang(self, enable: bool,
                           step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables using the slang frontend.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "use_slang", enable, step=step, index=index)

    def set_yosys_autoname(self, enable: bool,
                           step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables renaming wires based on registers.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "autoname", enable, step=step, index=index)

    def set_yosys_tieundefined(self, tie: str,
                               step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets how to handle undefined signals in the netlist.

        Args:
            tie (str): The tie strategy ('high', 'low', 'none').
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "tie_undef", tie, step=step, index=index)

    def set_yosys_addtiecells(self, enable: bool,
                              step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables adding tie high and tie low cells.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "add_tieoffs", enable, step=step, index=index)

    def set_yosys_addbuffers(self, enable: bool,
                             step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables adding buffers.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "add_buffers", enable, step=step, index=index)

    def set_yosys_optundriven(self, enable: bool,
                              step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables marking undriven nets during optimization.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "opt_undriven", enable, step=step, index=index)

    def set_yosys_mapadders(self, enable: bool,
                            step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables techmapping adders in Yosys.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "map_adders", enable, step=step, index=index)

    def set_yosys_memorylibmap(self, file: str,
                               step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the file used to map memories with Yosys.

        Args:
            file (str): The path to the library map file.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "memory_libmap", file, step=step, index=index)

    def set_yosys_memorytechmap(self, file: str,
                                step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the file used to techmap memories with Yosys.

        Args:
            file (str): The path to the technology map file.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "memory_techmap", file, step=step, index=index)

    def add_yosys_synthextramap(self, map: Union[str, List[str]],
                                step: Optional[str] = None, index: Optional[str] = None,
                                clobber: bool = False):
        """
        Adds files used in synthesis to perform additional techmapping.

        Args:
            map (Union[str, List[str]]): The map file(s) to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "synth_extra_map", map, step=step, index=index)
        else:
            self.add("var", "synth_extra_map", map, step=step, index=index)

    def add_yosys_preservemodules(self, modules: Union[str, List[str]],
                                  step: Optional[str] = None, index: Optional[str] = None,
                                  clobber: bool = False):
        """
        Adds modules to prevent flattening.

        Args:
            modules (Union[str, List[str]]): The module name(s) to preserve.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "preserve_modules", modules, step=step, index=index)
        else:
            self.add("var", "preserve_modules", modules, step=step, index=index)

    def add_yosys_blackboxmodules(self, modules: Union[str, List[str]],
                                  step: Optional[str] = None, index: Optional[str] = None,
                                  clobber: bool = False):
        """
        Adds modules to exclude from synthesis by replacing them with empty blackboxes.

        Args:
            modules (Union[str, List[str]]): The module name(s) to blackbox.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "blackbox_modules", modules, step=step, index=index)
        else:
            self.add("var", "blackbox_modules", modules, step=step, index=index)

    def set_yosys_flatten(self, enable: bool,
                          step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables invoking synth with the -flatten option.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "flatten", enable, step=step, index=index)

    def set_yosys_autoflatten(self, enable: bool,
                              step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables attempting to determine how to flatten the design.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "auto_flatten", enable, step=step, index=index)

    def set_yosys_hierthreshold(self, threshold: int,
                                step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the instance limit for the number of cells in a module to preserve.

        Args:
            threshold (int): The instance limit.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "hier_threshold", threshold, step=step, index=index)

    def set_yosys_hierarchyseparator(self, separator: str,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the hierarchy separator used during design flattening.

        Args:
            separator (str): The separator character.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "hierarchy_separator", separator, step=step, index=index)

    def set_yosys_strategy(self, strategy: str,
                           step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the ABC synthesis strategy.

        Args:
            strategy (str): The strategy name (e.g., 'DELAY1', 'AREA2').
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "strategy", strategy, step=step, index=index)

    def set_yosys_abcconstraintdriver(self, driver: str,
                                      step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the buffer that drives the ABC techmapping.

        Args:
            driver (str): The driver cell name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "abc_constraint_driver", driver, step=step, index=index)

    def set_yosys_abcclockperiod(self, period: float,
                                 step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the clock period to use for synthesis.

        Args:
            period (float): The clock period in ps.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "abc_clock_period", period, step=step, index=index)

    def set_yosys_abcconstraintload(self, load: float,
                                    step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the capacitive load for the ABC techmapping.

        Args:
            load (float): The load in fF.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "abc_constraint_load", load, step=step, index=index)

    def set_yosys_abcclockderating(self, derating: float,
                                   step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the derating to apply to the clock period for ABC synthesis.

        Args:
            derating (float): The derating factor.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "abc_clock_derating", derating, step=step, index=index)

    def set_yosys_mapclockgates(self, enable: bool,
                                step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables mapping clockgates during synthesis.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "map_clockgates", enable, step=step, index=index)

    def set_yosys_minclockgatefanout(self, fanout: int,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the minimum clockgate fanout.

        Args:
            fanout (int): The minimum fanout.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "min_clockgate_fanout", fanout, step=step, index=index)

    def set_yosys_lockdesign(self, enable: bool,
                             step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables attempting to lock the design with moosic.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "lock_design", enable, step=step, index=index)

    def set_yosys_lockdesignkey(self, key: str,
                                step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the lock locking key.

        Args:
            key (str): The key.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "lock_design_key", key, step=step, index=index)

    def set_yosys_lockdesignport(self, port: str,
                                 step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the lock locking port name.

        Args:
            port (str): The port name.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "lock_design_port", port, step=step, index=index)

    def task(self):
        return "syn_asic"

    def setup(self):
        super().setup()

        self.set_script("sc_synth_asic.tcl")

        self.add_required_key("asic", "mainlib")

        design = self.project.design
        fileset = self.project.get("option", "fileset")[0]

        if f"{self.design_topmodule}.v" in self.get_files_from_input_nodes():
            self.add_input_file(ext="v")
            self.set("input", f"{self.design_topmodule}.v")
        elif f"{self.design_topmodule}.sv" in self.get_files_from_input_nodes():
            self.add_input_file(ext="sv")
        else:
            filekeys = self.get_fileset_file_keys("systemverilog") + \
                self.get_fileset_file_keys("verilog")
            if not filekeys:
                self.add_required_key(design, "fileset", fileset, "file", "verilog")
            else:
                for obj, key in filekeys:
                    self.add_required_key(obj, *key)

        for param in design.getkeys("fileset", fileset, "param"):
            self.add_required_key(design, "fileset", fileset, "param", param)

        self.add_output_file(ext="vg", clobber=True)
        self.add_output_file(ext="netlist.json")

        mainlib = self.project.get_library(self.project.get("asic", "mainlib"))

        if self.get('var', 'abc_constraint_driver') is not None:
            self.add_required_key("var", "abc_constraint_driver")
        else:
            lib_driver = mainlib.get("tool", "yosys", "driver_cell")
            if lib_driver:
                self.add_required_key(mainlib, "tool", "yosys", "driver_cell")
                self.add_required_key("var", "abc_constraint_driver")
                self.set("var", "abc_constraint_driver", lib_driver)
        if self.get("var", "abc_clock_period"):
            self.add_required_key("var", "abc_clock_period")
        else:
            self.add_required_key(mainlib, "tool", "yosys", "abc_clock_multiplier")
            self.add_required_key("var", "abc_clock_derating")
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="sdc"):
                    self.add_required_key(lib, "fileset", fileset, "file", "sdc")

        if mainlib.get("tool", "yosys", "tristatebuffermap"):
            self.add_required_key(mainlib, "tool", "yosys", "tristatebuffermap")
        if mainlib.get("tool", "yosys", "techmap"):
            self.add_required_key(mainlib, "tool", "yosys", "techmap")

        self.add_required_key("var", "map_adders")
        if self.get("var", "map_adders"):
            if mainlib.get("tool", "yosys", "addermap"):
                self.add_required_key(mainlib, "tool", "yosys", "addermap")
            else:
                self.set("var", "map_adders", False)

        if self.get("var", "memory_libmap"):
            self.add_required_key("var", "memory_libmap")
        if self.get("var", "memory_techmap"):
            self.add_required_key("var", "memory_techmap")

        if self.get("var", "synth_extra_map"):
            self.add_required_key("var", "synth_extra_map")

        if self.get("var", "preserve_modules"):
            self.add_required_key("var", "preserve_modules")
        if self.get("var", "blackbox_modules"):
            self.add_required_key("var", "blackbox_modules")

        self.add_required_key("var", "use_slang")
        self.add_required_key("var", "add_buffers")
        self.add_required_key("var", "tie_undef")
        self.add_required_key("var", "add_tieoffs")
        self.add_required_key("var", "opt_undriven")
        self.add_required_key("var", "flatten")
        self.add_required_key("var", "auto_flatten")
        self.add_required_key("var", "hier_threshold")
        self.add_required_key("var", "hierarchy_separator")

        if self.get("var", "strategy"):
            self.add_required_key("var", "strategy")

        self.add_required_key("var", "map_clockgates")
        self.add_required_key("var", "min_clockgate_fanout")

        self.add_required_key("var", "lock_design")
        if self.get("var", "lock_design"):
            self.add_required_key("var", "lock_design_key")
            self.add_required_key("var", "lock_design_port")

    def pre_process(self):
        super().pre_process()

        self.set("var", "abc_constraint_file",
                 os.path.join(self.nodeworkdir,
                              "inputs",
                              "sc_abc.constraints"))

        abc_clock_period = self._get_abc_period()
        if abc_clock_period:
            self.set("var", "abc_clock_period", abc_clock_period)

        self._create_abc_synthesis_constraints()

    def _get_abc_period(self):
        abc_clock_period = self.get('var', 'abc_clock_period')
        if abc_clock_period is not None:
            return abc_clock_period

        period = self._get_clock_period()
        if period is None:
            return None

        period *= 1000

        abc_clock_derating = self.get('var', 'abc_clock_derating')
        if abc_clock_derating is not None:
            if abc_clock_derating > 1:
                self.logger.warning("abc_clock_derating is greater than 1.0")
            elif abc_clock_derating >= 0:
                period *= (1.0 - abc_clock_derating)
            else:
                self.logger.error("abc_clock_derating is negative")

        return period

    def _get_clock_period(self):
        mainlib = self.project.get("asic", "mainlib")
        clock_units_multiplier = self.project.get_library(mainlib).get(
            "tool", "yosys", "abc_clock_multiplier") / 1000

        _, period = self.get_clock()
        if period is not None:
            period *= clock_units_multiplier

        return period

    def _create_abc_synthesis_constraints(self):
        abc_driver = self.get('var', 'abc_constraint_driver')
        abc_load = self.get('var', 'abc_constraint_load')

        if abc_driver is None and abc_load is None:
            # neither is set so nothing to do
            return

        with open(self.get("var", "abc_constraint_file"), "w") as f:
            abc_template = utils.get_file_template(
                'abc.const',
                root=os.path.join(os.path.dirname(__file__), 'templates'))
            f.write(abc_template.render(abc_driver=abc_driver, abc_load=abc_load))

    def post_process(self):
        super().post_process()
        self._synthesis_post_process()
        self._generate_cell_area_report()

    def _generate_cell_area_report(self):
        stat_json = "reports/stat.json"
        netlist = f"outputs/{self.design_topmodule}.netlist.json"
        if not os.path.exists(stat_json):
            return
        if not os.path.exists(netlist):
            return

        # Load data
        with sc_open(stat_json) as fd:
            stat = json.load(fd)
        with sc_open(netlist) as fd:
            netlist = json.load(fd)

        modules = []
        for module in stat["modules"].keys():
            if module[0] == "\\":
                modules.append(module[1:])

        cellarea_report = CellArea()

        def get_area_count(module):
            if f"\\{module}" not in stat["modules"]:
                return 0.0, 0
            info = stat["modules"][f"\\{module}"]

            count = info["num_cells"]
            area = 0.0
            if "area" in info:
                area = info["area"]

            for cell, inst_count in info["num_cells_by_type"].items():
                cell_area, cell_count = get_area_count(cell)

                count += cell_count * inst_count
                if cell_count > 0:
                    count -= inst_count
                area += cell_area * inst_count

            return area, count

        def handle_heir(level_info, prefix):
            cells = list(level_info["cells"])

            for cell in cells:
                cell_type = level_info["cells"][cell]["type"]
                if cell_type in modules:
                    area, count = get_area_count(cell_type)
                    cellarea_report.add_cell(
                        name=f"{prefix}{cell}",
                        module=cell_type,
                        cellcount=count,
                        cellarea=area)
                    handle_heir(netlist["modules"][cell_type], f"{prefix}{cell}.")

        count = stat["design"]["num_cells"]
        area = 0.0
        if "area" in stat["design"]:
            area = stat["design"]["area"]
        cellarea_report.add_cell(
            name=self.design_topmodule,
            module=self.design_topmodule,
            cellarea=area,
            cellcount=count
        )

        handle_heir(netlist["modules"][self.design_topmodule], "")

        if cellarea_report.size() > 0:
            cellarea_report.write_report("reports/hierarchical_cell_area.json")
