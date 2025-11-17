'''
VPR (Versatile Place and Route) is an open source CAD
tool designed for the exploration of new FPGA architectures and
CAD algorithms, at the packing, placement and routing phases of
the CAD flow. VPR takes, as input, a description of an FPGA
architecture along with a technology-mapped user circuit. It
then performs packing, placement, and routing to map the
circuit onto the FPGA. The output of VPR includes the FPGA
configuration needed to implement the circuit and statistics about
the final mapped design (eg. critical path delay, area, etc).

Documentation: https://docs.verilogtorouting.org/en/latest

Sources: https://github.com/verilog-to-routing/vtr-verilog-to-routing

Installation: https://github.com/verilog-to-routing/vtr-verilog-to-routing
'''

import glob
import shutil
import json
import re

import os.path

from siliconcompiler import sc_open

from siliconcompiler import Task

from typing import List, Union

from siliconcompiler import FPGADevice


class VPRFPGA(FPGADevice):
    """
    Schema for defining library parameters specifically for the
    VPR (Verilog Place and Route) tool.

    This class extends the base FPGADevice to manage various settings
    related to VPR, such as device information, channel width, resource types,
    and input file paths for the architecture and routing graph.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("vpr", "devicecode", "str",
                                   "The name or code for the target FPGA device.")
        self.define_tool_parameter("vpr", "channelwidth", "int",
                                   "The channel width to be used during routing.")

        self.define_tool_parameter("vpr", "registers", "{str}",
                                   "A set of supported register types.")
        self.define_tool_parameter("vpr", "brams", "{str}",
                                   "A set of supported block RAM types.")
        self.define_tool_parameter("vpr", "dsps", "{str}",
                                   "A set of supported DSP types.")

        self.define_tool_parameter("vpr", "archfile", "file",
                                   "The path to the VPR architecture description file.")
        self.define_tool_parameter("vpr", "graphfile", "file",
                                   "The path to the VPR routing graph file.")
        self.define_tool_parameter("vpr", "constraintsmap", "file",
                                   "The path to the VPR constraints map file.")

        self.define_tool_parameter("vpr", "clock_model", "<ideal,route,dedicated_network>",
                                   "The clock modeling strategy to be used.")

        self.define_tool_parameter("vpr",
                                   "router_lookahead",
                                   "<classic,map,compressed_map,extended_map,simple>",
                                   "The lookahead the router will use to estimate cost.",
                                   defvalue="map")

    def set_vpr_devicecode(self, name: str):
        """
        Sets the device code for VPR.

        Args:
            name (str): The name or code of the device.
        """
        return self.set("tool", "vpr", "devicecode", name)

    def set_vpr_channelwidth(self, width: int):
        """
        Sets the channel width for VPR routing.

        Args:
            width (int): The channel width value.
        """
        return self.set("tool", "vpr", "channelwidth", width)

    def add_vpr_registertype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds one or more register types to the list of supported registers.

        Args:
            name (Union[str, List[str]], optional): The register type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "vpr", "registers", name)
        else:
            return self.add("tool", "vpr", "registers", name)

    def add_vpr_bramtype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds one or more block RAM types to the list of supported BRAMs.

        Args:
            name (Union[str, List[str]], optional): The BRAM type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "vpr", "brams", name)
        else:
            return self.add("tool", "vpr", "brams", name)

    def add_vpr_dsptype(self, name: Union[str, List[str]] = None, clobber: bool = False):
        """
        Adds one or more DSP types to the list of supported DSPs.

        Args:
            name (Union[str, List[str]], optional): The DSP type or a list of types.
                                                    Defaults to None.
            clobber (bool, optional): If True, overwrites the existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if clobber:
            return self.set("tool", "vpr", "dsps", name)
        else:
            return self.add("tool", "vpr", "dsps", name)

    def set_vpr_archfile(self, file: str, dataroot: str = None):
        """
        Sets the path to the VPR architecture file.

        Args:
            file (str): The path to the architecture file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("tool", "vpr", "archfile", file)

    def set_vpr_graphfile(self, file: str, dataroot: str = None):
        """
        Sets the path to the VPR routing graph file.

        Args:
            file (str): The path to the routing graph file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("tool", "vpr", "graphfile", file)

    def set_vpr_constraintsmap(self, file: str, dataroot: str = None):
        """
        Sets the path to the VPR constraints map file.

        Args:
            file (str): The path to the constraints map file.
            dataroot (str, optional): The data root directory. Defaults to the active package.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("tool", "vpr", "constraintsmap", file)

    def set_vpr_clockmodel(self, model: str):
        """
        Sets the clock modeling strategy.

        Args:
            model (str): The name of the clock model to use
                         (e.g., 'ideal', 'route', or 'dedicated_network').
        """
        return self.set("tool", "vpr", "clock_model", model)

    def set_vpr_router_lookahead(self, lookahead: str):
        """
        Sets the lookahead that the router will use to estimate the cost of
        paths in the routing graph. This is also sometimes used in placement
        to estimate costs.

        Args:
            lookahead (str): The name of the lookahead to use
                             (e.g., 'map', 'classic', ...).
        """
        return self.set("tool", "vpr", "router_lookahead", lookahead)


class VPRTask(Task):
    __block_file = "reports/block_usage.json"

    def __init__(self):
        super().__init__()

        self.add_parameter("enable_images", "bool",
                           "true/false generate images of the design at the end of the task",
                           defvalue=True)
        self.add_parameter("timing_paths", "int", "number of timing paths to report", defvalue=20)
        self.add_parameter("timing_report_type",
                           "<netlist,aggregated,detailed,debug>",
                           "level of detail for timing reports: vpr --timing_report_detail",
                           defvalue="aggregated")
        self.add_parameter("enable_timing_analysis", "bool", "enable timing analysis")
        self.add_parameter("router_lookahead",
                           "<classic,map,compressed_map,extended_map,simple>",
                           "The lookahead the router will use to estimate cost.")

    def tool(self):
        return "vpr"

    def parse_version(self, stdout):
        # Example output of vpr --version:
        # Note that blank comment lines in this example
        # represent newlines printed by vpr --version

        # VPR FPGA Placement and Routing.
        # Version: 8.1.0-dev+c4156f225
        # Revision: v8.0.0-7887-gc4156f225
        # Compiled: 2023-06-14T17:32:05
        # Compiler: GNU 9.4.0 on Linux-5.14.0-1059-oem x86_64
        # Build Info: release IPO VTR_ASSERT_LEVEL=2
        #
        # University of Toronto
        # verilogtorouting.org
        # vtr-users@googlegroups.com
        # This is free open source code under MIT license.
        #
        #

        # Grab the revision. Which will be of the form:
        #       v8.0.0-7887-gc4156f225
        #               or
        #       v8.0.0-7887-gc4156f225-dirty (if modified locally)
        revision = stdout.split()[8]

        # VTR infrequently makes even minor releases, use the number of commits
        # since the last release of VTR as another part of the release segment.
        pieces = revision.split("-")
        if len(pieces) == 4:
            # Strip off the hash and "dirty" if they exists.
            return "-".join(pieces[:-2])
        if len(pieces) == 3:
            # Strip off the hash if it exists.
            return "-".join(pieces[:-1])
        else:
            return revision

    def auto_constraints_file(self):
        return 'inputs/sc_constraints.xml'

    def setup(self):
        super().setup()

        self.set_exe("vpr", vswitch="--version")
        self.add_version(">=v8.0.0-12677")

        self.add_regex("warnings", "^Warning")
        self.add_regex("errors", "^Error")

        self.set_threads()

        self.add_required_key("var", "enable_images")
        self.add_required_key("var", "timing_paths")
        self.add_required_key("var", "timing_report_type")
        self.add_required_key("var", "enable_timing_analysis")
        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="sdc"):
                self.add_required_key(lib, "fileset", fileset, "file", "sdc")
                self.set("var", "enable_timing_analysis", True)

        fpga = self.project.get("library", self.project.get("fpga", "device"), field="schema")
        self.add_required_key(fpga, "tool", "vpr", "devicecode")
        self.add_required_key(fpga, "tool", "vpr", "clock_model")
        self.add_required_key(fpga, "tool", "vpr", "archfile")
        self.add_required_key(fpga, "tool", "vpr", "graphfile")
        self.add_required_key(fpga, "tool", "vpr", "channelwidth")
        if self.get("var", "router_lookahead"):
            self.add_required_key("var", "router_lookahead")
        else:
            self.add_required_key(fpga, "tool", "vpr", "router_lookahead")

    def runtime_options(self):
        options = super().runtime_options()

        fpga = self.project.get("library", self.project.get("fpga", "device"), field="schema")

        options.extend(["--device", fpga.get("tool", "vpr", "devicecode")])

        # Medium-term solution:  VPR performs hash digest checks that
        # fail if file paths are changed between steps.  We wish to
        # disable the digest checks to work around this
        options.extend(["--verify_file_digests", "off"])

        options.extend(["--write_block_usage", VPRTask.__block_file])
        options.extend(["--outfile_prefix", "outputs/"])

        options.append(fpga.find_files("tool", "vpr", "archfile"))

        options.extend(["--num_workers", self.get_threads()])

        # For most architectures, constant nets need to be routed
        # like regular nets to be functionally correct (however inefficient
        # that might be...); these two options help control that
        options.extend(['--constant_net_method', 'route'])
        options.extend(['--const_gen_inference', 'none'])

        # If we allow VPR to sweep dangling primary I/Os and logic blocks
        # it can interfere with circuit debugging; so disable that
        options.extend(['--sweep_dangling_primary_ios', 'off'])
        # If you don't sweep dangling primary I/Os, but sweeping nets
        # VPR can crash:
        options.extend(['--sweep_dangling_nets', 'off'])
        # If you don't sweep dangling nets then the timing engine requires
        # you to set an option allowing dangling nodes
        options.extend(['--allow_dangling_combinational_nodes', 'on'])
        options.extend(['--sweep_constant_primary_outputs', 'off'])
        options.extend(['--sweep_dangling_blocks', 'off'])

        # Explicitly specify the clock modeling type in the part driver
        # to avoid ambiguity and future-proof against new VPR clock models
        options.extend(['--clock_modeling', fpga.get("tool", "vpr", "clock_model")])
        if fpga.get("tool", "vpr", "clock_model") == 'dedicated_network':
            options.append('--two_stage_clock_routing')

        # Set the router lookahead.
        if self.get("var", "router_lookahead"):
            # Use the router lookahead set on the tool if provided.
            options.extend(['--router_lookahead',
                            self.get("var", "router_lookahead")])
        else:
            # Use the router lookahead set on the FPGA.
            options.extend(['--router_lookahead',
                            fpga.get("tool", "vpr", "router_lookahead")])

        sdc_file = None
        for lib, fileset in self.project.get_filesets():
            files = lib.get_file(fileset=fileset, filetype="sdc")
            if files:
                sdc_file = files[0]

        if sdc_file:
            options.append("--sdc_file")
            options.append(sdc_file)

        if self.get("var", "enable_timing_analysis"):
            options.extend(['--timing_report_detail', self.get("var", "timing_report_type")])
            options.extend(['--timing_report_npaths', self.get("var", "timing_paths")])
        else:
            options.extend(["--timing_analysis", "off"])

        # Per the scheme implemented in the placement pre-process step,
        # if a constraints file exists it will always be in the auto_constraints()
        # location:
        if os.path.isfile(self.auto_constraints_file()):
            options.extend(["--read_vpr_constraints", self.auto_constraints_file()])

        # Routing graph XML:
        options.extend(["--read_rr_graph", fpga.find_files("tool", "vpr", "graphfile")])

        # ***NOTE: For real FPGA chips you need to specify the routing channel
        #          width explicitly.  VPR requires an explicit routing channel
        #          with when --read_rr_graph is used (typically the case for
        #          real chips).  Otherwise VPR performs a binary search for
        #          the minimum routing channel width that the circuit fits in.
        # Given the above, it may be appropriate to couple these variables somehow,
        # but --route_chan_width CAN be used by itself.
        options.extend(["--route_chan_width", fpga.get("tool", "vpr", "channelwidth")])

        return options

    def _get_common_graphics(self):
        graphics_commands = []

        # set_draw_block_text 1 displays the label for various blocks in the design
        # set_draw_block_outlines 1 displays the outline/boundary for various blocks in the design
        # save_graphics saves the block diagram as a png/svg/pdf
        # Refer:
        # https://docs.verilogtorouting.org/en/latest/vpr/command_line_usage/#graphics-options
        graphics_commands.append("set_draw_block_text 1; " +
                                 "set_draw_block_outlines 1; " +
                                 f"save_graphics reports/{self.design_topmodule}_place.png;")

        return graphics_commands

    def post_process(self):
        super().post_process()

        for report in glob.glob("*.rpt"):
            shutil.move(report, 'reports')

        fpga = self.project.get("fpga", "device")

        dff_cells = []
        if self.project.valid("library", fpga, "tool", "yosys", "registers"):
            dff_cells = self.project.get("library", fpga, "tool", "yosys", "registers")
        brams_cells = []
        if self.project.valid("library", fpga, "tool", "yosys", "brams"):
            brams_cells = self.project.get("library", fpga, "tool", "yosys", "brams")
        dsps_cells = []
        if self.project.valid("library", fpga, "tool", "yosys", "dsps"):
            dsps_cells = self.project.get("library", fpga, "tool", "yosys", "dsps")

        stat_extract = re.compile(r'  \s*(.*)\s*:\s*([0-9]+)')
        lut_match = re.compile(r'([0-9]+)-LUT')
        route_length = re.compile(r'	Total wirelength: ([0-9]+)')
        log_file = self.get_logpath("exe")
        mdata = {
            "registers": 0,
            "luts": 0,
            "dsps": 0,
            "brams": 0
        }
        with sc_open(log_file) as f:
            in_stats = False
            for line in f:
                if in_stats:
                    if not line.startswith("  "):
                        in_stats = False
                        continue
                    data = stat_extract.findall(line)
                    if data:
                        dtype, value = data[0]
                        dtype = dtype.strip()
                        value = int(value)

                        if dtype == "Blocks":
                            self.record_metric("cells", value, log_file)
                        elif dtype == "Nets":
                            self.record_metric("nets", value, log_file)
                        elif dtype in dff_cells:
                            mdata["registers"] += value
                        elif dtype in dsps_cells:
                            mdata["dsps"] += value
                        elif dtype in brams_cells:
                            mdata["brams"] += value
                        else:
                            lut_type = lut_match.findall(dtype)
                            if lut_type:
                                if int(lut_type[0]) == 0:
                                    pass
                                else:
                                    mdata["luts"] += value
                else:
                    if line.startswith("Circuit Statistics:"):
                        in_stats = True
                    route_len_data = route_length.findall(line)
                    if route_len_data:
                        # Fake the unit since this is meaningless for the FPGA
                        self.record_metric('wirelength', int(route_len_data[0]), log_file)

        for metric, value in mdata.items():
            self.record_metric(metric, value, log_file)

        if os.path.exists(VPRTask.__block_file):
            with sc_open(VPRTask.__block_file) as f:
                data = json.load(f)

                if "num_nets" in data and \
                        self.schema_metric.get('nets', step=self.step, index=self.index) is None:
                    self.record_metric("nets", int(data["num_nets"]), VPRTask.__block_file)

                io = 0
                if "input_pins" in data:
                    io += int(data["input_pins"])
                if "output_pins" in data:
                    io += int(data["output_pins"])

                self.record_metric("pins", io, VPRTask.__block_file)

        for setup_report in ("reports/report_timing.setup.rpt",
                             "reports/pre_pack.report_timing.setup.rpt"):
            if not os.path.exists(setup_report):
                continue

            slack = self._parse_timing_report(setup_report)
            if slack is not None:
                wns = min([slack, 0])
                self.record_metric("setupslack", slack, setup_report, source_unit="ns")
                self.record_metric("setupwns", wns, setup_report, source_unit="ns")
                break

        for hold_report in ("reports/report_timing.hold.rpt", ):
            if not os.path.exists(hold_report):
                continue

            slack = self._parse_timing_report(hold_report)
            if slack is not None:
                wns = min([slack, 0])
                self.record_metric("holdslack", slack, hold_report, source_unit="ns")
                self.record_metric("holdwns", wns, hold_report, source_unit="ns")
                break

        unconstrained = None
        unconstrained_reports = []
        for unconstrained_report in ("reports/report_unconstrained_timing.hold.rpt",
                                     "reports/report_unconstrained_timing.setup.rpt"):
            if not os.path.exists(unconstrained_report):
                continue

            paths = self._parse_unconstrained_report(unconstrained_report)
            if unconstrained is None:
                unconstrained = paths

            unconstrained = max([paths, unconstrained])
            unconstrained_reports.append(unconstrained_report)

        if unconstrained is not None:
            self.record_metric("unconstrained", unconstrained, unconstrained_reports)

    def _parse_timing_report(self, report):
        slack = re.compile(r"slack \(.*\)\s+(-?\d+\.?\d*)")
        with sc_open(report) as f:
            for line in f:
                match_slack = slack.findall(line)
                if match_slack:
                    return float(match_slack[0])
        return None

    def _parse_unconstrained_report(self, report):
        path = re.compile(r"\d+ .*")
        count = 0
        with sc_open(report) as f:
            for line in f:
                if path.match(line):
                    count += 1
        return count

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
