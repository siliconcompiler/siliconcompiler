import os.path

from siliconcompiler import Task
from siliconcompiler.utils import sc_open


class LECTask(Task):
    """LEC task using Kepler-formal for logical equivalence checking."""
    def tool(self) -> str:
        return "kepler-formal"

    def task(self) -> str:
        return "lec"

    def setup(self) -> None:
        super().setup()

        self.set_exe("kepler-formal")

        # Log file handled by kepler-formal config
        self.set_logdestination("stdout", "none")
        self.set_logdestination("stderr", "none")

        if f"{self.design_topmodule}.lec.vg" in self.get_files_from_input_nodes():
            inputnodes = self.get_files_from_input_nodes()[f"{self.design_topmodule}.lec.vg"]
            if len(inputnodes) != 2:
                raise ValueError("LEC requires exactly two input netlists for comparison.")
            for node in inputnodes:
                self.add_input_file(
                    self.compute_input_file_node_name(f"{self.design_topmodule}.lec.vg", *node))

        scenarios = self.project.constraint.timing.get_scenario()
        if not scenarios:
            raise ValueError("LEC requires at least one timing scenario to determine "
                             "library corners.")
        scenario = list(scenarios.values())[0]
        libcorners = scenario.get_libcorner(self.step, self.index)
        delay_model = self.project.get("asic", "delaymodel")
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get_library(asiclib)
            for corner in libcorners:
                if not lib.valid("asic", "libcornerfileset", corner, delay_model):
                    continue
                self.add_required_key(lib, "asic", "libcornerfileset", corner, delay_model)
                for fileset in lib.get("asic", "libcornerfileset", corner, delay_model):
                    self.add_required_key(lib, "fileset", fileset, "file", "liberty")

    def __config_file(self) -> str:
        return "lec.yaml"

    def pre_process(self):
        super().pre_process()

        with open(self.__config_file(), "w") as f:
            f.write("format: verilog\n")
            f.write("input_paths:\n")
            for node in self.get_files_from_input_nodes()[f"{self.design_topmodule}.lec.vg"]:
                filename = self.compute_input_file_node_name(f"{self.design_topmodule}.lec.vg",
                                                             *node)
                f.write(f"  - inputs/{filename}\n")
            f.write("liberty_files:\n")

            scenario = list(self.project.constraint.timing.get_scenario().values())[0]
            libcorners = scenario.get_libcorner(self.step, self.index)
            delay_model = self.project.get("asic", "delaymodel")
            for asiclib in self.project.get("asic", "asiclib"):
                lib = self.project.get_library(asiclib)
                for corner in libcorners:
                    if not lib.valid("asic", "libcornerfileset", corner, delay_model):
                        continue
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
        # Kepler-formal writes its own log file; nothing to do here.
        errors = 0
        log = self.get_logpath('exe')
        if os.path.exists(log):
            with sc_open(log, 'r') as f:
                for logline in f:
                    if "Found difference " in logline:
                        errors += 1

            self.record_metric("drvs", errors, source_file=log)

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
