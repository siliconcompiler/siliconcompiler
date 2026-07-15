import re

import os.path

from typing import Optional

from siliconcompiler import sc_open

from siliconcompiler.tools.opensta import OpenSTATask

from siliconcompiler import TaskSkip


class TimingTaskBase(OpenSTATask):
    '''
    Base class for generating static timing reports.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("top_n_paths", "int<1..>", "number of paths to report timing for",
                           defvalue=10)
        self.add_parameter("unique_path_groups_per_clock", "bool",
                           "if true will generate separate path groups per clock", defvalue=False)
        self.add_parameter("timing_mode", "str", "timing mode to use")

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")
        self.add_parameter("opensta_generic_sdc", "file", "generic opensta SDC file",
                           defvalue="tools/_common/sdc/sc_constraints.sdc",
                           dataroot="siliconcompiler")

        self.add_parameter("write_sdf", "bool", "if true will write sdf for every corner",
                           defvalue=False)
        self.add_parameter("write_liberty", "bool", "if true will write liberty for every corner",
                           defvalue=False)

        self.add_parameter("power_activities", "[(str,str,str)]",
                           "list of (VCD scope, library, fileset) tuples specifying VCD files to "
                           "read for vector-based power analysis. The scope is the instance path "
                           "of the design top within the VCD. If empty, a VCD is read from the "
                           "active filesets (or the step input) with no scope.")

    def set_opensta_topnpaths(self, n: int,
                              step: Optional[str] = None,
                              index: Optional[str] = None):
        """
        Sets the number of paths to report timing for.

        Args:
            n (int): The number of paths.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "top_n_paths", n, step=step, index=index)

    def set_opensta_uniquepathgroupsperclock(self, enable: bool,
                                             step: Optional[str] = None,
                                             index: Optional[str] = None):
        """
        Enables or disables generating separate path groups per clock.

        Args:
            enable (bool): Whether to enable unique path groups per clock.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "unique_path_groups_per_clock", enable, step=step, index=index)

    def set_opensta_timingmode(self, mode: str,
                               step: Optional[str] = None, index: Optional[str] = None):
        """
        Sets the timing mode to use.

        Args:
            mode (str): The timing mode to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "timing_mode", mode, step=step, index=index)

    def set_opensta_writesdf(self, enable: bool,
                             step: Optional[str] = None,
                             index: Optional[str] = None):
        """
        Enables or disables writing SDF files for every corner.

        Args:
            enable (bool): Whether to enable writing SDF files.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "write_sdf", enable, step=step, index=index)

    def set_opensta_writeliberty(self, enable: bool,
                                 step: Optional[str] = None,
                                 index: Optional[str] = None):
        """
        Enables or disables writing liberty files for every corner.

        Args:
            enable (bool): Whether to enable writing liberty files.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "write_liberty", enable, step=step, index=index)

    def add_opensta_poweractivity(self, scope: str, library: str, fileset: str,
                                  clobber: bool = False,
                                  step: Optional[str] = None,
                                  index: Optional[str] = None):
        """
        Adds a VCD source for vector-based power analysis.

        Args:
            scope (str): The instance path of the design top within the VCD.
            library (str): The library (design) providing the VCD fileset.
            fileset (str): The fileset containing the VCD file.
            clobber (bool): If True, overwrites any existing entries. If False (default),
                the entry is appended.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        if clobber:
            return self.set("var", "power_activities", (scope, library, fileset),
                            step=step, index=index)
        return self.add("var", "power_activities", (scope, library, fileset),
                        step=step, index=index)

    def setup(self):
        super().setup()

        self.set_script("sc_timing.tcl")

        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        else:
            # sc_timing.tcl reads the netlist from the design filesets when no vg
            # input is present; declare them required so they are hashed (cache)
            # and copied (remote runs).
            for obj, key in self.get_fileset_file_keys("verilog"):
                self.add_required_key(obj, *key)

        if self.get("var", "timing_mode"):
            self.add_required_key("var", "timing_mode")
            if self.get("var", "timing_mode") not in self.project.constraint.timing.get_modes():
                raise LookupError(f'{self.get("var", "timing_mode")} is not a defined mode')
        self.add_required_key("var", "top_n_paths")
        self.add_required_key("var", "unique_path_groups_per_clock")
        # NOTE: opensta_generic_sdc is intentionally not required — the opensta scripts only read it
        # in a commented-out fallback (the live reader is OpenROAD's separate same-named parameter).

        self.add_required_key("var", "write_sdf")
        if self.get("var", "write_sdf"):
            for corner in self.project.getkeys('constraint', 'timing', 'scenario'):
                self.add_output_file(ext=f"{corner}.sdf")

        self.add_required_key("var", "write_liberty")
        if self.get("var", "write_liberty"):
            for corner in self.project.getkeys('constraint', 'timing', 'scenario'):
                self.add_output_file(ext=f"{corner}.lib")

        # VCD power activities are read by sc_timing.tcl; declare the source files
        # required so they are hashed (cache) and copied (remote runs). The
        # power_activities var itself is optional (defaults to an empty list), but
        # is required once activities are configured.
        power_activities = self.get("var", "power_activities")
        if power_activities:
            self.add_required_key("var", "power_activities")
            for _, lib_name, fileset in power_activities:
                lib = self.project.get_library(lib_name)
                for fs_lib, fs in self.project.get_filesets(library=lib, filesets=[fileset]):
                    self.add_required_key(fs_lib, "fileset", fs, "file", "vcd")
        elif f"{self.design_topmodule}.vcd" in self.get_files_from_input_nodes():
            # default: VCD delivered from a previous node in the same flowgraph
            self.add_input_file(ext="vcd")
        else:
            # default: VCD provided via the active filesets
            for obj, key in self.get_fileset_file_keys("vcd"):
                self.add_required_key(obj, *key)

    def post_process(self):
        super().post_process()

        peakpower = []
        leakagepower = []
        skews = {}
        # parsing log file
        logpath = self.get_logpath("exe")
        with sc_open(logpath) as f:
            timescale = "s"
            metric = None
            for line in f:
                metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
                value = re.search(r'(\d*\.?\d)*', line)
                fmax = re.search(r'fmax = (\d*\.?\d*)', line)
                tns = re.search(r'^tns (.*)', line)
                slack = re.search(r'^worst slack (.*)', line)
                skew = re.search(r'^\s*(.*)\s+(.*) skew', line)
                power = re.search(r'^Total(.*)', line)
                if metricmatch:
                    metric = metricmatch.group(1)
                    continue

                if metric:
                    if metric == 'timeunit':
                        timescale = f'{line.strip()}s'
                        metric = None
                    if metric == 'fmax':
                        if fmax:
                            self.record_metric("fmax", float(fmax.group(1)),
                                               source_file=self.__report_map("fmax"),
                                               source_unit="MHz")
                            metric = None
                    elif metric == 'power':
                        if power:
                            powerlist = power.group(1).split()
                            leakage = powerlist[2]
                            total = powerlist[3]

                            peakpower.append(float(total))
                            leakagepower.append(float(leakage))

                            metric = None
                    elif metric == 'cellarea':
                        self.record_metric("cellarea", float(value.group(0)),
                                           source_file=self.__report_map("cellarea"),
                                           source_unit="um^2")
                        metric = None
                    elif metric in ('logicdepth',
                                    'cells',
                                    'nets',
                                    'buffers',
                                    'inverters',
                                    'registers',
                                    'unconstrained',
                                    'pins',
                                    'setuppaths',
                                    'holdpaths'):
                        self.record_metric(metric, int(value.group(0)),
                                           source_file=self.__report_map(metric))
                        metric = None
                    elif metric in ('holdslack', 'setupslack'):
                        if slack:
                            self.record_metric(metric, float(slack.group(1).split()[-1]),
                                               source_file=self.__report_map(metric),
                                               source_unit=timescale)
                            metric = None
                    elif metric in ('setuptns', 'holdtns'):
                        if tns:
                            self.record_metric(metric, float(tns.group(1).split()[-1]),
                                               source_file=self.__report_map(metric),
                                               source_unit=timescale)
                            metric = None
                    elif metric in ('setupskew', 'holdskew'):
                        if skew:
                            skews.setdefault(skew.group(2), []).append(float(skew.group(1)))
                    else:
                        metric = None

        if peakpower:
            self.record_metric("peakpower", max(peakpower),
                               source_file=self.__report_map("peakpower"),
                               source_unit='W')
        if leakagepower:
            self.record_metric("leakagepower", max(leakagepower),
                               source_file=self.__report_map("leakagepower"),
                               source_unit='W')
        if skews:
            for skewtype, values in skews.items():
                skew = f'{skewtype}skew'
                self.record_metric(skew, max(values),
                                   source_file=self.__report_map(skew),
                                   source_unit=timescale)

        drv_report = "reports/checks/drv_violators.rpt"
        if os.path.exists(drv_report):
            drv_count = 0
            with sc_open(drv_report) as f:
                for line in f:
                    if re.search(r'\(VIOLATED\)$', line):
                        drv_count += 1

            self.record_metric("drvs", drv_count, source_file=[drv_report])

    def __report_map(self, metric):
        corners = self.project.getkeys('constraint', 'timing', 'scenario')
        power_reports = [f"reports/power/{corner}.rpt" for corner in corners]
        mapping = {
            "peakpower": power_reports,
            "leakagepower": power_reports,
            "unconstrained": ["reports/timing/unconstrained.rpt",
                              "reports/timing/unconstrained.topN.rpt"],
            "setuppaths": ["reports/timing/setup.rpt", "reports/timing/setup.topN.rpt"],
            "holdpaths": ["reports/timing/hold.rpt", "reports/timing/hold.topN.rpt"],
            "holdslack": ["reports/timing/hold.rpt", "reports/timing/hold.topN.rpt"],
            "setupslack": ["reports/timing/setup.rpt", "reports/timing/setup.topN.rpt"],
            "setuptns": ["reports/timing/setup.rpt", "reports/timing/setup.topN.rpt"],
            "holdtns": ["reports/timing/hold.rpt", "reports/timing/hold.topN.rpt"],
            "setupskew": ["reports/clocks/skew.setup.rpt",
                          "reports/timing/setup.rpt", "reports/timing/setup.topN.rpt"],
            "holdskew": ["reports/clocks/skew.hold.rpt",
                         "reports/timing/hold.rpt", "reports/timing/hold.topN.rpt"]
        }

        if metric in mapping:
            paths = [self.get_logpath("exe")]
            for path in mapping[metric]:
                if os.path.exists(path):
                    paths.append(path)
            return paths
        return [self.get_logpath("exe")]


class TimingTask(TimingTaskBase):
    '''
    Generate static timing reports for an ASIC target device.
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "timing"

    def get_tcl_variables(self, manifest=None):
        """
        Gets Tcl variables for the task, setting 'opensta_timing_mode' to asic.
        """
        vars = super().get_tcl_variables(manifest)
        vars["opensta_timing_mode"] = "asic"
        return vars

    def setup(self):
        """
        Prepare timing-related input files for an ASIC timing task by registering SDC,
        SPEF, or SDF files as inputs or required keys.

        If a top-module SDC file is present in the input nodes, it is added as an input;
        otherwise, SDC file keys from the fileset are marked required.
        For each timing scenario with a `pexcorner`, the method adds a matching SPEF file
        (named `<topmodule>.<pexcorner>.spef`) if present. If no SPEF files were added,
        it falls back to adding matching SDF files (named `<topmodule>.<pexcorner>.sdf`
        when present.

        Notes:
        - Uses :meth:`.Task.design_topmodule` to locate per-corner SPEF/SDF files.
        """
        super().setup()

        if f"{self.design_topmodule}.sdc" in self.get_files_from_input_nodes():
            self.add_input_file(ext="sdc")
        else:
            for obj, key in self.get_fileset_file_keys("sdc"):
                self.add_required_key(obj, *key)

            # sc_timing.tcl also reads the timing mode's sdcfileset, resolving
            # aliases and depfilesets; mirror that here so the files are hashed
            # (cache) and copied (remote runs).
            timing_mode = self.get("var", "timing_mode")
            if timing_mode:
                mode_obj = self.project.constraint.timing.get_mode(timing_mode)
                for lib, fileset in mode_obj.get_sdcfileset():
                    libobj = self.project.get_library(lib)
                    for fs_lib, fs in self.project.get_filesets(library=libobj,
                                                                filesets=[fileset]):
                        if fs_lib.has_file(fileset=fs, filetype="sdc"):
                            self.add_required_key(fs_lib, "fileset", fs, "file", "sdc")

        # per-corner liberty files are read by sc_timing.tcl; declare them required
        # so they are hashed (cache) and copied (remote runs).
        delay_model = self.project.get("asic", "delaymodel")
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get_library(asiclib)
            for scenario in self.project.constraint.timing.get_scenario().values():
                for corner in scenario.get_libcorner(self.step, self.index):
                    if not lib.valid("asic", "libcornerfileset", corner, delay_model):
                        continue
                    self.add_required_key(lib, "asic", "libcornerfileset", corner, delay_model)
                    for fileset in lib.get("asic", "libcornerfileset", corner, delay_model):
                        self.add_required_key(lib, "fileset", fileset, "file", "liberty")

        added_spef = False
        for scenario in self.project.constraint.timing.get_scenario().values():
            if scenario.get("pexcorner") is None:
                continue
            if f"{self.design_topmodule}.{scenario.get('pexcorner')}.spef" in \
                    self.get_files_from_input_nodes():
                self.add_input_file(ext=f"{scenario.get('pexcorner')}.spef")
                added_spef = True
        if not added_spef:
            for scenario in self.project.constraint.timing.get_scenario().values():
                if scenario.get("pexcorner") is None:
                    continue
                if f"{self.design_topmodule}.{scenario.get('pexcorner')}.sdf" in \
                        self.get_files_from_input_nodes():
                    self.add_input_file(ext=f"{scenario.get('pexcorner')}.sdf")


class FPGATimingTask(TimingTaskBase):
    '''
    Generate static timing reports for an FPGA target device.
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "fpga_timing"

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, FPGA
        from siliconcompiler.scheduler import SchedulerNode
        from siliconcompiler.demos.fpga_demo import Z1000
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = FPGA(design)
        proj.add_fileset("docs")
        proj.set_fpga(Z1000())
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task

    def get_tcl_variables(self, manifest=None):
        """
        Gets Tcl variables for the task, setting 'opensta_timing_mode' to fpga.
        """
        vars = super().get_tcl_variables(manifest)
        vars["opensta_timing_mode"] = "fpga"
        return vars

    def setup(self):
        super().setup()

        self.add_input_file(ext="sdc")
        self.add_input_file(ext="typical.sdf")

        # per-device liberty files are read by sc_timing.tcl (fpga mode); declare
        # them required so they are hashed (cache) and copied (remote runs).
        device = self.project.get("fpga", "device")
        if device:
            lib = self.project.get_library(device)
            # not every FPGA device defines the opensta liberty_filesets parameter
            if lib.valid("tool", "opensta", "liberty_filesets") and \
                    lib.get("tool", "opensta", "liberty_filesets"):
                self.add_required_key(lib, "tool", "opensta", "liberty_filesets")
                for fileset in lib.get("tool", "opensta", "liberty_filesets"):
                    if lib.has_file(fileset=fileset, filetype="liberty"):
                        self.add_required_key(lib, "fileset", fileset, "file", "liberty")

    def pre_process(self):
        """
        Skip this node if no non-empty sdc files in inputs
        """
        file_path = f"inputs/{self.design_topmodule}.sdc"

        if os.path.getsize(file_path) == 0:
            raise TaskSkip(f"an empty {self.design_topmodule}.sdc file")

        super().pre_process()
