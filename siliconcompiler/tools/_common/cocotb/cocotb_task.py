import os
import sys
from pathlib import Path
from typing import Optional, Union, Dict
import xml.etree.ElementTree as ET

from siliconcompiler import Task

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


class CocotbTask(Task):

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

        # GPI_USERS: libraries the GPI layer loads to bootstrap Python inside
        # the simulator (libpython followed by the PyGPI entry point).
        self.set_environmentalvariable("GPI_USERS", get_gpi_users())
        self.add_required_key("env", "GPI_USERS")

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

        if not _has_cocotb:
            raise RuntimeError("Cocotb is not installed; cannot run test.")

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
        and the Python executable used by the GPI bridge. PATH and PYTHONPATH
        entries are added idempotently so repeated calls do not duplicate them.

        Args:
            include_path (bool): If True, includes the PATH variable.

        Returns:
            dict: A dictionary of environment variable names to their values.
        """
        envs = super().get_runtime_environmental_variables(include_path)

        ##########################################
        # PATH: add cocotb libs directory
        ##########################################
        if include_path:
            libs_dir = str(cocotb_tools.config.libs_dir)
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

        for path in module_dirs + user_lib_dirs:
            if path not in python_path:
                python_path.append(path)

        # Set new python path
        envs["PYTHONPATH"] = os.pathsep.join(python_path)

        ##########################################
        # PYGPI_PYTHON_BIN: set python executable
        ##########################################
        envs["PYGPI_PYTHON_BIN"] = sys.executable

        return envs

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
