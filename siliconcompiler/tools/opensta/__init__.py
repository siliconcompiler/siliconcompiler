'''
OpenSTA is a gate level static timing verifier.

Documentation: https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/doc/OpenSTA.pdf

Sources: https://github.com/The-OpenROAD-Project/OpenSTA

Installation: https://github.com/The-OpenROAD-Project/OpenSTA (also installed with OpenROAD)
'''


from siliconcompiler import TaskSchema

from siliconcompiler import FPGASchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope

from siliconcompiler.schema.utils import trim


class OpenSTATask(TaskSchema):
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
        self.add_regex("errors", r'^\[ERROR')

    def runtime_options(self):
        options = super().runtime_options()
        options.append("-no_init")
        if not self.has_breakpoint():
            options.append("-exit")

        options.extend(["-threads", self.get_threads()])

        return options

    @classmethod
    def make_docs(cls):
        from siliconcompiler import FlowgraphSchema, DesignSchema, ASICProject
        from siliconcompiler.scheduler import SchedulerNode
        from siliconcompiler.targets import freepdk45_demo
        design = DesignSchema("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = ASICProject(design)
        proj.add_fileset("docs")
        proj.load_target(freepdk45_demo.setup)
        flow = FlowgraphSchema("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task

class OpenSTAFPGA(FPGASchema):
    """
    Schema for defining library parameters specifically for the
    OpenSTA tool when targeting an FPGA.

    This class extends the base FPGASchema to manage various settings
    related to OpenSTA, specifically for passing timing corner liberty
    filesets.
    """
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)

        schema.insert(
                'fpga_sta_timing', 'libcornerfileset', 'default', 'default',
                Parameter(
                    '{str}',
                    scope=Scope.GLOBAL,
                    shorthelp="FPGA: map of filesets to timing corners used for STA",
                    example=[
                        "api: schema.set('fpga_sta_timing', 'libcornerfileset', 'typical', 'nldm', 'timing.typical')"],
                    help=trim("""Map between filesets and timing corners.""")))

    def add_fpga_sta_timing_libcornerfileset(self, corner: str, model: str, fileset: str = None):
        """
        Adds a mapping between filesets a corners defined in the library.

        Args:
            corner (str): name of the timing or parasitic corner
            model (str): type of delay modeling used, eg. nldm, ccs, etc.
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        if not isinstance(model, str):
            raise TypeError("model must be a string")

        self._assert_fileset(fileset)

        return self.add("fpga_sta_timing", "libcornerfileset", corner, model, fileset)
