import os
import re
import shutil

import os.path

from typing import Optional

from siliconcompiler.utils import sc_open

from siliconcompiler import Task
from siliconcompiler.asic import ASICTask, CellArea
from siliconcompiler.tools._common import distinct


class ConvertTask(ASICTask, Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("memorychannels", "int<1..>", "Number of memory channels available",
                           defvalue=1)
        self.add_parameter("simulate", "bool",
                           "simulate the generated RTL. This is what produces the cycle "
                           "counts; without it bambu reports area and timing estimates "
                           "only. Needs a testbench.",
                           defvalue=False)
        self.add_parameter("simulator", "str",
                           "simulator bambu drives when 'simulate' is set "
                           "(MODELSIM, XSIM or VERILATOR)",
                           defvalue="VERILATOR")
        self.add_parameter("testbench_fileset", "[(str,str)]",
                           "filesets holding the testbench to simulate against: either a "
                           "testbench XML, or a C/C++ file whose main() calls the "
                           "top-level function. Its files are excluded from the sources "
                           "bambu synthesizes, so the testbench can live in a fileset the "
                           "project has selected.")

    def set_bambu_memorychannels(self, channels: int,
                                 step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the number of memory channels for the Bambu synthesizer.

        This method configures the 'memorychannels' variable within the Bambu
        tool flow. It's used to specify the number of independent memory
        channels the synthesized hardware should have.

        Args:
            channels: The number of memory channels to configure.
            step: The specific synthesis step to which this setting applies.
                  If None, it applies globally. Defaults to None.
            index: The index for the step, used if a step can have multiple
                   configurations. Defaults to None.
        """
        self.set("var", "memorychannels", channels, step=step, index=index)

    def set_bambu_simulate(self, value: bool,
                           step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Enables or disables simulating the generated RTL.

        Simulation is what produces the cycle counts; without it bambu reports
        its area and timing estimates only. It needs a testbench, so setting
        this without one is an error rather than a silent no-op.

        Args:
            value: Whether to simulate.
            step: The step to associate with this setting. Defaults to None.
            index: The index to associate with this setting. Defaults to None.
        """
        self.set("var", "simulate", value, step=step, index=index)

    def set_bambu_simulator(self, simulator: str,
                            step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the simulator bambu drives.

        Args:
            simulator: One of MODELSIM, XSIM or VERILATOR.
            step: The step to associate with this setting. Defaults to None.
            index: The index to associate with this setting. Defaults to None.
        """
        self.set("var", "simulator", simulator, step=step, index=index)

    def add_bambu_testbenchfileset(self, library: str, fileset: str,
                                   clobber: bool = False) -> None:
        """Adds a fileset holding the testbench to simulate against.

        The fileset carries either a testbench XML or a C/C++ file whose main()
        calls the top-level function; the MLIR front ends emit one of the latter
        alongside the kernel. Its files are kept out of the sources bambu
        synthesizes, so the testbench can sit in a fileset the project selected
        without being compiled into the design.

        Args:
            library: Name of the library owning the fileset.
            fileset: Name of the fileset.
            clobber: If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "testbench_fileset", (library, fileset))
        else:
            self.add("var", "testbench_fileset", (library, fileset))

    #: What bambu accepts for --generate-tb: a testbench XML, or C/C++ with a main().
    TESTBENCH_FILETYPES = ("c", "xml")

    def __testbench_filesets(self):
        """The (library, fileset) pairs naming the testbench, as a set of names."""
        return {(library, fileset)
                for library, fileset in self.get("var", "testbench_fileset")}

    def __testbench_files(self):
        """Resolves the testbench filesets to (library object, fileset) pairs."""
        resolved = []
        for library, fileset in self.get("var", "testbench_fileset"):
            resolved.extend(self.project.get_filesets(library=library, filesets=[fileset]))
        return resolved

    def tool(self):
        return "bambu"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # Long multiline output, but second-to-last line looks like:
        # Version: PandA 0.9.6 - Revision 5e5e306b86383a7d85274d64977a3d71fdcff4fe-main
        version_line = stdout.split('\n')[-3]
        return version_line.split()[2]

    def setup(self):
        super().setup()

        self.set_exe("bambu", vswitch="--version")
        self.add_version(">=2024.03")

        self.set_threads(1)

        self.add_output_file(ext="v")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # memorychannels is read unconditionally in runtime_options (has a defvalue)
        self.add_required_key("var", "memorychannels")

        self.add_required_key("var", "simulate")
        if self.get("var", "simulate"):
            if not self.get("var", "testbench_fileset"):
                raise ValueError(
                    f"{self.tool()}/{self.task()}: simulation needs a testbench; "
                    "add the fileset holding it with add_bambu_testbenchfileset()")
            self.add_required_key("var", "simulator")
            self.add_required_key("var", "testbench_fileset")
            for lib, fileset in self.__testbench_files():
                for filetype in ConvertTask.TESTBENCH_FILETYPES:
                    if lib.has_file(fileset=fileset, filetype=filetype):
                        self.add_required_key(lib, "fileset", fileset, "file", filetype)

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="c"):
                self.add_required_key(lib, "fileset", fileset, "file", "c")
            elif lib.has_file(fileset=fileset, filetype="llvm"):
                self.add_required_key(lib, "fileset", fileset, "file", "llvm")

        # sdc files are read by get_clock() in runtime_options for clock extraction
        self._add_clock_required_keys()

    def runtime_options(self):
        options = super().runtime_options()

        filesets = self.project.get_filesets()
        idirs = []
        defines = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))
        idirs = distinct(idirs)
        defines = distinct(defines)

        for idir in idirs:
            options.append(f"-I{idir}")

        for define in defines:
            options.append(f"-D{define}")

        testbench_filesets = self.__testbench_filesets()

        sources = []
        for lib, fileset in filesets:
            # A testbench is not part of the design, and a project that selected
            # its fileset would otherwise compile it into one.
            if (lib.name, fileset) in testbench_filesets:
                continue
            if lib.get_file(fileset=fileset, filetype="c"):
                sources.extend(lib.get_file(fileset=fileset, filetype="c"))
            elif lib.get_file(fileset=fileset, filetype="llvm"):
                sources.extend(lib.get_file(fileset=fileset, filetype="llvm"))
        for value in distinct(sources):
            options.append(value)

        # The resource summary post_process() reads is only printed at this
        # verbosity, so it is not a knob: lowering it would silently stop the
        # report being produced.
        options.append('-v3')

        options.append('--soft-float')
        options.append('--memory-allocation-policy=NO_BRAM')

        mem_channels = self.get("var", "memorychannels")
        if mem_channels > 0:
            options.append(f'--channels-number={mem_channels}')

        if self.get("var", "simulate"):
            testbenches = []
            for lib, fileset in self.__testbench_files():
                for filetype in ConvertTask.TESTBENCH_FILETYPES:
                    testbenches.extend(lib.find_files("fileset", fileset, "file", filetype,
                                                      missing_ok=True))
            for testbench in distinct(testbenches):
                options.append(f'--generate-tb={testbench}')
            options.append('--simulate')
            options.append(f'--simulator={self.get("var", "simulator")}')

        _, clk_period = self.get_clock()
        if clk_period is not None:
            clock_multiplier = 1.0
            # the multiplier is a property of the main library, which a project that
            # only runs the conversion need not have selected
            if self.project.valid("asic", "mainlib") and \
                    self.mainlib.valid("var", "bambu_clock_multiplier"):
                clock_multiplier = self.mainlib.get("var", "bambu_clock_multiplier")
            clk_period *= clock_multiplier
            # --clock-name names the clock port of the generated RTL, which the SDC
            # then constrains, so it has to be the port the SDC creates its clock on
            # and not the name of that clock.
            clk_port = self.get_clock_port()
            if clk_port:
                options.append(f'--clock-name={clk_port}')
            options.append(f'--clock-period={clk_period}')

        options.append('--disable-function-proxy')

        if self.project.valid("asic", "mainlib"):
            device = self.project.get("library",
                                      self.project.get("asic", "mainlib"),
                                      "tool", "bambu", "device")
            if device:
                options.append(f'--device={device}')

        options.append(f'--top-fname={self.design_topmodule}')

        return options

    def post_process(self):
        super().post_process()

        shutil.copy2(f'{self.design_topmodule}.v', os.path.join('outputs',
                                                                f'{self.design_topmodule}.v'))

        ff = re.compile(fr"Total number of flip-flops in function {self.design_topmodule}: (\d+)")
        area = re.compile(r"Total estimated area: (\d+)")
        fmax = re.compile(r"Estimated max frequency \(MHz\): (\d+\.?\d*)")
        slack = re.compile(r"Minimum slack: (\d+\.?\d*)")

        # A whole-design tally of the functional units the scheduler allocated,
        # printed as a header followed by one indented entry per unit and ended
        # by the first line that is not one (or by the end of the log).
        resource_header = re.compile(r"^\s*Summary of resources:\s*$")
        resource_entry = re.compile(r"^\s+-\s+(\S+):\s+(\d+)\s*$")

        # Only printed when bambu simulates the RTL it generated, which this
        # task does not ask it to do.
        cycles = re.compile(r"^\s*Total cycles\s*:\s*(\d+)")

        resources = {}
        in_resources = False

        log_file = self.get_logpath("exe")
        with sc_open(log_file) as log:
            for line in log:
                if in_resources:
                    entry = resource_entry.match(line)
                    if entry:
                        resources[entry.group(1)] = int(entry.group(2))
                        continue
                    in_resources = False

                if resource_header.match(line):
                    in_resources = True
                    continue

                cycles_match = cycles.match(line)
                if cycles_match:
                    # There is no cycles metric in the schema yet, so this is
                    # recorded quietly rather than warning on every run: it
                    # starts landing the day one is added.
                    self.record_metric("cycles", int(cycles_match.group(1)), log_file,
                                       quiet=True)
                    continue

                ff_match = ff.findall(line)
                area_match = area.findall(line)
                fmax_match = fmax.findall(line)
                slack_match = slack.findall(line)
                if ff_match:
                    self.record_metric("registers", int(ff_match[0]), log_file)
                if area_match:
                    self.record_metric("cellarea", float(area_match[0]), log_file,
                                       source_unit='um^2')
                if fmax_match:
                    self.record_metric("fmax", float(fmax_match[0]), log_file, source_unit='MHz')
                if slack_match:
                    slack_ns = float(slack_match[0])
                    if slack_ns >= 0:
                        self.record_metric("setupwns", 0, log_file, source_unit='ns')
                    else:
                        self.record_metric("setupwns", slack_ns, log_file, source_unit='ns')
                    self.record_metric("setupslack", slack_ns, log_file, source_unit='ns')

        if resources:
            # Reported the same way synthesis reports its cells, so the two can
            # be read by the same tooling. Only the count is known: these are
            # functional units the HLS scheduler allocated, which have no area
            # until something maps them onto a technology.
            report = CellArea()
            for name, count in sorted(resources.items()):
                report.add_cell(name=name, module=name, cellcount=count)
            report.write_report("reports/resource_usage.json")
