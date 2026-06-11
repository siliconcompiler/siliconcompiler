'''
Magic is a chip layout viewer, editor, and circuit verifier with
built in DRC and LVS engines.

Documentation: http://opencircuitdesign.com/magic/userguide.html

Installation: https://github.com/RTimothyEdwards/magic

Sources: https://github.com/RTimothyEdwards/magic
'''

from siliconcompiler import Task


class MagicTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("read_lef", "[file]", "lef files to read")

    def tool(self):
        return "magic"

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
        return stdout.strip('\n')

    def setup(self):
        super().setup()

        self.set_exe("magic", vswitch="--version", format="tcl")
        self.add_version(">=8.3.196")

        self.set_threads()

        self.set_dataroot("magic", __file__)
        with self.active_dataroot("magic"):
            self.set_refdir("scripts")
        self.set_script("sc_magic.tcl")

        self.add_commandline_option("-noc")
        self.add_commandline_option("-dnull")

        if f"{self.design_topmodule}.gds" in self.get_files_from_input_nodes():
            self.add_input_file(ext="gds")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="gds"):
                    self.add_required_key(lib, "fileset", fileset, "file", "gds")

        self.add_regex("errors", r'^Error')
        self.add_regex("warnings", r'warning')

        if self.get("var", "read_lef"):
            self.add_required_key("var", "read_lef")
        self.add_required_key("asic", "pdk")

        # sc_magic.tcl loads the DRC runset (tech file) on every magic task;
        # declare it required so it is hashed (cache) and copied (remote runs).
        pdk = self.project.get_library(self.project.get("asic", "pdk"))
        if pdk.get("pdk", "drc", "runsetfileset", "magic", "basic"):
            self.add_required_key(pdk, "pdk", "drc", "runsetfileset", "magic", "basic")
            for fileset in pdk.get("pdk", "drc", "runsetfileset", "magic", "basic"):
                if pdk.has_file(fileset=fileset, filetype="tech"):
                    self.add_required_key(pdk, "fileset", fileset, "file", "tech")
