from siliconcompiler import Task


class APRTask(Task):
    '''
    Perform automated place and route on FPGAs
    '''
    def __init__(self):
        super().__init__()

    def tool(self):
        return "nextpnr"

    def task(self):
        return "apr"

    def parse_version(self, stdout):
        # Examples:
        # nextpnr-ice40 -- Next Generation Place and Route (Version c73d4cf6)
        # nextpnr-ice40 -- Next Generation Place and Route (Version nextpnr-0.2)
        version = stdout.split()[-1].rstrip(')')
        if version.startswith('nextpnr-'):
            return version.split('-')[1]
        else:
            return version

    def setup(self):
        super().setup()

        self.set_exe("nextpnr-ice40", vswitch="--version")
        self.add_version(">=0.2")

        self.add_input_file(ext="netlist.json")
        self.add_output_file(ext="asc")

        self.add_required_key("fpga", "device")
        self.add_required_key("library", self.project.get("fpga", "device"), "fpga", "partname")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="pcf"):
                self.add_required_key(lib, "fileset", fileset, "file", "pcf")

    def runtime_options(self):
        options = super().runtime_options()

        partname = self.project.get("library",
                                    self.project.get("fpga", "device"), "fpga", "partname")

        options.extend(['--json', f'inputs/{self.design_topmodule}.netlist.json'])
        options.extend(['--asc', f'outputs/{self.design_topmodule}.asc'])

        if partname == 'ice40up5k-sg48':
            options.extend(['--up5k', '--package', 'sg48'])

        for lib, fileset in self.project.get_filesets():
            for pcf in lib.get_file(fileset=fileset, filetype="pcf"):
                options.extend(['--pcf', pcf])

        return options

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, FPGA, FPGADevice
        from siliconcompiler.scheduler import SchedulerNode
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = FPGA(design)
        proj.add_fileset("docs")
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)
        proj.set_fpga(FPGADevice("<fpga>"))

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task
