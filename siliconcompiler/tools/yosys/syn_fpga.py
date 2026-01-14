import json

from typing import Optional

from siliconcompiler import sc_open

from siliconcompiler.tools.yosys import YosysTask


class FPGASynthesis(YosysTask):
    def __init__(self):
        super().__init__()

        self.add_parameter(
            "use_slang",
            "bool",
            "true/false, if true will attempt to use the slang frontend",
            False)
        self.add_parameter(
            "synth_opt_mode",
            "<none,delay,area>",
            "optimization mode: 'none' for a balanced optimization, 'delay' to"
            " prioritize path delay, 'area' to prioritize utilization",
            "none")
        self.add_parameter(
            "synth_insert_buffers",
            "bool",
            "perform buffer insertion",
            True)

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

    def set_yosys_synthoptmode(self, mode: str,
                               step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the optimization mode for synthesis.

        Args:
            mode (str): The optimization mode ('none', 'delay', 'area').
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "synth_opt_mode", mode, step=step, index=index)

    def set_yosys_synthinsertbuffers(self, enable: bool,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables buffer insertion during synthesis.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "synth_insert_buffers", enable, step=step, index=index)

    def task(self):
        return "syn_fpga"

    def setup(self):
        super().setup()

        self.set_script("sc_synth_fpga.tcl")

        if f"{self.design_topmodule}.v" in self.get_files_from_input_nodes():
            self.set("input", f"{self.design_topmodule}.v")
        elif f"{self.design_topmodule}.sv" in self.get_files_from_input_nodes():
            self.set("input", f"{self.design_topmodule}.sv")
        else:
            filekeys = self.get_fileset_file_keys("systemverilog") + \
                self.get_fileset_file_keys("verilog")
            if not filekeys:
                self.add_required_key("library", self.design_name, "fileset",
                                      self.project.get("option", "fileset")[0], "file", "verilog")
            else:
                for lib, key in filekeys:
                    self.add_required_key(lib, *key)
                # TODO, mark required for define and params

        self.add_output_file(ext="vg")
        self.add_output_file(ext="netlist.json")
        self.add_output_file(ext="blif")

        self.add_required_key("var", "use_slang")

    def post_process(self):
        super().post_process()

        self._synthesis_post_process()

        fpga = self.project.get_library(self.project.get("fpga", "device"))

        with sc_open("reports/stat.json") as f:
            metrics = json.load(f)
            if "design" in metrics:
                metrics = metrics["design"]
            else:
                return

            if "num_cells_by_type" in metrics:
                metrics = metrics["num_cells_by_type"]
            else:
                return

            dff_cells = []
            if fpga.valid("tool", "yosys", "registers"):
                dff_cells = fpga.get("tool", "yosys", "registers")
            brams_cells = []
            if fpga.valid("tool", "yosys", "brams"):
                brams_cells = fpga.get("tool", "yosys", "brams")
            dsps_cells = []
            if fpga.valid("tool", "yosys", "dsps"):
                dsps_cells = fpga.get("tool", "yosys", "dsps")
            data = {
                "registers": 0,
                "luts": 0,
                "dsps": 0,
                "brams": 0
            }
            for cell, count in metrics.items():
                if cell == "$lut":
                    data["luts"] += count
                elif cell in dff_cells:
                    data["registers"] += count
                elif cell in dsps_cells:
                    data["dsps"] += count
                elif cell in brams_cells:
                    data["brams"] += count

            for metric, value in data.items():
                self.record_metric(metric, value, source_file="reports/stat.json")
