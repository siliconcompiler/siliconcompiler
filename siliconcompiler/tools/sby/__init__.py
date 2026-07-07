'''
SymbiYosys (sby) is a front-end driver program for Yosys-based formal
hardware verification flows. It reads a job configuration file, runs
Yosys to elaborate the design into a formal model, and dispatches one
or more proof engines (smtbmc with boolector/bitwuzla/z3, btor, abc,
aiger, ...) to prove or disprove the SystemVerilog assertions in the
design.

Documentation: https://symbiyosys.readthedocs.io

Sources: https://github.com/YosysHQ/sby

Installation: https://symbiyosys.readthedocs.io/en/latest/install.html
'''
import os
import shutil

from siliconcompiler import Task
from siliconcompiler.utils import sc_open


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

        self.add_parameter("engine", "[str]",
                           "Engine lines for the [engines] section of the sby job file, e.g. "
                           "'smtbmc bitwuzla' or 'smtbmc boolector'. Each entry is one line.",
                           defvalue=["smtbmc bitwuzla"])

        self.add_parameter("timeout", "int",
                           "Timeout in seconds for the proof engines (sby [options] timeout). "
                           "0 disables the timeout.",
                           defvalue=0)

        self.add_parameter("toolroot", "dir",
                           "Installation prefix of the formal toolchain to use (containing "
                           "bin/sby, bin/yosys, bin/yosys-smtbmc, ...). When set, this prefix "
                           "is prepended to PATH and passed to sby via --yosys/--smtbmc/... so "
                           "the tools in this prefix are used even if others exist on PATH.")

    def tool(self):
        return "sby"

    def mode(self):
        '''sby verification mode; same as the task name.'''
        return self.task()

    def set_depth(self, depth, step=None, index=None):
        """Sets the solver unrolling depth (cycles for bmc/cover, induction length for prove)."""
        self.set("var", "depth", depth, step=step, index=index)

    def set_engine(self, engine, step=None, index=None):
        """Sets the sby engine line(s), e.g. 'smtbmc bitwuzla'."""
        self.set("var", "engine", engine, step=step, index=index)

    def set_timeout(self, timeout, step=None, index=None):
        """Sets the proof engine timeout in seconds (0 disables)."""
        self.set("var", "timeout", timeout, step=step, index=index)

    def set_toolroot(self, toolroot, step=None, index=None):
        """Sets the installation prefix of the formal toolchain to use."""
        self.set("var", "toolroot", toolroot, step=step, index=index)

    def setup(self):
        super().setup()

        # The upstream sby git build reports a versionless "SBY" banner, so no
        # vswitch/version specifiers: the version check is skipped entirely.
        self.set_exe("sby")

        toolroot = self.get("var", "toolroot")
        if toolroot:
            self.set_path(os.path.join(toolroot, "bin"))
            libpaths = [os.path.join(toolroot, lib) for lib in ("lib", "lib64")]
            libpaths = [path for path in libpaths if os.path.isdir(path)]
            if os.environ.get("LD_LIBRARY_PATH"):
                libpaths.append(os.environ["LD_LIBRARY_PATH"])
            if libpaths:
                self.set_environmentalvariable("LD_LIBRARY_PATH", os.pathsep.join(libpaths))

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

        for var in ("depth", "engine", "timeout"):
            self.add_required_key("var", var)

    def sby_workdir(self):
        '''Work directory (relative to the node work directory) sby runs the proof in.'''
        return "sby"

    def __sby_file(self):
        return f"{self.design_topmodule}.sby"

    def __collect_sources(self):
        '''Collects (dst, src) pairs for the [files] section.

        sby copies each source into <workdir>/src/<dst>; dst must be a
        relative path, so files are referenced by basename with a prefix
        added on collision.
        '''
        sources = []
        seen = set()
        for lib, fileset in self.project.get_filesets():
            for filetype in ("systemverilog", "verilog"):
                for src in lib.get_file(fileset=fileset, filetype=filetype):
                    dst = os.path.basename(src)
                    if dst in seen:
                        dst = f"f{len(sources)}_{dst}"
                    seen.add(dst)
                    sources.append((dst, src, filetype))
        return sources

    def pre_process(self):
        super().pre_process()

        idirs = []
        defines = []
        for lib, fileset in self.project.get_filesets():
            for idir in lib.get_idir(fileset):
                if idir not in idirs:
                    idirs.append(idir)
            for define in lib.get("fileset", fileset, "define"):
                if define not in defines:
                    defines.append(define)

        read_opts = ["-formal", "-sv"]
        for idir in idirs:
            read_opts.append(f"-I{idir}")
        for define in defines:
            read_opts.append(f"-D{define}")

        sources = self.__collect_sources()
        if not sources:
            raise ValueError("sby requires at least one verilog/systemverilog source file")

        with open(self.__sby_file(), "w") as f:
            f.write("[options]\n")
            f.write(f"mode {self.mode()}\n")
            f.write(f"depth {self.get('var', 'depth')}\n")
            timeout = self.get("var", "timeout")
            if timeout:
                f.write(f"timeout {timeout}\n")
            f.write("\n")

            f.write("[engines]\n")
            for engine in self.get("var", "engine"):
                f.write(f"{engine}\n")
            f.write("\n")

            f.write("[script]\n")
            for dst, _, _ in sources:
                f.write(f"read_verilog {' '.join(read_opts)} {dst}\n")
            f.write(f"prep -top {self.design_topmodule}\n")
            f.write("\n")

            f.write("[files]\n")
            for dst, src, _ in sources:
                f.write(f"{dst} {src}\n")

    def runtime_options(self):
        options = super().runtime_options()

        toolroot = self.get("var", "toolroot")
        if toolroot:
            for opt, exe in (("--yosys", "yosys"),
                             ("--abc", "yosys-abc"),
                             ("--smtbmc", "yosys-smtbmc"),
                             ("--witness", "yosys-witness"),
                             ("--btormc", "btormc")):
                path = os.path.join(toolroot, "bin", exe)
                if os.path.exists(path):
                    options.extend([opt, path])

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
                    shutil.copy2(os.path.join(root, fname),
                                 os.path.join("reports", fname))
