'''
Yosys is a framework for RTL synthesis that takes synthesizable
Verilog-2005 design and converts it to BLIF, EDIF, BTOR, SMT,
Verilog netlist etc. The tool supports logical synthesis and
tech mapping to ASIC standard cell libraries, FPGA architectures.
In addition it has built in formal methods for property and
equivalence checking.

Documentation: https://yosyshq.readthedocs.io/projects/yosys/en/latest/

Sources: https://github.com/YosysHQ/yosys

Installation: https://github.com/YosysHQ/yosys
'''
import json
import os
import re

from typing import List, Union

from siliconcompiler import sc_open

from siliconcompiler import StdCellLibrary
from siliconcompiler import FPGADevice
from siliconcompiler import Task


class YosysStdCellLibrary(StdCellLibrary):
    """
    Schema for a standard cell library specifically for the Yosys tool.

    This class extends the base StdCellLibrary to define and manage
    a variety of tool-specific parameters required by Yosys for synthesis
    and technology mapping.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("yosys", "abc_clock_multiplier", "float",
                                   "Scalar factor to convert timing from library units to ns "
                                   "for ABC.")
        self.define_tool_parameter("yosys", "abc_constraint_load", "float",
                                   "The load constraint for the ABC tool", unit="fF")

        self.define_tool_parameter("yosys", "driver_cell", "str",
                                   "The name of the driver cell to be used.")
        self.define_tool_parameter("yosys", "buffer_cell", "(str,str,str)",
                                   "A tuple specifying the buffer cell name, its input port, and "
                                   "its output port.")
        self.define_tool_parameter("yosys", "tiehigh_cell", "(str,str)",
                                   "A tuple specifying the tie-high cell name and its output port.")
        self.define_tool_parameter("yosys", "tielow_cell", "(str,str)",
                                   "A tuple specifying the tie-low cell name and its output port.")

        self.define_tool_parameter("yosys", "techmap", "[file]",
                                   "A list of technology map files to be used by Yosys.")
        self.define_tool_parameter("yosys", "tristatebuffermap",
                                   "file", "The file to be used for tristate buffer mapping.")
        self.define_tool_parameter("yosys", "addermap", "file",
                                   "The file to be used for adder mapping.")

        self.define_tool_parameter("yosys", "synthesis_fileset", "[str]",
                                   "name of the filesets to use for yosys synthesis")
        self.define_tool_parameter("yosys", "blackbox_fileset", "[str]",
                                   "A list of fileset names that contain blackbox definitions.")

    def set_yosys_driver_cell(self, cell: str):
        """
        Sets the driver cell for Yosys synthesis.

        Args:
            cell (str): The name of the driver cell.
        """
        self.set("tool", "yosys", "driver_cell", cell)

    def set_yosys_buffer_cell(self, cell: str, input_port: str, output_port: str):
        """
        Sets the buffer cell and its corresponding input and output ports.

        Args:
            cell (str): The name of the buffer cell.
            input_port (str): The name of the input port.
            output_port (str): The name of the output port.
        """
        self.set("tool", "yosys", "buffer_cell", (cell, input_port, output_port))

    def set_yosys_tiehigh_cell(self, cell: str, output_port: str):
        """
        Sets the tie-high cell and its output port.

        Args:
            cell (str): The name of the tie-high cell.
            output_port (str): The name of the output port.
        """
        self.set("tool", "yosys", "tiehigh_cell", (cell, output_port))

    def set_yosys_tielow_cell(self, cell: str, output_port: str):
        """
        Sets the tie-low cell and its output port.

        Args:
            cell (str): The name of the tie-low cell.
            output_port (str): The name of the output port.
        """
        self.set("tool", "yosys", "tielow_cell", (cell, output_port))

    def set_yosys_abc(self, clock_multiplier: float, load: float):
        """
        Sets the clock multiplier and load constraints for the Yosys ABC tool.

        Args:
            clock_multiplier (float): The scalar clock multiplier.
            load (float): The constraint load in fF.
        """
        self.set("tool", "yosys", "abc_clock_multiplier", clock_multiplier)
        self.set("tool", "yosys", "abc_constraint_load", load)

    def set_yosys_tristatebuffer_map(self, map: str, dataroot: str = None):
        """
        Sets the file path for the tristate buffer mapping.

        Args:
            map (str): The file path for the mapping.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("tool", "yosys", "tristatebuffermap", map)

    def set_yosys_adder_map(self, map: str, dataroot: str = None):
        """
        Sets the file path for the adder mapping.

        Args:
            map (str): The file path for the mapping.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("tool", "yosys", "addermap", map)

    def add_yosys_tech_map(self,
                           map: Union[str, List[str]],
                           dataroot: str = None,
                           clobber: bool = False):
        """
        Adds a technology map file to the list of maps.

        Args:
            map (Union[str, List[str]]): The file path or a list of file paths for the technology
                                         map.
            dataroot (str, optional): The data root directory. Defaults to the active package.
            clobber (bool, optional): If True, replaces the current value. Defaults to False.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("tool", "yosys", "techmap", map)
            else:
                self.add("tool", "yosys", "techmap", map)

    def add_yosys_synthesis_fileset(self, fileset: Union[str, List[str]], clobber: bool = False):
        """
        Adds a fileset name to the list of synthesis filesets.

        Args:
            fileset (Union[str, List[str]]): The name of the fileset or a list of fileset names.
            clobber (bool, optional): If True, replaces the current value. Defaults to False.
        """
        if clobber:
            self.set("tool", "yosys", "synthesis_fileset", fileset)
        else:
            self.add("tool", "yosys", "synthesis_fileset", fileset)

    def add_yosys_blackbox_fileset(self, fileset: Union[str, List[str]], clobber: bool = False):
        """
        Adds a fileset name to the list of blackbox filesets.

        Args:
            fileset (Union[str, List[str]]): The name of the fileset or a list of fileset names.
            clobber (bool, optional): If True, replaces the current value. Defaults to False.
        """
        if clobber:
            self.set("tool", "yosys", "blackbox_fileset", fileset)
        else:
            self.add("tool", "yosys", "blackbox_fileset", fileset)


class YosysFPGA(FPGADevice):
    """
    Schema for defining FPGA-specific parameters for the Yosys tool.

    This class extends the base FPGADevice to manage various configurations
    and technology-specific files required for synthesizing designs onto
    an FPGA using Yosys, including macro libraries, technology maps, and
    feature sets.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("yosys", "fpga_config", "file",
                                   "The main configuration file for the target FPGA.")
        self.define_tool_parameter("yosys", "macrolib", "[file]",
                                   "A list of macro library files to be used.")
        self.define_tool_parameter("yosys", "dsp_techmap", "file",
                                   "The technology map file for DSP blocks.")
        self.define_tool_parameter("yosys", "dsp_options", "{str}",
                                   "A list of synthesis options for DSP blocks.")
        self.define_tool_parameter("yosys", "memory_libmap", "file",
                                   "The library map file for memory elements.")
        self.define_tool_parameter("yosys", "memory_techmap", "file",
                                   "The technology map file for memory elements.")
        self.define_tool_parameter("yosys", "flop_techmap", "file",
                                   "The technology map file for flip-flop elements.")
        self.define_tool_parameter("yosys", "feature_set",
                                   "{<mem_init,enable,async_reset,async_set>}",
                                   "The set of supported features for the FPGA.")

        self.define_tool_parameter("yosys", "registers", "{str}",
                                   "A list of supported register types.")
        self.define_tool_parameter("yosys", "brams", "{str}",
                                   "A list of supported block RAM types.")
        self.define_tool_parameter("yosys", "dsps", "{str}",
                                   "A list of supported DSP types.")

    def set_yosys_config(self, file: str, dataroot: str = None):
        """
        Sets the main FPGA configuration file.

        Args:
            file (str): The path to the configuration file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("tool", "yosys", "fpga_config", file)

    def add_yosys_macrolib(self, file: Union[str, List[str]], dataroot: str = None,
                           clobber: bool = False):
        """
        Adds a macro library file.

        Args:
            file (Union[str, List[str]]): The path to the macro library file or a list of paths.
            dataroot (str, optional): The data root directory. Defaults to the active package.
            clobber (bool, optional): If True, overwrites the existing list with the new file(s).
                                      If False, appends the file(s) to the list. Defaults to False.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                return self.set("tool", "yosys", "macrolib", file)
            else:
                return self.add("tool", "yosys", "macrolib", file)

    def set_yosys_dsptechmap(self, file: str, options: List[str] = None, dataroot: str = None):
        """
        Sets the technology map file and optional synthesis options for DSP blocks.

        Args:
            file (str): The path to the DSP technology map file.
            options (List[str], optional): A list of synthesis options for DSP blocks.
                Defaults to None.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("tool", "yosys", "dsp_techmap", file)
        if options:
            self.set("tool", "yosys", "dsp_options", options)

    def set_yosys_memorymap(self, libmap: str = None, techmap: str = None, dataroot: str = None):
        """
        Sets the library and technology map files for memory elements.

        Args:
            libmap (str, optional): The path to the memory library map file. Defaults to None.
            techmap (str, optional): The path to the memory technology map file. Defaults to None.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if libmap:
                self.set("tool", "yosys", "memory_libmap", libmap)
            if techmap:
                self.set("tool", "yosys", "memory_techmap", techmap)

    def set_yosys_flipfloptechmap(self, file: str = None, dataroot: str = None):
        """
        Sets the technology map file for flip-flops.

        Args:
            file (str, optional): The path to the flip-flop technology map file. Defaults to None.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("tool", "yosys", "flop_techmap", file)

    def add_yosys_featureset(self, feature: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds a feature to the feature set.

        Args:
            feature (Union[str, List[str]], optional): The name of the feature or a list of feature
                                                       names to add. Defaults to None.
            clobber (bool, optional): If True, overwrites the existing set with the new feature(s).
                                      If False, adds the feature(s) to the set. Defaults to False.
        """
        if clobber:
            return self.set("tool", "yosys", "feature_set", feature)
        else:
            return self.add("tool", "yosys", "feature_set", feature)

    def add_yosys_registertype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds a register type to the list of supported registers.

        Args:
            name (Union[str, List[str]], optional): The name of the register type or a list
                                                    of types. Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list with the new type(s).
                                      If False, adds the type(s) to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "yosys", "registers", name)
        else:
            return self.add("tool", "yosys", "registers", name)

    def add_yosys_bramtype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds a block RAM type to the list of supported BRAMs.

        Args:
            name (Union[str, List[str]], optional): The name of the BRAM type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list with the new type(s).
                                      If False, adds the type(s) to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "yosys", "brams", name)
        else:
            return self.add("tool", "yosys", "brams", name)

    def add_yosys_dsptype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds a DSP type to the list of supported DSPs.

        Args:
            name (Union[str, List[str]], optional): The name of the DSP type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list with the new type(s).
                                      If False, adds the type(s) to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "yosys", "dsps", name)
        else:
            return self.add("tool", "yosys", "dsps", name)


class YosysTask(Task):
    def tool(self):
        return "yosys"

    def setup(self):
        super().setup()

        self.set_exe("yosys", vswitch="--version", format="tcl")
        self.add_version(">=0.48")

        if self.has_breakpoint():
            self.add_commandline_option("-C")
        self.add_commandline_option("-c")

        self.set_dataroot("siliconcompiler-yosys", __file__)

        with self.active_dataroot("siliconcompiler-yosys"):
            self.set_refdir("scripts")

        self.add_regex("warnings", "Warning:")
        self.add_regex("errors", "^ERROR")

    def parse_version(self, stdout):
        # Yosys 0.9+3672 (git sha1 014c7e26, gcc 7.5.0-3ubuntu1~18.04 -fPIC -Os)
        return stdout.split()[1]

    def normalize_version(self, version):
        # Replace '+', which represents a "local version label", with '-', which is
        # an "implicit post release number".
        return version.replace('+', '-')

    def _synthesis_post_process(self):
        stat_json = "reports/stat.json"
        if os.path.exists(stat_json):
            with sc_open(stat_json) as f:
                metrics = json.load(f)
                if "design" in metrics:
                    metrics = metrics["design"]

                if "area" in metrics:
                    self.record_metric("cellarea", float(metrics["area"]),
                                       source_file=stat_json, source_unit="um^2")
                if "num_cells" in metrics:
                    self.record_metric("cells", metrics["num_cells"],
                                       source_file=stat_json)
                if "num_wire_bits" in metrics:
                    self.record_metric("nets", metrics["num_wire_bits"],
                                       source_file=stat_json)
                if "num_port_bits" in metrics:
                    self.record_metric("pins", float(metrics["num_port_bits"]),
                                       source_file=stat_json)
        else:
            self.logger.warning("Yosys cell statistics are missing")

        registers = None
        with sc_open(self.get_logpath("exe")) as f:
            for line in f:
                line_registers = re.findall(r"^\s*mapped ([0-9]+) \$_DFF.*", line)
                if line_registers:
                    if registers is None:
                        registers = 0
                    registers += int(line_registers[0])
        if registers is not None:
            self.record_metric("registers", registers, source_file=self.get_logpath("exe"))
