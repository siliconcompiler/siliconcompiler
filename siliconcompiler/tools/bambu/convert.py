import os
import re
import shutil

import os.path

from typing import List, Optional, Union

from pathlib import Path

from siliconcompiler.utils import sc_open

from siliconcompiler import Task
from siliconcompiler.asic import ASICTask, CellArea
from siliconcompiler.tools._common import distinct


class ConvertTask(ASICTask, Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("memorychannels", "int<1..>", "Number of memory channels available",
                           defvalue=1)
        self.add_parameter("memorypolicy", "str",
                           "Bambu memory allocation policy, which decides how the "
                           "kernel's arrays are mapped onto memory (e.g. NO_BRAM, "
                           "ALL_BRAM, EXT_PIPELINED_BRAM).",
                           defvalue="NO_BRAM")
        self.add_parameter("experimentalsetup", "str",
                           "Bambu experimental setup, which selects the preset of "
                           "optimizations and scheduling options to synthesize with "
                           "(e.g. BAMBU-BALANCED-MP). Empty leaves bambu on its own "
                           "default.")
        self.add_parameter("compiler", "str",
                           "Front end compiler bambu uses to read its inputs "
                           "(e.g. I386_CLANG16). Empty leaves bambu to pick one.")
        self.add_parameter("simulate", "bool",
                           "simulate the generated RTL. This is what produces the cycle "
                           "counts; without it bambu reports area and timing estimates "
                           "only. Needs a testbench.",
                           defvalue=False)
        self.add_parameter("simulator", "<modelsim,xsim,verilator>",
                           "simulator bambu drives when 'simulate' is set",
                           defvalue="verilator")
        self.add_parameter("verilatorparallel", "int<0..>",
                           "threads verilator simulates with, when 'simulator' is "
                           "verilator. 0 emits the bare flag and lets verilator choose.",
                           defvalue=0)
        self.add_parameter("printdot", "bool",
                           "dump the tool's internal graphs as graphviz .dot files. "
                           "Useful for seeing what the scheduler and binder did, and "
                           "verbose enough that it is off by default.",
                           defvalue=False)
        self.add_parameter("constraintsfile", "file",
                           "Bambu constraints XML, the second positional input in "
                           "'bambu <source> [constraints] [technology]'.")
        self.add_parameter("technologyfile", "file",
                           "Bambu technology XML describing modules to bind against, "
                           "the third positional input. This is what an instrumentation "
                           "IP's module library is.")
        self.add_parameter("cnoparse", "[file]",
                           "C files bambu links into the testbench but does not "
                           "synthesize, passed as --C-no-parse. Used by IP integration "
                           "for the co-simulation half of an instrumentation IP.")
        self.add_parameter("fileinputdata", "[file]",
                           "extra files the specification refers to, passed as "
                           "--file-input-data. For IP integration these are the Verilog "
                           "sources of the components bound in from the technology XML.")
        self.add_parameter("componentslibrary", "bool",
                           "export Bambu's standard RTL components as a separate "
                           "library, which IP integration needs so the bound-in "
                           "components resolve.",
                           defvalue=False)
        self.add_parameter("testbench_fileset", "[(str,str)]",
                           "filesets holding the testbench to simulate against: either a "
                           "testbench XML, or a C/C++ file whose main() calls the "
                           "top-level function. Its files are excluded from the sources "
                           "bambu synthesizes, so the testbench can live in a fileset the "
                           "project has selected.")

    def set_bambu_constraintsfile(self, path: Union[str, Path],
                                  dataroot: Optional[str] = None,
                                  step: Optional[str] = None,
                                  index: Optional[str] = None) -> None:
        """Sets the Bambu constraints XML.

        Args:
            path: Path to the constraints XML.
            dataroot: The dataroot used to resolve relative paths.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("var", "constraintsfile", path, step=step, index=index)

    def set_bambu_technologyfile(self, path: Union[str, Path],
                                 dataroot: Optional[str] = None,
                                 step: Optional[str] = None,
                                 index: Optional[str] = None) -> None:
        """Sets the Bambu technology XML.

        Args:
            path: Path to the technology XML, e.g. an IP's module library.
            dataroot: The dataroot used to resolve relative paths.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            self.set("var", "technologyfile", path, step=step, index=index)

    def add_bambu_cnoparse(self, path: Union[List[Union[str, Path]], str, Path],
                           dataroot: Optional[str] = None,
                           step: Optional[str] = None, index: Optional[str] = None,
                           clobber: bool = False) -> None:
        """Adds a C file bambu compiles for co-simulation but does not synthesize.

        Args:
            path: Path(s) to the C file(s).
            dataroot: The dataroot used to resolve relative paths.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
            clobber: If True, replaces the list instead of appending to it.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "cnoparse", path, step=step, index=index)
            else:
                self.add("var", "cnoparse", path, step=step, index=index)

    def add_bambu_fileinputdata(self, path: Union[List[Union[str, Path]], str, Path],
                                dataroot: Optional[str] = None,
                                step: Optional[str] = None, index: Optional[str] = None,
                                clobber: bool = False) -> None:
        """Adds a file the specification refers to, such as an IP's Verilog source.

        Args:
            path: Path(s) to the file(s).
            dataroot: The dataroot used to resolve relative paths.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
            clobber: If True, replaces the list instead of appending to it.
        """
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                self.set("var", "fileinputdata", path, step=step, index=index)
            else:
                self.add("var", "fileinputdata", path, step=step, index=index)

    def set_bambu_componentslibrary(self, value: bool,
                                    step: Optional[str] = None,
                                    index: Optional[str] = None) -> None:
        """Enables exporting Bambu's standard RTL components as a separate library.

        Args:
            value: True to export the components library.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
        """
        self.set("var", "componentslibrary", value, step=step, index=index)

    def set_bambu_verilatorparallel(self, threads: int,
                                    step: Optional[str] = None,
                                    index: Optional[str] = None) -> None:
        """Sets how many threads verilator simulates with.

        Only reaches the command line when 'simulator' is verilator, which is
        the only simulator bambu passes this to.

        Args:
            threads: Thread count, or 0 to emit the bare flag and let verilator
                decide.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
        """
        self.set("var", "verilatorparallel", threads, step=step, index=index)

    def set_bambu_printdot(self, value: bool,
                           step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Enables dumping the tool's internal graphs as graphviz .dot files.

        Args:
            value: True to dump the graphs.
            step: The specific synthesis step to which this setting applies.
            index: The specific index of the step.
        """
        self.set("var", "printdot", value, step=step, index=index)

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

    def set_bambu_memorypolicy(self, policy: str,
                               step: Optional[str] = None,
                               index: Optional[str] = None) -> None:
        """Sets the Bambu memory allocation policy.

        The policy decides how the kernel's arrays are mapped onto memory, which
        is the choice that most changes what the generated RTL looks like: the
        default ``NO_BRAM`` leaves them in external memory the accelerator reads
        through its channels, while ``ALL_BRAM`` puts them in block RAM inside it.

        Args:
            policy: The policy name.
            step: The step to associate with this setting. Defaults to None.
            index: The index to associate with this setting. Defaults to None.
        """
        self.set("var", "memorypolicy", policy, step=step, index=index)

    def set_bambu_experimentalsetup(self, setup: str,
                                    step: Optional[str] = None,
                                    index: Optional[str] = None) -> None:
        """Sets the Bambu experimental setup.

        An experimental setup is a named preset of the optimization and
        scheduling options bambu synthesizes with; ``BAMBU-BALANCED-MP`` is the
        one the SODA Synthesizer uses.

        Args:
            setup: The setup name. An empty string leaves bambu on its default.
            step: The step to associate with this setting. Defaults to None.
            index: The index to associate with this setting. Defaults to None.
        """
        self.set("var", "experimentalsetup", setup, step=step, index=index)

    def set_bambu_compiler(self, compiler: str,
                           step: Optional[str] = None,
                           index: Optional[str] = None) -> None:
        """Sets the front end compiler bambu reads its inputs with.

        bambu bundles several clang front ends and picks one by name, e.g.
        ``I386_CLANG16``. Which one matters for LLVM IR input: it has to be new
        enough to parse the IR the front end produced.

        Args:
            compiler: The compiler name. An empty string leaves bambu to pick.
            step: The step to associate with this setting. Defaults to None.
            index: The index to associate with this setting. Defaults to None.
        """
        self.set("var", "compiler", compiler, step=step, index=index)

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
            simulator: One of 'modelsim', 'xsim' or 'verilator'. bambu names
                these in upper case on its command line; the conversion happens
                on the way out.
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

    def __mainlib(self):
        """The main standard cell library, or None if no target selected one.

        ['asic', 'mainlib'] is a valid keypath on any ASIC project but stays
        empty until a target fills it in, so its validity says nothing about
        whether there is a library to ask.
        """
        if not self.project.valid("asic", "mainlib"):
            return None
        if not self.project.get("asic", "mainlib"):
            return None
        return self.mainlib

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
        self.add_required_key("var", "memorypolicy")
        self.add_required_key("var", "printdot")
        self.add_required_key("var", "componentslibrary")
        for var in ("constraintsfile", "technologyfile", "cnoparse", "fileinputdata"):
            if self.get("var", var):
                self.add_required_key("var", var)
        if self.get("var", "experimentalsetup"):
            self.add_required_key("var", "experimentalsetup")
        if self.get("var", "compiler"):
            self.add_required_key("var", "compiler")

        self.add_required_key("var", "simulate")
        if self.get("var", "simulate"):
            self.add_required_key("var", "simulator")
            self.add_required_key("var", "verilatorparallel")

            staged_testbench = self.__staged_testbench()
            if staged_testbench:
                self.add_input_file(file=staged_testbench)
            else:
                # Required whether or not it is set: with no upstream testbench
                # either, simulation is not a run bambu can make, so an empty
                # fileset has to reach the required-key check rather than be
                # passed over here.
                self.add_required_key("var", "testbench_fileset")
                for lib, fileset in self.__testbench_files():
                    for filetype in ConvertTask.TESTBENCH_FILETYPES:
                        if lib.has_file(fileset=fileset, filetype=filetype):
                            self.add_required_key(lib, "fileset", fileset, "file", filetype)

        if self.__has_staged_ir():
            self.add_input_file(ext="ll")
        else:
            # Only the source path reads these. When an upstream node supplies
            # the IR they describe a compilation that already happened, so
            # declaring them required would make this node's inputs -- and so
            # its cache key, and what a remote run copies -- depend on files it
            # never opens.
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

    def __has_staged_ir(self):
        """Reports whether an upstream node supplies the LLVM IR to synthesize.

        That is how the MLIR based front ends (soda) reach bambu: they produce
        the IR, and the design's filesets hold the MLIR it was generated from
        rather than anything bambu can read.
        """
        return f"{self.design_topmodule}.ll" in self.get_files_from_input_nodes()

    def __staged_testbench(self):
        """The testbench file an upstream node produced, or None.

        soda-opt writes a testbench for the kernel it outlines, so a flow that
        ran it has already produced the testbench for the IR it hands over, and
        the node needs no fileset of its own. Either form --generate-tb takes
        will do: the C testbench soda-opt emits by default, or the XML test
        vectors it emits instead when asked for them. The C one wins when both
        are there, being what the reference flow simulates against.

        Note that soda-opt's other XML, <kernel>_interface.xml, is a description
        of the kernel's arguments rather than a testbench, and bambu has no
        option that reads it.

        An explicitly named fileset still wins: this is the fallback, not an
        override.
        """
        if self.get("var", "testbench_fileset"):
            return None
        staged = self.get_files_from_input_nodes()
        for name in (f"{self.design_topmodule}_testbench.c",
                     f"{self.design_topmodule}_test.xml"):
            if name in staged:
                return name
        return None

    def __source_options(self):
        """The input bambu synthesizes, and the flags for compiling it.

        Include paths and defines belong to the C front end, so they are emitted
        only when bambu is the one doing that compilation.
        """
        if self.__has_staged_ir():
            return [os.path.join("inputs", f"{self.design_topmodule}.ll")]

        options = []
        filesets = self.project.get_filesets()

        idirs = []
        defines = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))

        for idir in distinct(idirs):
            options.append(f"-I{idir}")
        for define in distinct(defines):
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
        options.extend(distinct(sources))

        return options

    def runtime_options(self):
        options = super().runtime_options()

        options.extend(self.__source_options())

        # bambu's positional inputs, in the order its usage states them:
        # "<source_file> [<constraints_file>] [<technology_file>]".
        for var in ("constraintsfile", "technologyfile"):
            if self.get("var", var):
                options.append(self.find_files("var", var))

        # Comma-separated lists, which is how bambu parses both of these.
        for var, flag in (("cnoparse", "--C-no-parse"),
                          ("fileinputdata", "--file-input-data")):
            files = self.find_files("var", var)
            if files:
                options.append(f'{flag}={",".join(files)}')

        if self.get("var", "componentslibrary"):
            options.append('--generate-components-library')

        compiler = self.get("var", "compiler")
        if compiler:
            options.append(f'--compiler={compiler}')

        # The resource summary post_process() reads is only printed at this
        # verbosity, so it is not a knob: lowering it would silently stop the
        # report being produced.
        options.append('-v3')

        if self.get("var", "printdot"):
            options.append('--print-dot')

        # -lm goes with --soft-float: the soft-float lowering emits calls into
        # libm, which bambu then has to have a definition for.
        options.append('-lm')
        options.append('--soft-float')
        options.append(f'--memory-allocation-policy={self.get("var", "memorypolicy")}')

        setup = self.get("var", "experimentalsetup")
        if setup:
            options.append(f'--experimental-setup={setup}')

        mem_channels = self.get("var", "memorychannels")
        if mem_channels > 0:
            options.append(f'--channels-number={mem_channels}')

        if self.get("var", "simulate"):
            staged_testbench = self.__staged_testbench()
            if staged_testbench:
                options.append(f'--generate-tb={os.path.join("inputs", staged_testbench)}')
            else:
                testbenches = []
                for lib, fileset in self.__testbench_files():
                    for filetype in ConvertTask.TESTBENCH_FILETYPES:
                        testbenches.extend(lib.find_files("fileset", fileset, "file", filetype,
                                                          missing_ok=True))
                for testbench in distinct(testbenches):
                    options.append(f'--generate-tb={testbench}')
            options.append('--simulate')
            # bambu spells these in upper case; the schema holds them lower so
            # the accepted set reads like every other enum in the tree.
            options.append(f'--simulator={self.get("var", "simulator").upper()}')
            if self.get("var", "simulator") == "verilator":
                threads = self.get("var", "verilatorparallel")
                if threads:
                    options.append(f'--verilator-parallel={threads}')
                else:
                    options.append('--verilator-parallel')

        _, clk_period = self.get_clock()
        if clk_period is not None:
            clock_multiplier = 1.0
            # the multiplier is a property of the main library, which a project that
            # only runs the conversion need not have selected
            mainlib = self.__mainlib()
            if mainlib and mainlib.valid("tool", "bambu", "clock_multiplier"):
                clock_multiplier = mainlib.get("tool", "bambu", "clock_multiplier")
            clk_period *= clock_multiplier
            # --clock-name names the clock port of the generated RTL, which the SDC
            # then constrains, so it has to be the port the SDC creates its clock on
            # and not the name of that clock.
            clk_port = self.get_clock_port()
            if clk_port:
                options.append(f'--clock-name={clk_port}')
            options.append(f'--clock-period={clk_period}')

        options.append('--disable-function-proxy')

        # Only a library that knows about bambu carries a device name for it.
        mainlib = self.__mainlib()
        if mainlib and mainlib.valid("tool", "bambu", "device"):
            device = mainlib.get("tool", "bambu", "device")
            if device:
                options.append(f'--device={device}')

        options.append(f'--top-fname={self.design_topmodule}')

        return options

    def post_process(self):
        super().post_process()

        shutil.copy2(f'{self.design_topmodule}.v', os.path.join('outputs',
                                                                f'{self.design_topmodule}.v'))

        # --print-dot writes one graph per function per stage into a tree whose
        # shape depends on the design, so these cannot be declared outputs --
        # outputs/ is checked against the declared list and an undeclared file
        # there fails the node. They are debugging artifacts, so they belong in
        # reports/ alongside the resource summary.
        if self.get("var", "printdot"):
            dot_dir = os.path.join("HLS_output", "dot")
            if os.path.isdir(dot_dir):
                shutil.copytree(dot_dir, os.path.join("reports", "dot"),
                                dirs_exist_ok=True)

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
