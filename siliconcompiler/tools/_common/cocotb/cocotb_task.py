import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union, Dict

from siliconcompiler import Task

try:
    import cocotb_tools.config
    _has_cocotb = True
except ModuleNotFoundError:
    _has_cocotb = False


if _has_cocotb:
    def get_cocotb_config(sim="icarus"):
        libs_dir = cocotb_tools.config.libs_dir
        lib_name = cocotb_tools.config.lib_name("vpi", sim)
        share_dir = cocotb_tools.config.share_dir

        return libs_dir, lib_name, share_dir


class CocotbTask(Task):

    def __init__(self):
        super().__init__()

        self.add_parameter("cocotb_random_seed", "int",
                           'Random seed for cocotb test reproducibility. '
                           'If not set, cocotb will generate a random seed.')

        self.add_parameter("trace", "bool",
                           'Enable waveform tracing. The simulation must have been '
                           'compiled with trace support enabled.',
                           defvalue=False)

        self.add_parameter("trace_type", "<vcd,fst>",
                           'Specifies type of wave file to create when [trace] is set.',
                           defvalue="vcd")

    def set_randomseed(
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

    def set_traceconfig(
        self,
        enable: bool = True,
        trace_type: str = "vcd",
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None
    ):
        self.set("var", "trace", enable, step=step, index=index)
        self.set("var", "trace_type", trace_type, step=step, index=index)

    def task(self):
        return "exec_cocotb"

    def _get_libpython_path(self):
        result = subprocess.run(
            ['cocotb-config', '--libpython'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

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
        libpython_path = self._get_libpython_path()

        # LIBPYTHON_LOC: path to libpython shared library
        self.set_environmentalvariable("LIBPYTHON_LOC", libpython_path)

        # COCOTB_TOPLEVEL: the HDL toplevel module name
        self.set_environmentalvariable("COCOTB_TOPLEVEL", self.design_topmodule)

        # COCOTB_TEST_MODULES: comma-separated list of Python test modules
        self.set_environmentalvariable("COCOTB_TEST_MODULES", test_modules)

        # TOPLEVEL_LANG: HDL language of the toplevel
        self.set_environmentalvariable("TOPLEVEL_LANG", self._get_toplevel_lang())

        # COCOTB_RESULTS_FILE: path to xUnit XML results
        self.set_environmentalvariable("COCOTB_RESULTS_FILE", "outputs/results.xml")

        # COCOTB_RANDOM_SEED: optional random seed for reproducibility
        random_seed = self.get("var", "cocotb_random_seed")
        if random_seed:
            self.set_environmentalvariable("COCOTB_RANDOM_SEED", str(random_seed))

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

        if self.get("var", "cocotb_random_seed"):
            self.add_required_key("var", "cocotb_random_seed")

        self.add_required_key("var", "trace")
        self.add_required_key("var", "trace_type")

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
            import xml.etree.ElementTree as ET

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
