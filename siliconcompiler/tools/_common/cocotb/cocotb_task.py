import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Union, Dict
import xml.etree.ElementTree as ET

from siliconcompiler import Task, utils
from siliconcompiler.tool import PythonEnvironment, TaskExecutableNotFound


def _cocotb():
    """cocotb's configuration and ``find_libpython``, imported where they are
    used, or None.

    🔴 **Never at import, and never in setup()**: setup runs on the machine a
    run is submitted from, which for a remote run need not have cocotb -- the
    node's image does, at SiliconCompiler's range. What needs it is what runs
    on the node.
    """
    try:
        import cocotb_tools.config
        import find_libpython
    except ModuleNotFoundError:
        return None
    return cocotb_tools.config, find_libpython


def _require_cocotb(what):
    found = _cocotb()
    if found is None:
        raise NotImplementedError(f"COCOTB must be installed to use {what}")
    return found


def get_cocotb_config(sim="icarus"):
    """
    Return the cocotb VPI library and share directory for a simulator.

    Returns:
        tuple: ``(libs_dir, vpi_lib, share_dir)`` where ``vpi_lib`` is the
        absolute path to the simulator's cocotb VPI library.
    """
    config, _ = _require_cocotb("get_cocotb_config")

    libs_dir = config.libs_dir
    vpi_lib = config.lib_name_path("vpi", sim)
    share_dir = config.share_dir

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
    config, _ = _require_cocotb("get_cocotb_lib_entry")

    return config.lib_entry(interface, sim)


def get_libpython_path():
    """
    Retrieve the path to the libpython shared library.

    Returns:
        str: Absolute path to the libpython shared library.

    Raises:
        ValueError: If libpython cannot be found.
    """
    _, find_libpython = _require_cocotb("get_libpython_path")

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
    config, _ = _require_cocotb("get_gpi_users")

    return ";".join([get_libpython_path(), config.pygpi_entry_point()])


class CocotbTask(Task):

    # Test modules whose file collection renamed, linked back under the name
    # cocotb imports them by, in the node's work directory.
    _STAGED_MODULES_DIR = "cocotb_modules"

    @classmethod
    def framework_distributions(cls) -> Tuple[str, ...]:
        """cocotb: this process sets up the GPI from its own copy, so the
        node's image holds it at SiliconCompiler's range and the testbench's
        environment leaves it out."""
        return ("cocotb",)

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

    def _get_test_module_names(self):
        """
        Get cocotb test module names from Python files in filesets.

        🔴 The name comes from each file as declared, not as resolved:
        collection renames a file to ``<name>_<hash>.py``, and a module's name
        is what cocotb imports and what every test is reported under.

        Returns:
            str: comma-separated module names.
        """
        module_names = []
        for lib, fileset in self.project.get_filesets():
            for pyfile in lib.get("fileset", fileset, "file", "python"):
                module_names.append(Path(pyfile).stem)
        return ",".join(module_names)

    def _get_test_modules(self):
        """
        Resolve cocotb test modules to the files that will be imported.

        Returns:
            tuple: (staged, module_dirs) where staged maps a module name to a
                   resolved file whose own name differs from it, and
                   module_dirs is a list of directories containing modules
                   that can be imported where they are.
        """
        staged = {}
        module_dirs = []

        for lib, fileset in self.project.get_filesets():
            declared = lib.get("fileset", fileset, "file", "python")
            resolved = lib.get_file(fileset=fileset, filetype="python")
            for name, pyfile in zip(declared, resolved):
                path = Path(pyfile)
                module_name = Path(name).stem
                if path.stem != module_name:
                    staged[module_name] = str(path.resolve())
                    continue
                dir_path = str(path.parent.resolve())
                if dir_path not in module_dirs:
                    module_dirs.append(dir_path)

        return staged, module_dirs

    def get_python_environment(self) -> PythonEnvironment:
        """
        The testbench's own Python, for a remote run to carry.

        The test modules are the sources whose imports the environment is
        read from. cocotb itself is SiliconCompiler's: this process configures
        the GPI from its own copy, so the image has to hold the same version,
        and the testbench's environment leaves it out.

        Returns:
            PythonEnvironment: the test modules, and cocotb as the framework's.
        """
        sources = tuple(str(pyfile) for lib, fileset in self.project.get_filesets()
                        for pyfile in lib.get_file(fileset=fileset, filetype="python"))
        return PythonEnvironment(sources=sources, framework=self.framework_distributions())

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

        test_modules = self._get_test_module_names()

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

    def setup(self):
        super().setup()

        # Only running the test needs cocotb, and get_exe() stops the run
        # there, so setting it up without cocotb is only worth a warning.
        if _cocotb() is None:
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
        found = _cocotb()

        ##########################################
        # PATH: add cocotb libs directory
        ##########################################
        if include_path and found:
            libs_dir = str(found[0].libs_dir)
            path_parts = envs.get("PATH", "").split(os.pathsep)
            if libs_dir not in path_parts:
                path_parts.insert(0, libs_dir)
            envs["PATH"] = os.pathsep.join(p for p in path_parts if p)

        ##########################################
        # PYTHONPATH: add dirs to python path
        ##########################################
        python_path = [p for p in envs.get("PYTHONPATH", "").split(os.pathsep) if p]

        # Get test module directories, the renamed ones linked back first
        staged, module_dirs = self._get_test_modules()
        if staged:
            module_dirs.insert(0, os.path.join(self.nodeworkdir, self._STAGED_MODULES_DIR))
        # Get lib directories
        user_lib_dirs = self._get_libdirs()

        for path in module_dirs + user_lib_dirs:
            if path not in python_path:
                python_path.append(path)

        # Set new python path
        envs["PYTHONPATH"] = os.pathsep.join(python_path)

        ##########################################
        # GPI_USERS / PYGPI_PYTHON_BIN: the Python this node runs on
        ##########################################
        # Resolved here rather than in setup(): setup() runs on the submitting
        # machine, and these are absolute paths into whichever Python and
        # cocotb execute the node. GPI_USERS lists the libraries the GPI layer
        # loads to bring Python up inside the simulator: libpython, then the
        # PyGPI entry point.
        if found:
            envs["GPI_USERS"] = get_gpi_users()
        envs["PYGPI_PYTHON_BIN"] = sys.executable

        return envs

    def pre_process(self):
        super().pre_process()

        # Test modules whose file collection renamed are linked back under the
        # name cocotb imports them by.
        staged, _ = self._get_test_modules()
        if staged:
            staged_dir = os.path.join(self.nodeworkdir, self._STAGED_MODULES_DIR)
            os.makedirs(staged_dir, exist_ok=True)
            for module_name, path in staged.items():
                utils.link_symlink_copy(path, os.path.join(staged_dir, f"{module_name}.py"))

    def get_exe(self) -> Optional[str]:
        """
        Determines the absolute path for the task's executable.

        The simulator runs cocotb's VPI library and Python, so without cocotb
        it has nothing to run: the scheduler's tool check stops the run before
        any node starts.

        Raises:
            TaskExecutableNotFound: If cocotb is not installed, or the
                executable cannot be found in the system PATH.

        Returns:
            str: The absolute path to the executable, or None if not specified.
        """
        if _cocotb() is None:
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
