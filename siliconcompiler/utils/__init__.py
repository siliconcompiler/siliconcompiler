import contextlib
import logging
import re
import pathlib
import psutil
import shutil
import stat
import traceback

import os.path

from io import StringIO
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template

from typing import Dict, Optional, Union, Callable, List, TYPE_CHECKING

import importlib.util
from importlib.metadata import distributions, entry_points

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

try:
    import tomllib
except ImportError:  # Python < 3.11
    try:
        import tomli as tomllib
    except ImportError:  # pragma: no cover - only when tomli is not yet installed
        tomllib = None

from siliconcompiler.utils.paths import builddir

if TYPE_CHECKING:
    from siliconcompiler.project import Project


def link_symlink_copy(srcfile, dstfile):
    """
    Attempts to link a source file to a destination using hard link, symbolic link,
    or copy, in that order.

    Args:
        srcfile (str): Path to the source file.
        dstfile (str): Path to the destination file.
    """
    # first try hard linking, then symbolic linking,
    # and finally just copy the file
    for method in [os.link, os.symlink, shutil.copy2]:
        try:
            # create link
            return method(srcfile, dstfile)
            # success, no need to continue trying
        except OSError:
            pass


def link_copy(srcfile, dstfile):
    """
    Attempts to link a source file to a destination using hard link or copy,
    in that order.

    Args:
        srcfile (str): Path to the source file.
        dstfile (str): Path to the destination file.
    """
    # first try hard linking or just copy the file
    for method in [os.link, shutil.copy2]:
        try:
            # create link
            return method(srcfile, dstfile)
            # success, no need to continue trying
        except OSError:
            pass


def get_file_ext(filename: Union[Path, str]) -> str:
    """
    Get base file extension for a given path, disregarding .gz.

    Args:
        filename (str): The filename to extract the extension from.

    Returns:
        str: The file extension (e.g., 'v', 'py') without the dot.
    """
    filename = str(filename)
    if filename.lower().endswith('.gz'):
        filename = os.path.splitext(filename)[0]
    filetype = os.path.splitext(filename)[1].lower().lstrip('.')
    return filetype


def get_default_iomap() -> Dict[str, str]:
    """
    Returns the default input file map for SC with filesets and extensions.

    Returns:
        Dict[str, str]: A dictionary mapping file extensions to their SiliconCompiler type.
    """

    # Record extensions:

    # High level languages
    hll_c = ('c', 'cc', 'cpp', 'c++', 'cp', 'cxx', 'hpp', 'h')
    hll_llvm = ('ll',)
    hll_bsv = ('bsv',)
    hll_scala = ('scala',)
    hll_python = ('py',)

    config_chisel = ('sbt',)

    # Register transfer languages
    rtl_verilog = ('v', 'verilog', 'vh')
    rtl_systemverilog = ('sv', 'svh')
    rtl_vhdl = ('vhd', 'vhdl')

    # Timing libraries
    timing_liberty = ('lib', 'ccs')

    # Layout
    layout_def = ('def',)
    layout_lef = ('lef',)
    layout_gds = ('gds', 'gds2', 'gdsii')
    layout_oas = ('oas', 'oasis')
    layout_gerber = ('gbr', 'gerber')
    layout_odb = ('odb',)

    # Netlist
    netlist_cdl = ('cdl',)
    netlist_sp = ('sp', 'spice')
    netlist_verilog = ('vg',)

    # Waveform
    waveform_vcd = ('vcd',)

    # Constraint
    constraint_sdc = ('sdc',)
    constraint_upf = ('upf',)

    # FPGA constraints
    fpga_xdc = ('xdc',)
    constraint_pcf = ('pcf',)
    fpga_vpr_place = ('place',)
    fpga_vpr_route = ('route',)

    # Reports
    report_drc = ('lyrdb', 'ascii')
    report_log = ('log',)

    # Scripts
    tcl = ('tcl',)

    # Verilator control file
    verilator = ('vlt',)

    # Images
    image_dot = ('dot', 'xdot')
    image_png = ('png',)
    image_jpg = ('jpg', 'jpeg')
    image_bmp = ('bmp',)

    # Build default map with fileset and type
    default_iomap = {}
    default_iomap.update({ext: "c" for ext in hll_c})
    default_iomap.update({ext: "llvm" for ext in hll_llvm})
    default_iomap.update({ext: "bsv" for ext in hll_bsv})
    default_iomap.update({ext: "scala" for ext in hll_scala})
    default_iomap.update({ext: "python" for ext in hll_python})
    default_iomap.update({ext: "chisel" for ext in config_chisel})

    default_iomap.update({ext: "verilog" for ext in rtl_verilog})
    default_iomap.update({ext: "systemverilog" for ext in rtl_systemverilog})
    default_iomap.update({ext: "vhdl" for ext in rtl_vhdl})

    default_iomap.update({ext: "liberty" for ext in timing_liberty})

    default_iomap.update({ext: "def" for ext in layout_def})
    default_iomap.update({ext: "lef" for ext in layout_lef})
    default_iomap.update({ext: "gds" for ext in layout_gds})
    default_iomap.update({ext: "oas" for ext in layout_oas})
    default_iomap.update({ext: "gerber" for ext in layout_gerber})
    default_iomap.update({ext: "odb" for ext in layout_odb})

    default_iomap.update({ext: "cdl" for ext in netlist_cdl})
    default_iomap.update({ext: "sp" for ext in netlist_sp})
    default_iomap.update({ext: "verilog" for ext in netlist_verilog})

    default_iomap.update({ext: "vcd" for ext in waveform_vcd})

    default_iomap.update({ext: "sdc" for ext in constraint_sdc})
    default_iomap.update({ext: "upf" for ext in constraint_upf})
    default_iomap.update({ext: "pcf" for ext in constraint_pcf})

    default_iomap.update({ext: "xdc" for ext in fpga_xdc})
    default_iomap.update({ext: "vpr_place" for ext in fpga_vpr_place})
    default_iomap.update({ext: "vpr_route" for ext in fpga_vpr_route})

    default_iomap.update({ext: "drc" for ext in report_drc})
    default_iomap.update({ext: "log" for ext in report_log})

    default_iomap.update({ext: "dot" for ext in image_dot})
    default_iomap.update({ext: "png" for ext in image_png})
    default_iomap.update({ext: "jpeg" for ext in image_jpg})
    default_iomap.update({ext: "bitmap" for ext in image_bmp})

    default_iomap.update({ext: "tcl" for ext in tcl})

    default_iomap.update({ext: "verilatorctrlfile" for ext in verilator})

    return default_iomap


def default_sc_dir() -> str:
    """
    Returns the default SiliconCompiler configuration directory.

    Returns:
        str: The absolute path to the .sc directory in the user's home folder.
    """
    return os.path.join(Path.home(), '.sc')


def default_sc_path(path: str) -> str:
    """
    Returns a path relative to the default SiliconCompiler configuration directory.

    Args:
        path (str): The relative path to append to the default SC directory.

    Returns:
        str: The absolute path joined with the default SC directory.
    """
    return os.path.join(default_sc_dir(), path)


def default_credentials_file() -> str:
    """
    Returns the default path for the SiliconCompiler credentials file.

    Returns:
        str: The absolute path to the credentials file.
    """
    return default_sc_path('credentials')


def default_cache_dir() -> str:
    """
    Returns the default path for the SiliconCompiler cache directory.

    Returns:
        str: The absolute path to the cache directory.
    """
    return default_sc_path('cache')


def default_email_credentials_file() -> str:
    """
    Returns the default path for the SiliconCompiler email credentials file.

    Returns:
        str: The absolute path to the email.json file.
    """
    return default_sc_path('email.json')


@contextlib.contextmanager
def sc_open(path: str, *args, **kwargs):
    """
    A context manager for opening files with default settings convenient for SC.

    Sets ``errors='ignore'`` and ``newline='\n'`` by default unless overridden.

    Args:
        path (str): The file path to open.
        *args: Positional arguments passed to the builtin open().
        **kwargs: Keyword arguments passed to the builtin open().
    """
    if 'errors' not in kwargs:
        kwargs['errors'] = 'ignore'
    kwargs["newline"] = "\n"
    fobj = open(path, *args, **kwargs)
    try:
        with contextlib.closing(fobj):
            yield fobj
    finally:
        pass


def get_file_template(path: str,
                      root: str = os.path.join(
                          os.path.dirname(
                              os.path.dirname(os.path.abspath(__file__))),
                          'data',
                          'templates')) -> Template:
    """
    Retrieves a Jinja2 template object for the specified file.

    Args:
        path (str): The name of the template file or an absolute path to it.
        root (str, optional): The root directory to search for templates if path
            is relative. Defaults to the SiliconCompiler data/templates directory.

    Returns:
        Template: The loaded Jinja2 Template object.
    """
    if os.path.isabs(path):
        root = os.path.dirname(path)
        path = os.path.basename(path)

    import siliconcompiler
    scroot = os.path.dirname(siliconcompiler.__file__)

    env = Environment(loader=FileSystemLoader([root, scroot]))
    return env.get_template(path)


#######################################
def safecompare(value: Union[int, float], op: str, goal: Union[int, float]) -> bool:
    """
    Compares a value against a goal using a string operator.

    Args:
        value (Union[int, float]): The value to compare.
        op (str): The comparison operator ('>', '>=', '<', '<=', '==', '!=').
        goal (Union[int, float]): The target value to compare against.

    Returns:
        bool: The result of the comparison.

    Raises:
        ValueError: If the provided operator is not supported.
    """
    # supported relational operations
    # >, >=, <=, <. ==, !=
    if op == ">":
        return bool(value > goal)
    elif op == ">=":
        return bool(value >= goal)
    elif op == "<":
        return bool(value < goal)
    elif op == "<=":
        return bool(value <= goal)
    elif op == "==":
        return bool(value == goal)
    elif op == "!=":
        return bool(value != goal)
    else:
        raise ValueError(f"Illegal comparison operation {op}")


###########################################################################
def grep(logger: logging.Logger, args: str, line: str) -> Union[None, str]:
    """
    Emulates the Unix grep command on a string.

    Args:
        logger (logging.Logger): used for logging errors.
        args (str): Command line arguments for grep command.
        line (str): Line to process.

    Returns:
        Union[None, str]: Result of grep command (string) or None if no match.
    """

    # Quick return if input is None
    if line is None:
        return None

    # --- 1. Initialize Options and Parse Arguments ---
    options = {
        '-v': False,  # Invert the sense of matching
        '-i': False,  # Ignore case distinctions
        '-E': False,  # Extended regular expressions (Python's 're' module is ERE by default)
        '-e': False,  # Pattern starts with '-' (simplified logic)
        '-x': False,  # Exact line match
        '-o': False,  # Print only the match
        '-w': False}  # Whole word match

    parts = args.split()
    pattern = ""
    pattern_start_index = -1

    # Identify switches and the start of the pattern
    for i, part in enumerate(parts):
        # Check for switch starting with '-' and not just '-'
        if part.startswith('-') and len(part) > 1 and part != '-e':
            # Handle concatenated switches (e.g., -vi)
            is_valid_switch_group = True
            for char in part[1:]:
                switch = f"-{char}"
                if switch in options:
                    options[switch] = True
                else:
                    logger.error(f"Unknown switch: {switch}")
                    is_valid_switch_group = False
                    break
            if not is_valid_switch_group:
                # If an invalid switch was found, the rest must be the pattern
                pattern_start_index = i
                break
        elif part == '-e':
            # The next part is the pattern, regardless of what it looks like
            options['-e'] = True
            if i + 1 < len(parts):
                pattern_start_index = i + 1
            break
        elif not pattern.strip():
            # First non-switch part is the start of the pattern
            pattern_start_index = i
            break

    # Assemble the pattern from the determined starting index
    if pattern_start_index != -1:
        pattern = " ".join(parts[pattern_start_index:])

    if not pattern:
        return None

    # --- 2. Prepare Regex Flags and Pattern Modifiers ---

    regex_flags = 0
    if options['-i']:
        regex_flags |= re.IGNORECASE

    # Apply Whole Word (-w)
    pattern_to_search = pattern
    if options['-w']:
        # Apply word boundaries
        pattern_to_search = rf"\b({pattern})\b"

    # Apply Whole Line (-x)
    if options['-x']:
        # Exact line match, using the prepared pattern (which may have \b already)
        pattern_to_search = rf"^{pattern_to_search}$"

    # --- 3. Perform Search ---
    try:
        # re.search is used to find the pattern anywhere in the line
        match = re.search(pattern_to_search, line, regex_flags)
    except re.error as e:
        # Handle cases where the pattern itself is invalid regex
        logger.error(f"Invalid regex pattern '{pattern}': {e}")
        return None

    # --- 4. Handle Inversion (-v) and Final Return ---

    # Check if a result should be returned: (Match found) XOR (Invert is on)
    should_return = bool(match) != options["-v"]

    if should_return:
        if options['-o'] and match:
            # Print only the match part (which is match.group(0))
            return match.group(0)
        else:
            # Return the whole line (standard behavior)
            return line
    else:
        # Match found AND inverted, OR Match NOT found AND not inverted
        return None


def get_plugins(system: str, name: Optional[str] = None) -> List[Callable]:
    '''
    Search for python modules with a specific function.

    Args:
        system (str): The system/group to search within (e.g. 'siliconcompiler.metrics').
        name (str, optional): Specific plugin name to filter by.

    Returns:
        List[Callable]: A list of loaded plugin functions.
    '''
    plugins = []
    discovered_plugins = entry_points(group=f'siliconcompiler.{system}')
    for plugin in discovered_plugins:
        if name:
            if plugin.name == name:
                plugins.append(plugin.load())
        else:
            plugins.append(plugin.load())

    return plugins


def truncate_text(text: str, width: int) -> str:
    """
    Truncates text to a specific width, replacing the middle with '...'.

    Attempts to preserve the end of the string if it appears to be a version number
    or numeric index.

    Args:
        text (str): The text to truncate.
        width (int): The maximum desired width of the text.

    Returns:
        str: The truncated text.
    """
    width = max(width, 5)

    if len(text) <= width:
        return text

    keep_end = 0
    while text[-1 - keep_end].isnumeric():
        if keep_end >= 2:
            break
        keep_end += 1

    while len(text) > width:
        break_at = len(text) - keep_end - 3
        text = text[:break_at-1] + '...' + text[break_at+3:]

    return text


def get_cores(physical: bool = False) -> int:
    '''
    Get max number of cores available to this process.

    On Linux this honors the process' CPU affinity mask, so restrictions
    applied via cgroups/cpuset (e.g. containers) or ``taskset`` cap the value
    returned. This lets an operator bound SiliconCompiler's CPU usage without
    any additional configuration. On platforms without affinity support the
    machine-wide core count is used instead.

    Args:
        physical (bool): if true, only count physical cores. Defaults to False.

    Returns:
        int: The number of available cores. Defaults to 1 if detection fails.
    '''

    cores = None

    try:
        # os.sched_getaffinity respects cgroup/cpuset and taskset restrictions,
        # so it reflects the cores actually usable by this process rather than
        # every core on the machine.
        logical_available = len(os.sched_getaffinity(0))
    except AttributeError:
        # Not available on this platform (e.g. macOS, Windows).
        logical_available = None

    if logical_available:
        if physical:
            # sched_getaffinity only reports logical CPUs, so scale the
            # affinity-limited count down by the machine's hyperthreading
            # ratio to approximate the number of physical cores available.
            total_logical = psutil.cpu_count(logical=True)
            total_physical = psutil.cpu_count(logical=False)
            if total_logical and total_physical and total_physical < total_logical:
                threads_per_core = total_logical / total_physical
                # Clamp to at least 1 so a tight affinity mask (e.g. a single
                # logical CPU) still reports a usable core rather than falling
                # through to the machine-wide fallback below.
                cores = max(1, int(logical_available / threads_per_core))
            else:
                cores = logical_available
        else:
            cores = logical_available

    if not cores:
        cores = psutil.cpu_count(logical=not physical)

    if not cores:
        cores = os.cpu_count()
        if physical and cores:
            # assume this is divide by 2
            cores = int(cores / 2)

    if not cores or cores < 1:
        cores = 1

    return cores


def print_traceback(logger: logging.Logger, exception: Exception):
    """
    Prints the full traceback of an exception to the provided logger.

    Args:
        logger (logging.Logger): The logger instance to write the traceback to.
        exception (Exception): The exception to log.
    """
    logger.error(f'{exception}')
    trace = StringIO()
    traceback.print_tb(exception.__traceback__, file=trace)
    logger.error("Backtrace:")
    for line in trace.getvalue().splitlines():
        logger.error(line)


# Optional-dependency groups that provide development, testing, or CI tooling
# rather than runtime functionality. These are skipped by the pre-run dependency
# check because they are not required to execute a flow. Names are matched
# case-insensitively.
_IGNORED_OPTIONAL_GROUPS = frozenset({
    "test", "tests", "testing",
    "dev", "develop", "development",
    "lint", "linting",
    "doc", "docs", "documentation",
    "type", "types", "typing", "mypy",
    "cov", "coverage",
    "ci", "cicd",
    "build",
    "release",
    "format", "formatting", "style",
    "bench", "benchmark", "benchmarks",
    "check", "checks",
})


def _load_pyproject_data(pyproject_path: str) -> Optional[Dict]:
    """
    Parses a pyproject.toml file.

    Args:
        pyproject_path (str): Path to the pyproject.toml file.

    Returns:
        dict or None: The parsed contents, or None if the file is missing,
            malformed, or no TOML parser is available.
    """
    if tomllib is None:
        return None

    try:
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)
    except (OSError, ValueError):
        # ValueError covers tomllib.TOMLDecodeError (a ValueError subclass).
        return None


def _installed_distribution_versions() -> Dict[str, str]:
    """
    Maps canonicalized distribution names to their installed versions.

    Returns:
        dict: A mapping of :func:`packaging.utils.canonicalize_name` names to
            installed version strings for every distribution in the environment.
    """
    installed: Dict[str, str] = {}
    for dist in distributions():
        try:
            name = dist.metadata["Name"]
        except Exception:
            name = None
        if not name:
            continue
        canon = canonicalize_name(name)
        # Multiple site directories may expose the same distribution; keep the
        # first one found (matches import resolution order).
        if canon not in installed:
            installed[canon] = dist.version
    return installed


def _evaluate_requirement(req_str: str, installed: Dict[str, str]):
    """
    Evaluates a single PEP 508 requirement against the installed environment.

    Args:
        req_str (str): The raw requirement string from pyproject.toml.
        installed (dict): Mapping of canonicalized names to installed versions.

    Returns:
        tuple: ``(status, name, have)`` where ``status`` is one of ``"ok"``,
            ``"missing"``, ``"incompatible"``, or ``"skip"``. ``name`` is the
            distribution name (or None when unparsable) and ``have`` is the
            installed version (or None when not installed).
    """
    try:
        req = Requirement(req_str)
    except Exception:
        # Unparsable requirement (e.g. a bare URL); nothing actionable to report.
        return ("skip", None, None)

    try:
        if req.marker is not None and not req.marker.evaluate():
            # Requirement does not apply to this environment (OS/Python version).
            return ("skip", None, None)
    except Exception:
        return ("skip", None, None)

    name = req.name
    canon = canonicalize_name(name)
    if canon not in installed:
        return ("missing", name, None)

    have = installed[canon]
    try:
        if req.specifier and not req.specifier.contains(have, prereleases=True):
            return ("incompatible", name, have)
    except Exception:
        # Installed version could not be compared (non-PEP440); do not report.
        return ("skip", name, have)

    return ("ok", name, have)


def _check_optional_group(group: str, reqs: List, installed: Dict[str, str],
                          proj_name: str, logger: logging.Logger) -> int:
    """
    Reports issues for a single optional-dependencies group.

    A group is only treated as "opted into" when all-but-one of its applicable
    members are installed; only then are missing members reported. Version
    incompatibilities are always reported for members that are installed,
    regardless of whether the group is considered active.

    Returns:
        int: The number of issues reported for this group.
    """
    applicable = []
    for req_str in reqs:
        if not isinstance(req_str, str):
            continue
        status, name, have = _evaluate_requirement(req_str, installed)
        if status == "skip":
            continue
        applicable.append((req_str, status, name, have))

    if not applicable:
        return 0

    installed_count = sum(1 for (_, status, _, _) in applicable if status != "missing")
    # "active" == all-but-one applicable members are present (and at least one is).
    active = installed_count > 0 and installed_count >= len(applicable) - 1

    issues = 0
    for req_str, status, name, have in applicable:
        if status == "incompatible":
            logger.warning(
                f"installed '{name}' ({have}) does not satisfy '{req_str.strip()}' "
                f"from optional group '{group}' in {proj_name}")
            issues += 1
        elif status == "missing" and active:
            logger.warning(
                f"optional group '{group}' in {proj_name} appears installed, but "
                f"'{name}' is missing (declared as '{req_str.strip()}')")
            issues += 1
    return issues


def _check_project_dependencies(data: Dict, installed: Dict[str, str],
                                logger: logging.Logger) -> int:
    """
    Reports declared-vs-installed dependency issues for a parsed pyproject.toml.

    Args:
        data (dict): Parsed pyproject.toml contents.
        installed (dict): Mapping of canonicalized names to installed versions.
        logger (logging.Logger): Logger used to emit warnings.

    Returns:
        int: Total number of issues reported.
    """
    project = data.get("project") if isinstance(data, dict) else None
    if not isinstance(project, dict):
        return 0

    proj_name = project.get("name") or "this project"
    issues = 0

    core = project.get("dependencies")
    if isinstance(core, list):
        for req_str in core:
            if not isinstance(req_str, str):
                continue
            status, name, have = _evaluate_requirement(req_str, installed)
            if status == "missing":
                logger.warning(
                    f"required dependency '{name}' is declared in {proj_name}'s "
                    f"pyproject.toml but is not installed")
                issues += 1
            elif status == "incompatible":
                logger.warning(
                    f"installed '{name}' ({have}) does not satisfy "
                    f"'{req_str.strip()}' declared in {proj_name}'s pyproject.toml")
                issues += 1

    groups_with_issues = []
    optional = project.get("optional-dependencies")
    if isinstance(optional, dict):
        for group, reqs in optional.items():
            if not isinstance(reqs, list):
                continue
            if isinstance(group, str) and group.lower() in _IGNORED_OPTIONAL_GROUPS:
                # Development/testing tooling is not required to run a flow.
                continue
            group_issues = _check_optional_group(group, reqs, installed, proj_name, logger)
            if group_issues:
                groups_with_issues.append(group)
            issues += group_issues

    if issues:
        # Include any affected optional groups so the reinstall covers them too.
        if groups_with_issues:
            target = f".[{','.join(groups_with_issues)}]"
        else:
            target = "."
        logger.warning(
            f"{proj_name} environment is out of sync with pyproject.toml; "
            f"run 'pip install -e {target}' to update")
    return issues


def _locate_pyproject_for_module(module: str) -> Optional[str]:
    """
    Finds the source pyproject.toml associated with an importable module.

    Walks upward from the module's location to the nearest ancestor directory
    containing a pyproject.toml.

    Args:
        module (str): The top-level importable module name.

    Returns:
        str or None: Absolute path to the pyproject.toml, or None if not found.
    """
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError, AttributeError, ModuleNotFoundError):
        return None
    if spec is None:
        return None

    if spec.origin and spec.origin != "namespace":
        start = os.path.dirname(spec.origin)
    else:
        locations = list(spec.submodule_search_locations or [])
        if not locations:
            return None
        start = locations[0]

    current = os.path.abspath(start)
    while True:
        candidate = os.path.join(current, "pyproject.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _find_editable_pyproject_paths() -> List[str]:
    """
    Locates source pyproject.toml files for all editable-installed distributions.

    Reuses :class:`siliconcompiler.package.PythonPathResolver` to enumerate
    importable modules and to determine which are installed in editable mode.

    Returns:
        list: Absolute paths to discovered pyproject.toml files, de-duplicated.
    """
    # Imported lazily: siliconcompiler.package imports from siliconcompiler.utils,
    # so a module-level import here would be circular.
    try:
        from siliconcompiler.package import PythonPathResolver
    except Exception:
        return []

    try:
        mapping = PythonPathResolver.get_python_module_mapping()
    except Exception:
        return []

    paths: List[str] = []
    seen = set()
    for module in mapping:
        try:
            if not PythonPathResolver.is_python_module_editable(module):
                continue
        except Exception:
            continue

        pyproject = _locate_pyproject_for_module(module)
        if pyproject and pyproject not in seen:
            seen.add(pyproject)
            paths.append(pyproject)
    return paths


def check_python_dependencies(logger: logging.Logger) -> None:
    """
    Warns when an editable install's environment is out of sync with its
    declared pyproject.toml dependencies.

    This is a purely informative pre-run check aimed at editable (``pip install
    -e .``) installs, where changes to ``pyproject.toml`` are not reflected in
    the environment until a reinstall. For every editable-installed distribution
    whose source pyproject.toml can be located, declared dependencies are
    compared against what is actually installed, and mismatches are logged as
    warnings. Non-editable installs are skipped because their metadata is
    authoritative.

    The check never raises: any unexpected failure is logged at debug level so
    that it can never interfere with a run.

    Args:
        logger (logging.Logger): Logger used to emit warnings.
    """
    try:
        installed = _installed_distribution_versions()
        for pyproject in _find_editable_pyproject_paths():
            data = _load_pyproject_data(pyproject)
            if data is None:
                continue
            _check_project_dependencies(data, installed, logger)
    except Exception as e:
        logger.debug(f"python dependency check skipped: {e}")


class FilterDirectories:
    """
    A helper class to filter directories and files during file collection.

    This class prevents collecting files from the home directory, the build directory,
    and hidden files (on Linux, Windows, and macOS). It also enforces a limit on the
    number of files collected.
    """
    def __init__(self, project: "Project"):
        self.file_count = 0
        self.directory_file_limit = None
        self.abspath = None
        self.project = project

    @property
    def logger(self) -> logging.Logger:
        return self.project.logger

    @property
    def builddir(self) -> str:
        return builddir(self.project)

    def filter(self, path: str, files: List[str]) -> List[str]:
        """
        Filters a list of files based on the current directory path.

        Args:
            path (str): The current directory path being traversed.
            files (List[str]): The list of filenames in that directory.

        Returns:
            List[str]: A list of filenames that should be excluded (i.e., hidden files)
                or handled specifically. Note that despite the name returning 'hidden_files',
                the logic is essentially identifying what to *exclude* from the main processing
                loop in some contexts, or identifying hidden files to ignore.
        """
        if pathlib.Path(path) == pathlib.Path.home():
            # refuse to collect home directory
            self.logger.error(f'Cannot collect user home directory: {path}')
            return files

        if pathlib.Path(path) == pathlib.Path(self.builddir):
            # refuse to collect build directory
            self.logger.error(f'Cannot collect build directory: {path}')
            return files

        # do not collect hidden files
        hidden_files = []
        # filter out hidden files (unix)
        hidden_files.extend([f for f in files if f.startswith('.')])
        # filter out hidden files (windows)
        try:
            if hasattr(os.stat_result, 'st_file_attributes'):
                hidden_files.extend([
                    f for f in files
                    if bool(os.stat(os.path.join(path, f)).st_file_attributes &
                            stat.FILE_ATTRIBUTE_HIDDEN)
                ])
        except:  # noqa 722
            pass
        # filter out hidden files (macos)
        try:
            if hasattr(os.stat_result, 'st_reparse_tag'):
                hidden_files.extend([
                    f for f in files
                    if bool(os.stat(os.path.join(path, f)).st_reparse_tag &
                            stat.UF_HIDDEN)
                ])
        except:  # noqa 722
            pass

        self.file_count += len(files) - len(hidden_files)

        if self.directory_file_limit and \
                self.file_count > self.directory_file_limit:
            self.logger.error(f'File collection from {self.abspath} exceeds '
                              f'{self.directory_file_limit} files')
            return files

        return hidden_files
