import glob
import os
import stat
import sys
from pathlib import Path
from typing import Optional, Union

from siliconcompiler import Task
from siliconcompiler.tool import TaskExecutableNotReceived


class CocotbTask(Task):
    '''
    Run a cocotb testbench against a compiled Verilator simulation.

    This task takes a compiled .vexe file from the verilator cocotb_compile task
    and executes it with the cocotb environment variables set, enabling Python-based
    testbenches to interact with the simulation.

    Unlike Icarus where the VPI module is loaded at runtime via command-line flags,
    Verilator links the cocotb VPI library at compile time. This task simply runs
    the compiled executable directly with the appropriate environment.

    The task requires cocotb to be installed in the Python environment.
    Test modules are specified by adding Python files to the fileset using
    the "python" filetype.
    '''

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

    def set_cocotb_random_seed(self, seed: int,
                               step: Optional[str] = None,
                               index: Optional[Union[str, int]] = None):
        """
        Sets the random seed for cocotb tests.

        Args:
            seed (int): The random seed value.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "cocotb_random_seed", seed, step=step, index=index)

    def set_trace_enabled(self, enable: bool = True,
                          step: Optional[str] = None,
                          index: Optional[Union[str, int]] = None):
        """
        Enables or disables waveform tracing.

        When enabled, the simulation will generate a waveform file (VCD or FST).
        The simulation must have been compiled with trace support enabled.

        Args:
            enable (bool): Whether to enable tracing. Defaults to True.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "trace", enable, step=step, index=index)

    def set_trace_type(self, trace_type: str,
                       step: Optional[str] = None,
                       index: Optional[Union[str, int]] = None):
        """
        Sets the type of wave file to create when trace is enabled.

        Args:
            trace_type (str): The trace type ('vcd' or 'fst').
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "trace_type", trace_type, step=step, index=index)

    def tool(self):
        return "verilator"

    def task(self):
        return "cocotb"

    def setup(self):
        super().setup()

        self.set_threads()

        # Input: compiled .vexe file from cocotb_compile task
        self.add_input_file(ext="vexe")

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

        # Mark trace parameters as required if set
        self.add_required_key("var", "trace")
        self.add_required_key("var", "trace_type")

        # Set up cocotb environment variables
        self._setup_cocotb_environment()

    def get_exe(self):
        """
        Get the compiled executable to run.

        Unlike Icarus which uses vvp as a wrapper, Verilator produces
        a native executable that we run directly.
        """
        exec_file = None
        for fin in glob.glob('inputs/*'):
            if fin.endswith('.pkg.json'):
                continue
            if fin.endswith('.vexe'):
                exec_file = os.path.abspath(fin)
                break

        if not exec_file:
            raise TaskExecutableNotReceived(
                f'{self.step}/{self.index} did not receive a .vexe executable file'
            )

        # Ensure the file is executable
        os.chmod(exec_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        return exec_file

    def _get_cocotb_config(self):
        """
        Import and return cocotb configuration.

        Returns:
            tuple: (libs_dir, libpython_path)

        Raises:
            ImportError: If cocotb_tools is not installed.
        """
        try:
            import cocotb_tools.config
            import find_libpython

            libs_dir = cocotb_tools.config.libs_dir
            libpython_path = find_libpython.find_libpython()

            if not libpython_path:
                raise ValueError(
                    "Unable to find libpython. Please ensure libpython is installed."
                )

            return libs_dir, libpython_path
        except ImportError as e:
            raise ImportError(
                "cocotb must be installed to use the cocotb task. "
                "Install it with: pip install cocotb"
            ) from e

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

        For Verilator, this is always "verilog" since Verilator
        doesn't support VHDL. SystemVerilog is treated as Verilog
        for cocotb's TOPLEVEL_LANG.

        Returns:
            str: The toplevel language ("verilog").
        """
        # Verilator only supports Verilog/SystemVerilog, not VHDL
        # cocotb uses "verilog" for both Verilog and SystemVerilog
        return "verilog"

    def _setup_cocotb_environment(self):
        """
        Set up all required environment variables for cocotb execution.
        """
        libs_dir, libpython_path = self._get_cocotb_config()
        test_modules, module_dirs = self._get_test_modules()

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

        # PATH: add cocotb libs directory
        current_path = os.environ.get("PATH", "")
        new_path = f"{libs_dir}{os.pathsep}{current_path}"
        self.set_environmentalvariable("PATH", new_path)

        # PYTHONPATH: add directories containing test modules
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        pythonpath_parts = module_dirs + ([current_pythonpath] if current_pythonpath else [])
        self.set_environmentalvariable("PYTHONPATH", os.pathsep.join(pythonpath_parts))

        # PYGPI_PYTHON_BIN: Python executable
        self.set_environmentalvariable("PYGPI_PYTHON_BIN", sys.executable)

        # COCOTB_RANDOM_SEED: optional random seed for reproducibility
        random_seed = self.get("var", "cocotb_random_seed")
        if random_seed:
            self.set_environmentalvariable("COCOTB_RANDOM_SEED", str(random_seed))

    def runtime_options(self):
        options = super().runtime_options()

        # Add trace options if tracing is enabled
        if self.get("var", "trace"):
            options.append("--trace")

            trace_type = self.get("var", "trace_type")
            if trace_type == "vcd":
                ext = "vcd"
            elif trace_type == "fst":
                ext = "fst"
            else:
                ext = "vcd"  # Default to VCD

            trace_file = f"reports/{self.design_topmodule}.{ext}"
            options.extend(["--trace-file", trace_file])

        return options

    def post_process(self):
        super().post_process()

        # Parse cocotb results XML and report metrics
        results_file = Path("outputs/results.xml")
        if results_file.exists():
            self._parse_cocotb_results(results_file)

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
