'''
SymbiYosys (sby) is a front-end driver program for Yosys-based formal
hardware verification flows. It reads a job configuration file, runs
Yosys to elaborate the design into a formal model, and dispatches one
or more proof engines (smtbmc, btor, abc, aiger, ...) to prove or
disprove the SystemVerilog assertions in the design.

Documentation: https://symbiyosys.readthedocs.io

Sources: https://github.com/YosysHQ/sby

Installation: https://symbiyosys.readthedocs.io/en/latest/install.html
'''
import os

from typing import List, Optional, Union

from siliconcompiler import Task
from siliconcompiler.utils import link_copy, sc_open


class SBYTask(Task):
    '''Base class for SymbiYosys formal verification tasks.

    Concrete subclasses select the sby mode (bmc, prove, cover) via
    their task name. The task generates a .sby job file from the
    project's filesets and runs sby on it. Assertions must be present
    in the design (SVA ``assert``/``assume``/``cover`` properties); the
    sources are read with ``-formal`` so those statements are kept as
    proof obligations.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("depth", "int",
                           "Solver unrolling depth: the number of cycles checked in bmc/cover "
                           "mode, or the induction length in prove mode.",
                           defvalue=20)

        # bitwuzla is the default engine: it is the maintained successor to
        # boolector, and yosys >= 0.67's smtbmc drives it through its native
        # '--lang smt2' interface (0.66 could only drive it via the legacy '--smt2'
        # CLI, which modern bitwuzla dropped -- hence the >=0.67 version floor).
        self.add_parameter("engine", "[<smtbmc bitwuzla>]",
                           "Engine lines for the [engines] section of the sby job file. "
                           "Each entry is one line.",
                           defvalue=["smtbmc bitwuzla"])

    def tool(self):
        return "sby"

    def mode(self):
        '''sby verification mode; same as the task name.'''
        return self.task()

    def set_sby_depth(self, depth: int,
                      step: Optional[str] = None, index: Optional[str] = None):
        """Sets the solver unrolling depth (cycles for bmc/cover, induction length for prove)."""
        self.set("var", "depth", depth, step=step, index=index)

    def add_sby_engine(self, engine: Union[str, List[str]],
                       step: Optional[str] = None, index: Optional[str] = None,
                       clobber: bool = False):
        """Adds an sby engine line, e.g. 'smtbmc bitwuzla'.

        Args:
            engine (Union[str, List[str]]): engine line(s) for the [engines] section.
            step (str, optional): The step to apply the value to.
            index (str, optional): The index to apply the value to.
            clobber (bool, optional): If True, overwrites the existing engine list.
                                      If False, appends to it. Defaults to False.
        """
        if clobber:
            self.set("var", "engine", engine, step=step, index=index)
        else:
            self.add("var", "engine", engine, step=step, index=index)

    def setup(self):
        super().setup()

        # sby reports the yosys release it was built against, e.g. "SBY v0.67";
        # parse_version/normalize_version reduce that to "0.67". 0.67 is the first
        # release whose smtbmc drives the default bitwuzla engine via '--lang'.
        self.set_exe("sby", vswitch="--version")
        self.add_version(">=0.67")

        self.add_regex("warnings", r"^SBY .* WARNING")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="systemverilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "systemverilog")
            if lib.has_file(fileset=fileset, filetype="verilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        # top-level parameters are taken from the design only, not dependent libraries
        design = self.project.design
        for fileset in self.project.get("option", "fileset"):
            for param in design.getkeys("fileset", fileset, "param"):
                self.add_required_key(design, "fileset", fileset, "param", param)

        for var in ("depth", "engine"):
            self.add_required_key("var", var)

    def parse_version(self, stdout):
        # sby --version prints e.g. "SBY v0.66"
        return stdout.split()[-1]

    def normalize_version(self, version):
        # drop the leading 'v' from the git tag (e.g. "v0.66" -> "0.66")
        return version.lstrip("v")

    def _sby_workdir(self):
        '''Work directory (relative to the node work directory) sby runs the proof in.'''
        return "sby"

    def __sby_file(self):
        return f"{self.design_topmodule}.sby"

    def pre_process(self):
        super().pre_process()

        idirs = []
        defines = []
        sources = []
        for lib, fileset in self.project.get_filesets():
            for idir in lib.get_idir(fileset):
                if idir not in idirs:
                    idirs.append(idir)
            for define in lib.get("fileset", fileset, "define"):
                if define not in defines:
                    defines.append(define)
            for filetype in ("verilog", "systemverilog"):
                sources.extend(lib.get_file(fileset=fileset, filetype=filetype))

        # top-level parameters come from the design only
        params = []
        design = self.project.design
        for fileset in self.project.get("option", "fileset"):
            for param in design.getkeys("fileset", fileset, "param"):
                params.append((param, design.get("fileset", fileset, "param", param)))

        if not sources:
            raise ValueError("sby requires at least one verilog/systemverilog source file")

        read_opts = ["-formal", "-sv"]
        for idir in idirs:
            read_opts.append(f"-I{idir}")
        for define in defines:
            read_opts.append(f"-D{define}")

        with open(self.__sby_file(), "w") as f:
            f.write("[options]\n")
            f.write(f"mode {self.mode()}\n")
            f.write(f"depth {self.get('var', 'depth')}\n")
            timeout = self.project.option.get_timeout(step=self.step, index=self.index)
            if timeout:
                f.write(f"timeout {int(timeout)}\n")
            f.write("\n")

            f.write("[engines]\n")
            for engine in self.get("var", "engine"):
                f.write(f"{engine}\n")
            f.write("\n")

            # sby reads the sources directly from their original locations; no
            # [files] section is emitted so nothing is copied into the workdir.
            f.write("[script]\n")
            for src in sources:
                f.write(f"read_verilog {' '.join(read_opts)} {src}\n")
            for name, value in params:
                f.write(f"chparam -set {name} {value} {self.design_topmodule}\n")
            f.write(f"prep -top {self.design_topmodule}\n")

    def runtime_options(self):
        options = super().runtime_options()

        # -f: overwrite the work directory if it exists (needed for reruns)
        options.append("-f")
        options.extend(["-d", self._sby_workdir()])
        options.append(self.__sby_file())

        return options

    def post_process(self):
        super().post_process()

        status = None
        statusfile = os.path.join(self._sby_workdir(), "status")
        if os.path.exists(statusfile):
            with sc_open(statusfile) as f:
                content = f.read().strip()
            if content:
                status = content.split()[0]

        if status is not None:
            self.record_metric("errors", 0 if status == "PASS" else 1,
                               source_file=statusfile)

        # Preserve counterexample traces for debugging
        for root, _, files in os.walk(self._sby_workdir()):
            for fname in files:
                if fname.endswith((".vcd", ".fst")):
                    link_copy(os.path.join(root, fname),
                              os.path.join("reports", fname))
