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

        # Only boolector is offered for now: yosys' smtbmc in this release drives
        # the solver through the legacy '--smt2' CLI, which the rewritten bitwuzla
        # (every numbered release) dropped. bitwuzla can be re-added once yosys is
        # bumped to a smtbmc that speaks bitwuzla's native '--lang' interface.
        self.add_parameter("engine", "[<smtbmc boolector>]",
                           "Engine lines for the [engines] section of the sby job file. "
                           "Each entry is one line.",
                           defvalue=["smtbmc boolector"])

    def tool(self):
        return "sby"

    def mode(self):
        '''sby verification mode; same as the task name.'''
        return self.task()

    def set_sby_depth(self, depth):
        """Sets the solver unrolling depth (cycles for bmc/cover, induction length for prove)."""
        self.set("var", "depth", depth)

    def add_sby_engine(self, engine, clobber=False):
        """Adds an sby engine line, e.g. 'smtbmc boolector'.

        Args:
            engine (Union[str, List[str]]): engine line(s) for the [engines] section.
            clobber (bool, optional): If True, overwrites the existing engine list.
                                      If False, appends to it. Defaults to False.
        """
        if clobber:
            self.set("var", "engine", engine)
        else:
            self.add("var", "engine", engine)

    def setup(self):
        super().setup()

        # sby reports the yosys release it was built against (e.g. "SBY v0.66");
        # we rely on the pinned toolchain rather than gating on a runtime version.
        self.set_exe("sby")

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
            for param in lib.getkeys("fileset", fileset, "param"):
                self.add_required_key(lib, "fileset", fileset, "param", param)
            if lib.has_file(fileset=fileset, filetype="systemverilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "systemverilog")
            if lib.has_file(fileset=fileset, filetype="verilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        for var in ("depth", "engine"):
            self.add_required_key("var", var)

    def sby_workdir(self):
        '''Work directory (relative to the node work directory) sby runs the proof in.'''
        return "sby"

    def __sby_file(self):
        return f"{self.design_topmodule}.sby"

    def pre_process(self):
        super().pre_process()

        idirs = []
        defines = []
        params = []
        sources = []
        for lib, fileset in self.project.get_filesets():
            for idir in lib.get_idir(fileset):
                if idir not in idirs:
                    idirs.append(idir)
            for define in lib.get("fileset", fileset, "define"):
                if define not in defines:
                    defines.append(define)
            for param in lib.getkeys("fileset", fileset, "param"):
                params.append((param, lib.get("fileset", fileset, "param", param)))
            for filetype in ("verilog", "systemverilog"):
                sources.extend(lib.get_file(fileset=fileset, filetype=filetype))

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
        options.extend(["-d", self.sby_workdir()])
        options.append(self.__sby_file())

        return options

    def post_process(self):
        super().post_process()

        status = None
        statusfile = os.path.join(self.sby_workdir(), "status")
        if os.path.exists(statusfile):
            with sc_open(statusfile) as f:
                content = f.read().strip()
            if content:
                status = content.split()[0]

        if status is not None:
            self.record_metric("errors", 0 if status == "PASS" else 1,
                               source_file=statusfile)

        # Preserve counterexample traces for debugging
        for root, _, files in os.walk(self.sby_workdir()):
            for fname in files:
                if fname.endswith((".vcd", ".fst")):
                    link_copy(os.path.join(root, fname),
                              os.path.join("reports", fname))
