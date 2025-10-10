import re

import os.path

from siliconcompiler import sc_open

from siliconcompiler.tools.opensta import OpenSTATask

from siliconcompiler import TaskSkip


class TimingTaskBase(OpenSTATask):
    '''
    Base class for generating static timing reports.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("top_n_paths", "int", "number of paths to report timing for",
                           defvalue=10)
        self.add_parameter("unique_path_groups_per_clock", "bool",
                           "if true will generate separate path groups per clock", defvalue=False)
        self.add_parameter("timing_mode", "str", "timing mode to use")

        self.set_dataroot("siliconcompiler", "python://siliconcompiler")
        self.add_parameter("opensta_generic_sdc", "file", "generic opensta SDC file",
                           defvalue="tools/_common/sdc/sc_constraints.sdc",
                           dataroot="siliconcompiler")

    def set_timing_mode(self, mode: str, step: str = None, index: str = None):
        return self.set("var", "timing_mode", mode, step=step, index=index)

    def setup(self):
        super().setup()

        self.set_script("sc_timing.tcl")

        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")

        if self.get("var", "timing_mode"):
            self.add_required_key("var", "timing_mode")
        self.add_required_key("var", "top_n_paths")
        self.add_required_key("var", "unique_path_groups_per_clock")
        self.add_required_key("var", "opensta_generic_sdc")

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
                                   source_unit='W')

        drv_report = "reports/drv_violators.rpt"
        if os.path.exists(drv_report):
            drv_count = 0
            with sc_open(drv_report) as f:
                for line in f:
                    if re.search(r'\(VIOLATED\)$', line):
                        drv_count += 1

            self.record_metric("drvs", drv_count, source_file=[drv_report])

    def __report_map(self, metric):
        corners = self.project.getkeys('constraint', 'timing')
        mapping = {
            "power": [f"reports/power.{corner}.rpt" for corner in corners],
            "unconstrained": ["reports/unconstrained.rpt", "reports/unconstrained.topN.rpt"],
            "setuppaths": ["reports/setup.rpt", "reports/setup.topN.rpt"],
            "holdpaths": ["reports/hold.rpt", "reports/hold.topN.rpt"],
            "holdslack": ["reports/hold.rpt", "reports/hold.topN.rpt"],
            "setupslack": ["reports/setup.rpt", "reports/setup.topN.rpt"],
            "setuptns": ["reports/setup.rpt", "reports/setup.topN.rpt"],
            "holdtns": ["reports/hold.rpt", "reports/hold.topN.rpt"],
            "setupskew": ["reports/skew.setup.rpt", "reports/setup.rpt", "reports/setup.topN.rpt"],
            "holdskew": ["reports/skew.hold.rpt", "reports/hold.rpt", "reports/hold.topN.rpt"]
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

    def pre_process(self):
        """
        Skip this node if no non-empty sdc files in inputs
        """
        file_path = f"inputs/{self.design_topmodule}.sdc"

        if os.path.getsize(file_path) == 0:
            raise TaskSkip(f"an empty {self.design_topmodule}.sdc file")

        super().pre_process()
