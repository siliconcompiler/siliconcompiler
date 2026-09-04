import os.path

from typing import List, Optional, Tuple

from siliconcompiler import Design, Task
from siliconcompiler.utils import sc_open


class SECTask(Task):
    """SEC task using Kepler-formal to check a netlist against the RTL it came from."""

    # kepler-formal reports a found difference by exit status as well as in the
    # log, and a difference is a verdict rather than a failure to run.
    _DIFFERENCE_FOUND = 3

    def __init__(self):
        super().__init__()

        self.add_parameter(
            "reset_port", "[str]",
            "Top-level reset ports to hold active while the state settles, each "
            "given as 'name=value' with a value of 0 or 1. SEC cannot check a "
            "design whose observed outputs depend on state that no reset "
            "anchors, so without this it reports that it cannot run rather than "
            "proving an equivalence that would not hold for arbitrary initial "
            "state.")
        self.add_parameter(
            "reset_cycles", "int",
            "Number of cycles to hold the reset ports active for. Has to cover "
            "the design's reset distribution, so a reset that arrives through "
            "synchronizers or a pipeline needs more than one.",
            defvalue=100)

    def add_reset_port(self, name: str, active_value: int = 1,
                       step: Optional[str] = None, index: Optional[str] = None,
                       clobber: bool = False) -> None:
        """
        Adds a top-level reset port to hold active while the state settles.

        Args:
            name (str): Name of the top-level reset port.
            active_value (int, optional): Value that asserts it, 0 or 1. Defaults to 1.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, replaces the existing list.
        """
        if active_value not in (0, 1):
            raise ValueError(f"reset port active value must be 0 or 1, not {active_value}")

        value = f"{name}={active_value}"
        if clobber:
            self.set("var", "reset_port", value, step=step, index=index)
        else:
            self.add("var", "reset_port", value, step=step, index=index)

    def set_reset_cycles(self, cycles: int,
                         step: Optional[str] = None, index: Optional[str] = None) -> None:
        """
        Sets how many cycles the reset ports are held active for.

        Args:
            cycles (int): Number of cycles.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "reset_cycles", cycles, step=step, index=index)

    def __reset_ports(self) -> List[Tuple[str, str]]:
        """Returns the (name, active value) of each configured reset port."""
        ports = []
        for entry in self.get("var", "reset_port"):
            name, _, value = entry.partition("=")
            if not name or value not in ("0", "1"):
                raise ValueError(f"reset port must be given as 'name=0' or 'name=1', "
                                 f"not {entry!r}")
            ports.append((name, value))
        return ports

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

        if self.get("var", "reset_port"):
            # Rejected here rather than at write time, so a malformed value is a
            # setup error and not a tool error twenty seconds later.
            self.__reset_ports()
            self.add_required_key("var", "reset_port")
            self.add_required_key("var", "reset_cycles")

    def __rtl_file(self) -> str:
        """Returns the elaborated RTL file, which is SystemVerilog if the design holds any."""
        verilog = f"{self.design_topmodule}.v"
        if verilog in self.get_files_from_input_nodes():
            return verilog
        return f"{self.design_topmodule}.sv"

    def __libcorners(self) -> List[Tuple[Design, str, str]]:
        """Returns the library, corner and delay model of each corner this node checks."""
        scenarios = self.project.constraint.timing.get_scenario()
        if not scenarios:
            raise ValueError("SEC requires at least one timing scenario to determine "
                             "library corners.")
        scenario = list(scenarios.values())[0]
        libcorners = scenario.get_libcorner(self.step, self.index)
        delay_model = self.project.get("asic", "delaymodel")

        corners = []
        for asiclib in self.project.get("asic", "asiclib"):
            lib = self.project.get_library(asiclib)
            for corner in libcorners:
                if lib.valid("asic", "libcornerfileset", corner, delay_model):
                    corners.append((lib, corner, delay_model))
        return corners

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
            reset_ports = self.__reset_ports()
            if reset_ports:
                f.write("sec_reset:\n")
                f.write(f"  cycles: {self.get('var', 'reset_cycles')}\n")
                f.write("  ports:\n")
                for name, value in reset_ports:
                    f.write(f"    - name: {name}\n")
                    f.write(f"      active_value: {value}\n")
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

    def run_task(self, *args, **kwargs) -> int:
        retcode = super().run_task(*args, **kwargs)

        # A found difference exits non-zero, and that is the answer rather than a
        # failure to produce one: post_process turns it into the drv. Anything
        # else stays as it is, so a design SEC refuses to check -- one whose
        # outputs all depend on state no reset anchors -- still fails the node.
        if retcode == self._DIFFERENCE_FOUND:
            return 0
        return retcode

    def post_process(self):
        super().post_process()

        # The verdict is in the log either way; run_task has already folded the
        # differing exit status away.
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
