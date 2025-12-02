'''
OpenSTA is a gate level static timing verifier.

Documentation: https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/doc/OpenSTA.pdf

Sources: https://github.com/The-OpenROAD-Project/OpenSTA

Installation: https://github.com/The-OpenROAD-Project/OpenSTA (also installed with OpenROAD)
'''


from siliconcompiler import Task

from siliconcompiler import FPGADevice


class OpenSTATask(Task):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "opensta"

    def parse_version(self, stdout):
        return stdout.strip()

    def setup(self):
        super().setup()

        self.set_exe("sta", vswitch="-version", format="tcl")
        self.add_version(">=2.6.2")

        self.set_dataroot("refdir-root", __file__)
        with self.active_dataroot("refdir-root"):
            self.set_refdir("scripts")

        self.set_threads()

        self.add_regex("warnings", r'^\[WARNING|^Warning')
        self.add_regex("errors", r'^\[ERROR|^Error')

    def runtime_options(self):
        options = super().runtime_options()
        options.append("-no_init")
        if not self.has_breakpoint():
            options.append("-exit")

        options.extend(["-threads", self.get_threads()])

        return options

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


class OpenSTAFPGA(FPGADevice):
    """
    Schema for defining library parameters specifically for the
    OpenSTA tool when targeting an FPGA.

    This class extends the base FPGADevice to manage various settings
    related to OpenSTA, specifically for passing liberty filesets.
    """
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("opensta", "liberty_filesets", "{str}",
                                   "A set of liberty filesets to read to perform STA.")

    def add_opensta_liberty_fileset(self, fileset: str = None, clobber: bool = False):
        """
        Adds the given fileset to the set of liberty files which will be used
        for STA.

        Args:
            fileset (str): name of the fileset
            clobber (bool, optional): If True, overwrites existing list.
                                      If False, adds to the list. Defaults to False.
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        if clobber:
            return self.set("tool", "opensta", "liberty_filesets", fileset)
        else:
            return self.add("tool", "opensta", "liberty_filesets", fileset)
