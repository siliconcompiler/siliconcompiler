import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Union, Dict, List
import xml.etree.ElementTree as ET

from siliconcompiler import Task
from siliconcompiler.tool import TaskExecutableNotFound
from siliconcompiler.utils import paths
from siliconcompiler.tools._common.cocotb import python_env

try:
    import cocotb_tools.config
    import find_libpython
    _has_cocotb = True
except ModuleNotFoundError:
    _has_cocotb = False


def _require_cocotb(what):
    if not _has_cocotb:
        raise NotImplementedError(f"COCOTB must be installed to use {what}")


def get_cocotb_config(sim="icarus"):
    """
    Return the cocotb VPI library and share directory for a simulator.

    Returns:
        tuple: ``(libs_dir, vpi_lib, share_dir)`` where ``vpi_lib`` is the
        absolute path to the simulator's cocotb VPI library.
    """
    _require_cocotb("get_cocotb_config")

    libs_dir = cocotb_tools.config.libs_dir
    vpi_lib = cocotb_tools.config.lib_name_path("vpi", sim)
    share_dir = cocotb_tools.config.share_dir

    return libs_dir, vpi_lib, share_dir


def get_cocotb_lib_entry(sim="icarus", interface="vpi"):
    """
    Return the cocotb interface library for a simulator to load.

    This is the value cocotb documents as ``cocotb-config --lib-entry`` for
    custom flows.  For simulators that need an explicit entry function the
    result uses the ``library:entry_function`` format, so it must be passed to
    the simulator verbatim.

    Returns:
        str: The interface library, optionally suffixed with its entry function.
    """
    _require_cocotb("get_cocotb_lib_entry")

    return cocotb_tools.config.lib_entry(interface, sim)


def get_libpython_path():
    """
    Retrieve the path to the libpython shared library.

    Returns:
        str: Absolute path to the libpython shared library.

    Raises:
        ValueError: If libpython cannot be found.
    """
    _require_cocotb("get_libpython_path")

    libpython_path = find_libpython.find_libpython()
    if not libpython_path:
        raise ValueError(
            "Unable to find libpython, please make sure the appropriate libpython "
            "is installed")
    return libpython_path


def get_gpi_users():
    """
    Build the ``GPI_USERS`` value that bootstraps Python inside the simulator.

    cocotb's GPI layer loads the libraries listed in ``GPI_USERS`` once it has
    initialized.  Python is brought up by loading libpython followed by the
    PyGPI entry point.

    Returns:
        str: Semicolon-separated ``GPI_USERS`` value.
    """
    _require_cocotb("get_gpi_users")

    return ";".join([get_libpython_path(), cocotb_tools.config.pygpi_entry_point()])


class CocotbEnvironment(Task):
    '''Mixin for tasks that need cocotb on the node that runs them.

    The node gets cocotb, and the Python packages the testbench imports, from
    the machine the run was submitted from rather than from its own install.
    :meth:`capture_python_environment` records them there; :meth:`pre_process`
    makes them available on the node, installing the pins its own Python does
    not satisfy and staging the packages that were copied.

    Intended to be used via multiple inheritance alongside a concrete task
    class that defines :meth:`tool` and :meth:`task`.
    '''

    # Directory in the node's workdir holding packages copied from the
    # submitting machine, under the names they are imported by.
    _FORWARD_DIR = "cocotb_python"

    def __init__(self):
        super().__init__()

        self.add_parameter("python_requirement", "[str]",
                           'Python distributions the node needs beyond those the testbench '
                           'imports directly, as names or PEP 508 requirements. The version '
                           'installed on the submitting machine is the one used.')
        self.add_parameter("python_install", "[str]",
                           'Python distributions captured from the submitting machine, as '
                           '``name==version`` pins, for the node to install when its own '
                           'Python does not have them. Set by setup().')
        self.add_parameter("python_forward_package", "[str]",
                           'Python distributions captured from the submitting machine that '
                           'cannot be installed from an index, such as editable installs, as '
                           '``name==version`` pins. Set by setup().')
        self.add_parameter("python_forward", "[dir]",
                           'Directories copied to the node for the distributions in '
                           '``python_forward_package``. Set by setup().')

        self.__python_path: List[str] = []
        self.__cocotb: Optional[dict] = None

    def add_cocotb_python_requirement(
        self, requirement: Union[str, List[str]],
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None,
        clobber: bool = False
    ):
        """
        Adds Python distributions the node needs that the testbench does not
        import directly, such as a plugin loaded by name.

        Args:
            requirement (str or list of str): Distribution names or PEP 508
                requirements.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool): If True, replaces the existing requirements.
        """
        if clobber:
            self.set("var", "python_requirement", requirement, step=step, index=index)
        else:
            self.add("var", "python_requirement", requirement, step=step, index=index)

    def _get_python_sources(self) -> List[str]:
        """
        Python files whose imports decide what the node needs.

        Returns:
            list of str: Paths to Python source files.
        """
        return []

    def capture_python_environment(self) -> None:
        """
        Records what the node needs from this machine's Python environment.

        Runs where the run is submitted from, which is the one machine known to
        have the environment the testbench was written against. Needs no
        cocotb: without it here, the node has to provide its own.
        """
        modules = python_env.imported_modules(self._get_python_sources())
        requirements = self.get("var", "python_requirement")
        if _has_cocotb:
            requirements = ["cocotb"] + requirements
        else:
            # A cocotb that cannot be imported here is not this machine's to
            # send: the node's own has to do.
            modules.discard("cocotb")
        install, packages, forward, warnings = python_env.capture(modules, requirements)
        for warning in warnings:
            self.logger.warning(warning)

        self.set("var", "python_install", install, clobber=True)
        self.set("var", "python_forward_package", packages, clobber=True)
        self.set("var", "python_forward", forward, clobber=True)
        if forward:
            self.get("var", "python_forward", field=None).set(True, field="copy")

    def setup(self):
        super().setup()

        if self.get("var", "python_requirement"):
            self.add_required_key("var", "python_requirement")

        if not self.project.get("record", "remoteid"):
            # A job carrying a remote ID was submitted from another machine,
            # which captured its environment before sending it.
            self.capture_python_environment()

        for key in ("python_install", "python_forward_package", "python_forward"):
            if self.get("var", key):
                self.add_required_key("var", key)

    def pre_process(self):
        super().pre_process()

        self.__python_path = self.__prepare_python_environment()
        self.__cocotb = None

    def __prepare_python_environment(self) -> List[str]:
        """
        Makes the captured Python environment available on this node.

        Returns:
            list of str: Directories to put ahead of this Python's own packages.
        """
        python_path = []

        packages = self.get("var", "python_forward_package")
        if not all(python_env.is_installed(pin) for pin in packages):
            staged = os.path.join(self.nodeworkdir, self._FORWARD_DIR)
            os.makedirs(staged, exist_ok=True)
            for declared, resolved in zip(self.get("var", "python_forward"),
                                          self.find_files("var", "python_forward")):
                link = os.path.join(staged, os.path.basename(declared))
                if os.path.lexists(link):
                    continue
                try:
                    os.symlink(resolved, link, target_is_directory=True)
                except OSError:
                    shutil.copytree(resolved, link)
            python_path.append(staged)

        missing = [pin for pin in self.get("var", "python_install")
                   if not python_env.is_installed(pin)]
        if missing:
            python_path.append(python_env.install(
                missing,
                os.path.join(paths.toolcachedir(self.project), "cocotb", "python"),
                self.logger))

        return python_path

    def _get_python_path(self) -> List[str]:
        """
        Directories :meth:`pre_process` added for the captured environment.

        Returns:
            list of str: Directories to put ahead of this Python's own packages.
        """
        return list(self.__python_path)

    def _cocotb_pinned(self) -> bool:
        """
        Whether the node is to install cocotb from the captured environment.

        Returns:
            bool: True if a cocotb pin was captured.
        """
        return any(pin.partition("==")[0].lower() == "cocotb"
                   for pin in self.get("var", "python_install"))

    def _cocotb_found(self) -> bool:
        """
        Whether the Python this node simulates with can import cocotb.

        Before :meth:`pre_process`, and wherever it added nothing, that Python
        is this one; after it, it is this one with the captured environment.

        Returns:
            bool: True if cocotb can be found.
        """
        if self.__python_path:
            return self.__node_cocotb() is not None
        return _has_cocotb

    def __node_cocotb(self) -> Optional[dict]:
        """
        cocotb's locations as seen through the environment :meth:`pre_process`
        prepared, or None if cocotb cannot be found there.
        """
        if self.__cocotb is None:
            try:
                self.__cocotb = python_env.cocotb_config(self.tool(), self.__python_path)
            except RuntimeError:
                return None
        return self.__cocotb

    def __require_node_cocotb(self) -> dict:
        cocotb = self.__node_cocotb()
        if cocotb is None:
            raise NotImplementedError(f"COCOTB must be installed to run {self.tool()}")
        return cocotb

    def _get_cocotb_libs_dir(self) -> str:
        """
        Returns:
            str: The directory holding the cocotb libraries this node loads.
        """
        if self.__python_path:
            return self.__require_node_cocotb()["libs_dir"]
        _require_cocotb("_get_cocotb_libs_dir")
        return str(cocotb_tools.config.libs_dir)

    def _get_cocotb_config(self):
        """
        As :func:`get_cocotb_config`, for the cocotb this node simulates with.

        Returns:
            tuple: ``(libs_dir, vpi_lib, share_dir)``.
        """
        if self.__python_path:
            cocotb = self.__require_node_cocotb()
            return Path(cocotb["libs_dir"]), Path(cocotb["vpi_lib"]), Path(cocotb["share_dir"])
        return get_cocotb_config(self.tool())

    def _get_cocotb_lib_entry(self) -> str:
        """
        As :func:`get_cocotb_lib_entry`, for the cocotb this node simulates with.

        Returns:
            str: The interface library, optionally suffixed with its entry function.
        """
        if self.__python_path:
            return self.__require_node_cocotb()["lib_entry"]
        return get_cocotb_lib_entry(self.tool())

    def _get_gpi_users(self) -> str:
        """
        As :func:`get_gpi_users`, for the Python and cocotb this node simulates with.

        Returns:
            str: Semicolon-separated ``GPI_USERS`` value.
        """
        if self.__python_path:
            cocotb = self.__require_node_cocotb()
            if not cocotb["libpython"]:
                raise ValueError(
                    "Unable to find libpython, please make sure the appropriate libpython "
                    "is installed")
            return ";".join([cocotb["libpython"], cocotb["pygpi_entry"]])
        return get_gpi_users()


class CocotbTask(CocotbEnvironment):

    def __init__(self):
        super().__init__()

        self.add_parameter("cocotb_random_seed", "int",
                           'Random seed for cocotb test reproducibility. '
                           'If not set, cocotb will generate a random seed.')

    def set_cocotb_randomseed(
        self, seed: int,
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None
    ):
        """
        Sets the random seed for cocotb tests.

        Args:
            seed (int): The random seed value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "cocotb_random_seed", seed, step=step, index=index)

    def task(self):
        return "exec_cocotb"

    def _get_test_modules(self):
        """
        Get cocotb test module names from Python files in filesets.

        Returns:
            tuple: (module_names, module_dirs) where module_names is a
                   comma-separated string and module_dirs is a list of
                   directories containing the modules.
        """
        module_names = []
        module_dirs = []
        seen_dirs = set()

        for lib, fileset in self.project.get_filesets():
            for pyfile in lib.get_file(fileset=fileset, filetype="python"):
                path = Path(pyfile)
                # Module name is the filename without .py extension
                module_name = path.stem
                module_names.append(module_name)
                # Track the directory for PYTHONPATH
                dir_path = str(path.parent.resolve())
                if dir_path not in seen_dirs:
                    seen_dirs.add(dir_path)
                    module_dirs.append(dir_path)

        return ",".join(module_names), module_dirs

    def _get_libdirs(self):
        """
        Collect user-provided library directories from all filesets.

        These directories are added to PYTHONPATH so cocotb can import
        Python modules that the testbench depends on.

        Returns:
            list: A list of library directory paths.
        """
        libdirs = []
        for lib, fileset in self.project.get_filesets():
            libdirs.extend(lib.get_libdir(fileset=fileset))
        return libdirs

    def _get_toplevel_lang(self):
        """
        Determine the HDL toplevel language from the design schema.

        For Icarus Verilog, this is always "verilog" since Icarus
        doesn't support VHDL. SystemVerilog is treated as Verilog
        for cocotb's TOPLEVEL_LANG.

        Returns:
            str: The toplevel language ("verilog").
        """
        # Icarus only supports Verilog/SystemVerilog, not VHDL
        # cocotb uses "verilog" for both Verilog and SystemVerilog
        return "verilog"

    def __setup_cocotb_environment(self):
        """
        Set up all required environment variables for cocotb execution.
        """

        test_modules, _ = self._get_test_modules()

        # GPI_USERS is the node's, in get_runtime_environmental_variables():
        # absolute paths into whichever Python and cocotb run the node.

        # COCOTB_TOPLEVEL: the HDL toplevel module name
        self.set_environmentalvariable("COCOTB_TOPLEVEL", self.design_topmodule)
        self.add_required_key("env", "COCOTB_TOPLEVEL")

        # COCOTB_TEST_MODULES: comma-separated list of Python test modules
        self.set_environmentalvariable("COCOTB_TEST_MODULES", test_modules)
        self.add_required_key("env", "COCOTB_TEST_MODULES")

        # TOPLEVEL_LANG: HDL language of the toplevel
        self.set_environmentalvariable("TOPLEVEL_LANG", self._get_toplevel_lang())
        self.add_required_key("env", "TOPLEVEL_LANG")

        # COCOTB_RESULTS_FILE: path to xUnit XML results
        self.set_environmentalvariable("COCOTB_RESULTS_FILE", "outputs/results.xml")
        self.add_required_key("env", "COCOTB_RESULTS_FILE")

        # COCOTB_RANDOM_SEED: optional random seed for reproducibility
        random_seed = self.get("var", "cocotb_random_seed")
        if random_seed is not None:
            self.set_environmentalvariable("COCOTB_RANDOM_SEED", str(random_seed))
            self.add_required_key("env", "COCOTB_RANDOM_SEED")

    def _get_python_sources(self):
        """
        The test modules and the Python files in the user library directories.

        Returns:
            list of str: Paths to Python source files.
        """
        sources = []
        for lib, fileset in self.project.get_filesets():
            sources.extend(lib.get_file(fileset=fileset, filetype="python"))
        for libdir in self._get_libdirs():
            for root, _, files in os.walk(libdir):
                sources.extend(os.path.join(root, f) for f in files if f.endswith(".py"))
        return sources

    def setup(self):
        super().setup()

        # Only running the test needs cocotb, and get_exe() stops the run
        # there, so setting it up without cocotb is only worth a warning --
        # and none at all when the node will install the cocotb captured here.
        if not _has_cocotb and not self._cocotb_pinned():
            self.logger.warning("Cocotb is not installed; this test will not be able to run.")

        # Output: xUnit XML results file
        self.add_output_file(file="results.xml")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Require Python test modules
        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="python"):
                self.add_required_key(lib, "fileset", fileset, "file", "python")
            if lib.has_libdir(fileset=fileset):
                self.add_required_key(lib, "fileset", fileset, "libdir")

        if self.get("var", "cocotb_random_seed") is not None:
            self.add_required_key("var", "cocotb_random_seed")

        # Set up cocotb environment variables
        self.__setup_cocotb_environment()

    def get_runtime_environmental_variables(self, include_path: bool = True) -> Dict[str, str]:
        """
        Build the environment variables required to run a cocotb simulation.

        Extends the base environment with the cocotb library directory on
        PATH, the test-module and user library directories on PYTHONPATH,
        and the GPI bootstrap -- ``GPI_USERS`` and ``PYGPI_PYTHON_BIN`` -- for
        the Python running this node. PATH and PYTHONPATH entries are added
        idempotently so repeated calls do not duplicate them.

        Args:
            include_path (bool): If True, includes the PATH variable.

        Returns:
            dict: A dictionary of environment variable names to their values.
        """
        envs = super().get_runtime_environmental_variables(include_path)

        # The executable is looked up in this environment, and get_exe() is
        # what reports a missing cocotb, so without cocotb it is built without
        # cocotb's parts.
        has_cocotb = self._cocotb_found()

        ##########################################
        # PATH: add cocotb libs directory
        ##########################################
        if include_path and has_cocotb:
            libs_dir = self._get_cocotb_libs_dir()
            path_parts = envs.get("PATH", "").split(os.pathsep)
            if libs_dir not in path_parts:
                path_parts.insert(0, libs_dir)
            envs["PATH"] = os.pathsep.join(p for p in path_parts if p)

        ##########################################
        # PYTHONPATH: add dirs to python path
        ##########################################
        python_path = [p for p in envs.get("PYTHONPATH", "").split(os.pathsep) if p]

        # Get test module directories
        _, module_dirs = self._get_test_modules()
        # Get lib directories
        user_lib_dirs = self._get_libdirs()

        # Packages from the submitting machine, ahead of this Python's own
        forwarded = self._get_python_path()

        for path in module_dirs + user_lib_dirs + forwarded:
            if path not in python_path:
                python_path.append(path)

        # Forward the caller's PYTHONPATH last, as the base task forwards PATH,
        # so packages reachable only through it (a checkout, an environment
        # module) can still be imported by the testbench.
        if include_path:
            for path in os.getenv("PYTHONPATH", "").split(os.pathsep):
                if path and path not in python_path:
                    python_path.append(path)

        # Set new python path
        envs["PYTHONPATH"] = os.pathsep.join(python_path)

        ##########################################
        # GPI_USERS / PYGPI_PYTHON_BIN: the Python this node runs on
        ##########################################
        # Resolved here rather than in setup(): these are absolute paths into
        # whichever Python and cocotb execute the node. GPI_USERS lists the
        # libraries the GPI layer loads to bring Python up inside the
        # simulator: libpython, then the PyGPI entry point.
        if has_cocotb:
            envs["GPI_USERS"] = self._get_gpi_users()
        envs["PYGPI_PYTHON_BIN"] = sys.executable

        return envs

    def get_exe(self) -> Optional[str]:
        """
        Determines the absolute path for the task's executable.

        The simulator runs cocotb's VPI library and Python, so without cocotb
        it has nothing to run: the scheduler's tool check stops the run before
        any node starts. A cocotb captured from the submitting machine counts,
        since :meth:`pre_process` installs it before the simulator runs.

        Raises:
            TaskExecutableNotFound: If cocotb is not installed, or the
                executable cannot be found in the system PATH.

        Returns:
            str: The absolute path to the executable, or None if not specified.
        """
        if not self._cocotb_found() and not self._cocotb_pinned():
            self.logger.error("Cocotb is not installed; cannot run test.")
            raise TaskExecutableNotFound("cocotb is not installed")
        return super().get_exe()

    def _parse_cocotb_results(self, results_file: Path):
        """
        Parse the cocotb xUnit XML results file and extract metrics.

        Args:
            results_file: Path to the results.xml file.
        """
        try:
            tree = ET.parse(results_file)
            root = tree.getroot()

            # Count testcases and failures/errors
            testcases = root.findall(".//testcase")
            tests = len(testcases)
            failures = len(root.findall(".//failure"))
            errors = len(root.findall(".//error"))

            passed = tests - failures - errors

            self.logger.info(f"Cocotb results: {passed}/{tests} tests passed")
            if failures > 0:
                self.logger.warning(f"Cocotb: {failures} test(s) failed")
            if errors > 0:
                self.logger.warning(f"Cocotb: {errors} test(s) had errors")

            self.record_metric("errors", errors + failures, source_file=results_file)

        except Exception as e:
            self.logger.warning(f"Failed to parse cocotb results: {e}")

    def post_process(self):
        super().post_process()

        # Parse cocotb results XML and report metrics
        results_file = Path("outputs/results.xml")
        if results_file.exists():
            self._parse_cocotb_results(results_file)
