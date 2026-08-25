import os.path

from siliconcompiler import Task
from siliconcompiler.utils import sc_open


class SECTask(Task):
    """SEC task using Kepler-formal to check a netlist against the RTL it came from."""
    def tool(self) -> str:
        return "kepler-formal"

    def task(self) -> str:
        return "sec"

    def setup(self) -> None:
        super().setup()

        self.set_exe("kepler-formal")

        # Log file handled by kepler-formal config
        self.set_logdestination("stdout", "none")
        self.set_logdestination("stderr", "none")

        self.add_input_file(self.__rtl_file())
        self.add_input_file(ext="vg")

        for lib, corner, delay_model in self.__libcorners():
            self.add_required_key(lib, "asic", "libcornerfileset", corner, delay_model)
            for fileset in lib.get("asic", "libcornerfileset", corner, delay_model):
                self.add_required_key(lib, "fileset", fileset, "file", "liberty")

    def __rtl_file(self) -> str:
        """Returns the elaborated RTL file, which is SystemVerilog if the design holds any."""
        verilog = f"{self.design_topmodule}.v"
        if verilog in self.get_files_from_input_nodes():
            return verilog
        return f"{self.design_topmodule}.sv"

    def __libcorners(self):
        """Yields the library, corner and delay model of each corner this node checks."""
        scenarios = self.project.constraint.timing.get_scenario()
        if not scenarios:
            raise ValueError("SEC requires at least one timing scenario to determine "
                             "library corners.")
        scenario = list(scenarios.values())[0]
        libcorners = scenario.get_libcorner(self.step, self.index)
        delay_model = self.project.get("asic", "delaymodel")
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get_library(asiclib)
            for corner in libcorners:
                if not lib.valid("asic", "libcornerfileset", corner, delay_model):
                    continue
                yield lib, corner, delay_model

    def __config_file(self) -> str:
        return "sec.yaml"

    def pre_process(self):
        super().pre_process()

        with open(self.__config_file(), "w") as f:
            # sv2v reads design 1 as SystemVerilog and design 2 as verilog, which
            # only the sequential engine supports.
            f.write("format: sv2v\n")
            f.write("verification: sec\n")
            # Pin both rather than take kepler-formal's defaults: binary makes it
            # refuse a design holding reset-unanchored state instead of reporting no
            # difference for it.
            f.write("sec_engine: k_induction\n")
            f.write("sec_encoding: binary\n")
            f.write("input_paths:\n")
            f.write(f"  - [inputs/{self.__rtl_file()}]\n")
            f.write(f"  - [inputs/{self.design_topmodule}.vg]\n")
            f.write("liberty_files:\n")
            for lib, corner, delay_model in self.__libcorners():
                for fileset in lib.get("asic", "libcornerfileset", corner, delay_model):
                    for file in lib.get_file(fileset=fileset, filetype="liberty"):
                        f.write(f"  - {file}\n")
            f.write(f"log_file: {self.get_logpath('exe')}\n")

    def runtime_options(self):
        options = super().runtime_options()
        options.append("--config")
        options.append(self.__config_file())
        return options

    def post_process(self):
        super().post_process()

        # Equivalent and differing both exit zero, so the verdict is only in the log.
        log = self.get_logpath('exe')
        if os.path.exists(log):
            with sc_open(log, 'r') as f:
                for logline in f:
                    if "No difference was found." in logline:
                        self.record_metric("drvs", 0, source_file=log)
                    elif "Difference was found." in logline:
                        self.record_metric("drvs", 1, source_file=log)

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
