'''
OpenSTA is a gate level static timing verifier.

Documentation: https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/doc/OpenSTA.pdf

Sources: https://github.com/The-OpenROAD-Project/OpenSTA

Installation: https://github.com/The-OpenROAD-Project/OpenSTA (also installed with OpenROAD)
'''


from siliconcompiler import TaskSchema


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
