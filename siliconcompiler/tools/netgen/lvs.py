import os.path

from siliconcompiler.tools.netgen import count_lvs
from siliconcompiler import sc_open

from siliconcompiler import Task


class LVSTask(Task):
    '''
    Perform LVS on the supplied netlists
    '''

    def __init__(self):
        super().__init__()

    def tool(self):
        return "netgen"

    def task(self):
        return "lvs"

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

    def parse_version(self, stdout):
        # First line: Netgen 1.5.190 compiled on Fri Jun 25 16:05:36 EDT 2021
        return stdout.split()[1]

    def setup(self):
        super().setup()

        self.set_exe("netgen", vswitch="-batch", format="tcl")
        self.add_version(">=1.5.192")

        self.set_threads()

        self.set_dataroot("netgen", __file__)
        with self.active_dataroot("netgen"):
            self.set_refdir("scripts")
        self.set_script("sc_lvs.tcl")

        self.add_commandline_option("-batch")
        self.add_commandline_option("source")

        self.add_input_file(ext="spice")
        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="verilog"):
                    self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        # sc_lvs.tcl reads asic pdk and loads the LVS runset (.tcl) on every run;
        # declare them required so the runset is hashed (cache) and copied (remote).
        self.add_required_key("asic", "pdk")
        pdk = self.project.get_library(self.project.get("asic", "pdk"))
        if pdk.get("pdk", "lvs", "runsetfileset", "netgen", "basic"):
            self.add_required_key(pdk, "pdk", "lvs", "runsetfileset", "netgen", "basic")
            # sc_lvs.tcl reads the runset resolving aliases and depfilesets;
            # mirror that here so the files are hashed (cache) and copied
            # (remote runs).
            runsets = pdk.get("pdk", "lvs", "runsetfileset", "netgen", "basic")
            for fs_lib, fs in self.project.get_filesets(library=pdk, filesets=runsets):
                if fs_lib.has_file(fileset=fs, filetype="tcl"):
                    self.add_required_key(fs_lib, "fileset", fs, "file", "tcl")

        self.set_logdestination("stderr", "log", suffix="errors")
        self.add_regex("warnings", '^Warning:')

    def post_process(self):
        with sc_open(f'{self.step}.errors') as f:
            errors = len([line for line in f.readlines() if not line.startswith("Note:")])
        self.record_metric('errors', errors, f'{self.step}.errors')

        # Export metrics
        lvs_report = f'reports/{self.design_topmodule}.lvs.json'
        if not os.path.isfile(lvs_report):
            self.logger.warning('No LVS report generated. Netgen may have encountered errors.')
            return

        lvs_failures = count_lvs.count_lvs_failures(lvs_report)

        # We don't count top-level pin mismatches as errors b/c we seem to get
        # false positives for disconnected pins. Report them as warnings
        # instead, the designer can then take a look at the full report for
        # details.
        pin_failures = lvs_failures[3]
        errors = lvs_failures[0] - pin_failures
        self.record_metric('drcs', errors, lvs_report)
        self.record_metric('warnings', pin_failures, lvs_report)
