import os
import sys
from pathlib import Path
from typing import Optional, Union, Dict
import xml.etree.ElementTree as ET

from siliconcompiler import Task

try:
    import cocotb_tools.config
    import cocotb_tools.runner
    _has_cocotb = True
except ModuleNotFoundError:
    _has_cocotb = False


if _has_cocotb:
    def get_cocotb_config(sim="icarus"):
        libs_dir = cocotb_tools.config.libs_dir
        lib_name = cocotb_tools.config.lib_name("vpi", sim)
        share_dir = cocotb_tools.config.share_dir

        return libs_dir, lib_name, share_dir

    class CocotbRunnerDummy(cocotb_tools.runner.Runner):
        """
        A minimal Runner subclass used solely to retrieve the libpython path.

        This class provides access to the libpython shared library location
        without adding ``find_libpython`` as a direct dependency. It leverages
        cocotb's existing Runner infrastructure, which handles libpython
        discovery internally via the ``_set_env()`` method.

        The abstract methods required by the Runner base class are implemented
        as no-ops or raise NotImplementedError, as they are not intended to be
        called. This class should only be instantiated to call
        ``get_libpython_path()``.

        Example:
            >>> libpython = CocotbRunnerDummy().get_libpython_path()
            >>> print(libpython)
            /usr/lib/x86_64-linux-gnu/libpython3.10.so
        """

        def __init__(self):
            super().__init__()
            # These attributes are required by _set_env() which uses them to
            # populate environment variables.
            self.sim_hdl_toplevel = ""
            self.test_module = ""
            self.hdl_toplevel_lang = ""

        def _simulator_in_path(self):
            # No-op: This dummy class doesn't require any simulator executable.
            pass

        def _build_command(self):
            raise NotImplementedError(
                "CocotbRunnerDummy is not intended for building HDL sources")

        def _test_command(self):
            raise NotImplementedError(
                "CocotbRunnerDummy is not intended for running tests")

        def _get_define_options(self, defines):
            raise NotImplementedError(
                "CocotbRunnerDummy is not intended for HDL compilation")

        def _get_include_options(self, includes):
            raise NotImplementedError(
                "CocotbRunnerDummy is not intended for HDL compilation")

        def _get_parameter_options(self, parameters):
            raise NotImplementedError(
                "CocotbRunnerDummy is not intended for HDL compilation")

        def get_libpython_path(self):
            """
            Retrieve the path to the libpython shared library.

            This method uses cocotb's ``Runner._set_env()`` which internally
            calls ``find_libpython.find_libpython()`` to locate the library.

            Returns:
                str: Absolute path to the libpython shared library.

            Raises:
                ValueError: If libpython cannot be found.
            """
            self._set_env()
            return self.env["LIBPYTHON_LOC"]


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
        module_dirs = set()

        for lib, fileset in self.project.get_filesets():
            for pyfile in lib.get_file(fileset=fileset, filetype="python"):
                path = Path(pyfile)
                # Module name is the filename without .py extension
                module_name = path.stem
                module_names.append(module_name)
                # Track the directory for PYTHONPATH
                module_dirs.add(str(path.parent.resolve()))

        return ",".join(module_names), list(module_dirs)

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

    def _setup_cocotb_environment(self):
        """
        Set up all required environment variables for cocotb execution.
        """

        test_modules, _ = self._get_test_modules()
        libpython_path = CocotbRunnerDummy().get_libpython_path()

        # LIBPYTHON_LOC: path to libpython shared library
        self.set_environmentalvariable("LIBPYTHON_LOC", libpython_path)
        self.add_required_key("env", "LIBPYTHON_LOC")

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

        if self.get("var", "cocotb_random_seed") is not None:
            self.add_required_key("var", "cocotb_random_seed")

        # Set up cocotb environment variables
        self._setup_cocotb_environment()

    def get_runtime_environmental_variables(self, include_path: bool = True) -> Dict[str, str]:
        envs = super().get_runtime_environmental_variables(include_path)

        _, module_dirs = self._get_test_modules()
        libs_dir = cocotb_tools.config.libs_dir

        # PATH: add cocotb libs directory
        current_path = os.environ.get("PATH", "")
        new_path = f"{libs_dir}{os.pathsep}{current_path}"
        envs["PATH"] = new_path

        # PYTHONPATH: add directories containing test modules
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        pythonpath_parts = module_dirs + ([current_pythonpath] if current_pythonpath else [])
        envs["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        # PYGPI_PYTHON_BIN: Python executable
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

        except Exception as e:
            self.logger.warning(f"Failed to parse cocotb results: {e}")

    def post_process(self):
        super().post_process()

        # Parse cocotb results XML and report metrics
        results_file = Path("outputs/results.xml")
        if results_file.exists():
            self._parse_cocotb_results(results_file)
