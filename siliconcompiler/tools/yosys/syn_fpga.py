import json

from typing import List

from siliconcompiler.tools.yosys import synth_post_process, setup as tool_setup
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric

from siliconcompiler.tools.yosys import YosysTask
from siliconcompiler import FPGASchema


class YosysFPGA(FPGASchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("yosys", "fpga_config", "file", "blah")
        self.define_tool_parameter("yosys", "macrolib", "[file]", "blah")
        self.define_tool_parameter("yosys", "extractlib", "[file]", "blah")
        self.define_tool_parameter("yosys", "dsp_techmap", "file", "blah")
        self.define_tool_parameter("yosys", "dsp_options", "[str]", "blah")
        self.define_tool_parameter("yosys", "memory_libmap", "file", "blah")
        self.define_tool_parameter("yosys", "memory_techmap", "file", "blah")
        self.define_tool_parameter("yosys", "flop_techmap", "file", "blah")
        self.define_tool_parameter("yosys", "feature_set",
                                   "{<mem_init,enable,async_reset,async_set>}", "blah")

        self.define_tool_parameter("yosys", "registers", "[str]", "blah")
        self.define_tool_parameter("yosys", "brams", "[str]", "blah")
        self.define_tool_parameter("yosys", "dsps", "[str]", "blah")

    def set_yosys_config(self, file: str, dataroot: str = None):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "yosys", "fpga_config", file)

    def add_yosys_macrolib(self, file: str, dataroot: str = None, clobber: bool = False):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            if clobber:
                return self.set("tool", "yosys", "macrolib", file)
            else:
                return self.add("tool", "yosys", "macrolib", file)

    def add_yosys_extractlib(self, file: str, dataroot: str = None, clobber: bool = False):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            if clobber:
                return self.set("tool", "yosys", "extractlib", file)
            else:
                return self.add("tool", "yosys", "extractlib", file)

    def set_yosys_dsptechmap(self, file: str, options: List[str] = None, dataroot: str = None):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            self.set("tool", "yosys", "dsp_techmap", file)
        if options:
            self.set("tool", "yosys", "dsp_options", options)

    def set_yosys_memorymap(self, libmap: str = None, techmap: str = None, dataroot: str = None):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            if libmap:
                self.set("tool", "yosys", "memory_libmap", libmap)
            if techmap:
                self.set("tool", "yosys", "memory_techmap", techmap)

    def set_yosys_flipfloptechmap(self, file: str = None, dataroot: str = None):
        if not dataroot:
            dataroot = self._get_active("package")
        with self.active_dataroot(dataroot):
            return self.set("tool", "yosys", "flop_techmap", file)

    def add_yosys_featureset(self, feature: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "yosys", "feature_set", feature)
        else:
            return self.add("tool", "yosys", "feature_set", feature)

    def add_yosys_registertype(self, name: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "yosys", "registers", name)
        else:
            return self.add("tool", "yosys", "registers", name)

    def add_yosys_bramtype(self, name: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "yosys", "brams", name)
        else:
            return self.add("tool", "yosys", "brams", name)

    def add_yosys_dsptype(self, name: str = None, clobber: bool = False):
        if clobber:
            return self.set("tool", "yosys", "dsps", name)
        else:
            return self.add("tool", "yosys", "dsps", name)


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
            "blah",
            "none")
        self.add_parameter(
            "synth_insert_buffers",
            "bool",
            "blah",
            True)

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
            filekeys = self.get_fileset_file_keys("systemverilog") + self.get_fileset_file_keys("verilog")
            if not filekeys:
                self.add_required_key("library", self.design_name, "fileset", self.schema().get("option", "fileset")[0], "file", "verilog")
            else:
                for key in filekeys:
                    self.add_required_key(*key)
                # TODO, mark required for define and params

        self.add_output_file(ext="vg")
        self.add_output_file(ext="netlist.json")
        self.add_output_file(ext="blif")

    def post_process(self):
        super().post_process()

        self._synthesis_post_process()

        fpga = self.schema().get("fpga", "device")

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
            if self.schema().valid("library", fpga, "tool", "yosys", "registers"):
                dff_cells = self.schema().get("library", fpga, "tool", "yosys", "registers")
            brams_cells = []
            if self.schema().valid("library", fpga, "tool", "yosys", "brams"):
                brams_cells = self.schema().get("library", fpga, "tool", "yosys", "brams")
            dsps_cells = []
            if self.schema().valid("library", fpga, "tool", "yosys", "dsps"):
                dsps_cells = self.schema().get("library", fpga, "tool", "yosys", "dsps")

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


######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    from siliconcompiler.targets import fpgaflow_demo
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    chip.use(fpgaflow_demo)


def setup(chip):
    '''
    Perform FPGA synthesis
    '''

    tool_setup(chip)

    # Generic synthesis task setup.
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', 'sc_synth_fpga.tcl',
             step=step, index=index, clobber=False)

    # Input/output requirements.
    chip.set('tool', tool, 'task', task, 'input', design + '.v', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.netlist.json', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.blif', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'use_slang', False,
             step=step, index=index,
             clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'use_slang',
             'true/false, if true will attempt to use the slang frontend',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'synth_fpga_opt_mode', 'none',
             step=step, index=index,
             clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'synth_fpga_opt_mode',
             'optimization mode for the synth_fpga command',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'synth_fpga_insert_buffers', True,
             step=step, index=index,
             clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'synth_fpga_insert_buffers',
             'insert buffers as part of the synth_fpga command',
             field='help')

    # Setup FPGA params
    part_name = chip.get('fpga', 'partname')

    # Require that a lut size is set for FPGA scripts.
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['fpga', part_name, 'lutsize']),
             step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_flop_techmap') and \
       chip.get('fpga', part_name, 'file', 'yosys_flop_techmap'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_flop_techmap']),
                 step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_dsp_techmap') and \
       chip.get('fpga', part_name, 'file', 'yosys_dsp_techmap'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_dsp_techmap']),
                 step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_extractlib') and \
       chip.get('fpga', part_name, 'file', 'yosys_extractlib'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_extractlib']),
                 step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_macrolib') and \
       chip.get('fpga', part_name, 'file', 'yosys_macrolib'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_macrolib']),
                 step=step, index=index)

    part_name = chip.get('fpga', 'partname')
    for resource in ('yosys_registers', 'yosys_brams', 'yosys_dsps'):
        if not chip.valid('fpga', part_name, 'var', resource):
            continue
        if not chip.get('fpga', part_name, 'var', resource):
            continue
        chip.add('tool', tool, 'task', task, 'require', f'fpga,{part_name},var,{resource}',
                 step=step, index=index)

    # Verify memory techmapping setup.  If a memory libmap
    # is provided a memory techmap verilog file is needed too
    if (chip.valid('fpga', part_name, 'file', 'yosys_memory_libmap') and
        chip.get('fpga', part_name, 'file', 'yosys_memory_libmap')) or \
        (chip.valid('fpga', part_name, 'file', 'yosys_memory_techmap') and
         chip.get('fpga', part_name, 'file', 'yosys_memory_techmap')):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_memory_libmap']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_memory_techmap']),
                 step=step, index=index)


##################################################
def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    part_name = chip.get('fpga', 'partname')

    synth_post_process(chip)

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
        if chip.valid('fpga', part_name, 'var', 'yosys_registers'):
            dff_cells = chip.get('fpga', part_name, 'var', 'yosys_registers')
        brams_cells = []
        if chip.valid('fpga', part_name, 'var', 'yosys_brams'):
            brams_cells = chip.get('fpga', part_name, 'var', 'yosys_brams')
        dsps_cells = []
        if chip.valid('fpga', part_name, 'var', 'yosys_dsps'):
            dsps_cells = chip.get('fpga', part_name, 'var', 'yosys_dsps')

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
            record_metric(chip, step, index, metric, value, "reports/stat.json")
