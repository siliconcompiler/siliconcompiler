import contextlib
import hashlib
import os
import re
import psutil
import shutil
from pathlib import Path, PurePosixPath
from jinja2 import Environment, FileSystemLoader

import sys
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


def link_symlink_copy(srcfile, dstfile):
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
    # first try hard linking, then symbolic linking,
    # and finally just copy the file
    for method in [os.link, shutil.copy2]:
        try:
            # create link
            return method(srcfile, dstfile)
            # success, no need to continue trying
        except OSError:
            pass


def terminate_process(pid, timeout=3):
    '''Terminates a process and all its (grand+)children.

    Based on https://psutil.readthedocs.io/en/latest/#psutil.wait_procs and
    https://psutil.readthedocs.io/en/latest/#kill-process-tree.
    '''
    assert pid != os.getpid(), "won't terminate myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    children.append(parent)
    for p in children:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            # Process may have terminated on its own in the meantime
            pass

    _, alive = psutil.wait_procs(children, timeout=timeout)
    for p in alive:
        # If processes are still alive after timeout seconds, send more
        # aggressive signal.
        p.kill()


def get_file_ext(filename):
    '''Get base file extension for a given path, disregarding .gz.'''
    if filename.lower().endswith('.gz'):
        filename = os.path.splitext(filename)[0]
    filetype = os.path.splitext(filename)[1].lower().lstrip('.')
    return filetype


def get_default_iomap():
    """
    Default input file map for SC with filesets and extensions
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

    # Images
    image_dot = ('dot', 'xdot')
    image_png = ('png',)
    image_jpg = ('jpg', 'jpeg')
    image_bmp = ('bmp',)

    # Build default map with fileset and type
    default_iomap = {}
    default_iomap.update({ext: ('hll', 'c') for ext in hll_c})
    default_iomap.update({ext: ('hll', 'llvm') for ext in hll_llvm})
    default_iomap.update({ext: ('hll', 'bsv') for ext in hll_bsv})
    default_iomap.update({ext: ('hll', 'scala') for ext in hll_scala})
    default_iomap.update({ext: ('hll', 'python') for ext in hll_python})
    default_iomap.update({ext: ('config', 'chisel') for ext in config_chisel})

    default_iomap.update({ext: ('rtl', 'verilog') for ext in rtl_verilog})
    default_iomap.update({ext: ('rtl', 'systemverilog') for ext in rtl_systemverilog})
    default_iomap.update({ext: ('rtl', 'vhdl') for ext in rtl_vhdl})

    default_iomap.update({ext: ('timing', 'liberty') for ext in timing_liberty})

    default_iomap.update({ext: ('layout', 'def') for ext in layout_def})
    default_iomap.update({ext: ('layout', 'lef') for ext in layout_lef})
    default_iomap.update({ext: ('layout', 'gds') for ext in layout_gds})
    default_iomap.update({ext: ('layout', 'oas') for ext in layout_oas})
    default_iomap.update({ext: ('layout', 'gerber') for ext in layout_gerber})
    default_iomap.update({ext: ('layout', 'odb') for ext in layout_odb})

    default_iomap.update({ext: ('netlist', 'cdl') for ext in netlist_cdl})
    default_iomap.update({ext: ('netlist', 'sp') for ext in netlist_sp})
    default_iomap.update({ext: ('netlist', 'verilog') for ext in netlist_verilog})

    default_iomap.update({ext: ('waveform', 'vcd') for ext in waveform_vcd})

    default_iomap.update({ext: ('constraint', 'sdc') for ext in constraint_sdc})
    default_iomap.update({ext: ('constraint', 'upf') for ext in constraint_upf})
    default_iomap.update({ext: ('constraint', 'pcf') for ext in constraint_pcf})

    default_iomap.update({ext: ('fpga', 'xdc') for ext in fpga_xdc})
    default_iomap.update({ext: ('fpga', 'vpr_place') for ext in fpga_vpr_place})
    default_iomap.update({ext: ('fpga', 'vpr_route') for ext in fpga_vpr_route})

    default_iomap.update({ext: ('report', 'drc') for ext in report_drc})
    default_iomap.update({ext: ('report', 'log') for ext in report_log})

    default_iomap.update({ext: ('image', 'dot') for ext in image_dot})
    default_iomap.update({ext: ('image', 'png') for ext in image_png})
    default_iomap.update({ext: ('image', 'jpeg') for ext in image_jpg})
    default_iomap.update({ext: ('image', 'bitmap') for ext in image_bmp})

    return default_iomap


def format_fileset_type_table(indent=12):
    '''
    Generate a table to use in the __doc__ of the input function which auto
    updates based on the iomap
    '''
    table = "filetype      | fileset    | suffix (case insensitive)\n"
    indent = " " * indent
    table += f"{indent}--------------|------------|---------------------------------------------\n"

    iobytype = {}
    for ext, settype in get_default_iomap().items():
        fileset, filetype = settype
        iobytype.setdefault((fileset, filetype), []).append(ext)

    for settype, exts in iobytype.items():
        fileset, filetype = settype
        ext = ",".join(exts)
        table += f"{indent}{filetype:<14}| {fileset:<11}| {ext}\n"

    return table


def default_credentials_file():
    cfg_file = os.path.join(Path.home(), '.sc', 'credentials')

    return cfg_file


def default_cache_dir():
    cfg_file = os.path.join(Path.home(), '.sc', 'cache')

    return cfg_file


def default_email_credentials_file():
    cfg_file = os.path.join(Path.home(), '.sc', 'email.json')

    return cfg_file


@contextlib.contextmanager
def sc_open(path, *args, **kwargs):
    kwargs['errors'] = 'ignore_with_warning'
    fobj = open(path, *args, **kwargs)
    try:
        with contextlib.closing(fobj):
            yield fobj
    finally:
        pass


def get_file_template(path,
                      root=os.path.join(
                          os.path.dirname(
                              os.path.dirname(os.path.abspath(__file__))), 'templates')):
    if os.path.isabs(path):
        root = os.path.dirname(path)
        path = os.path.basename(path)

    import siliconcompiler
    scroot = os.path.dirname(siliconcompiler.__file__)

    env = Environment(loader=FileSystemLoader([root, scroot]))
    return env.get_template(path)


#######################################
def safecompare(chip, value, op, goal):
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
def grep(chip, args, line):
    """
    Emulates the Unix grep command on a string.

    Emulates the behavior of the Unix grep command that is etched into
    our muscle memory. Partially implemented, not all features supported.
    The function returns None if no match is found.

    Args:
        arg (string): Command line arguments for grep command
        line (string): Line to process

    Returns:
        Result of grep command (string).

    """

    # Quick return if input is None
    if line is None:
        return None

    # Partial list of supported grep options
    options = {
        '-v': False,  # Invert the sense of matching
        '-i': False,  # Ignore case distinctions in patterns and data
        '-E': False,  # Interpret PATTERNS as extended regular expressions.
        '-e': False,  # Safe interpretation of pattern starting with "-"
        '-x': False,  # Select only matches that exactly match the whole line.
        '-o': False,  # Print only the match parts of a matching line
        '-w': False}  # Select only lines containing matches that form whole words.

    # Split into repeating switches and everything else
    match = re.match(r'\s*((?:\-\w\s)*)(.*)', args)

    pattern = match.group(2)

    # Split space separated switch string into list
    switches = match.group(1).strip().split(' ')

    # Find special -e switch update the pattern
    for i in range(len(switches)):
        if switches[i] == "-e":
            if i != (len(switches)):
                pattern = ' '.join(switches[i + 1:]) + " " + pattern
                switches = switches[0:i + 1]
                break
            options["-e"] = True
        elif switches[i] in options.keys():
            options[switches[i]] = True
        elif switches[i] != '':
            chip.logger.error(switches[i])

    # REGEX
    # TODO: add all the other optinos
    match = re.search(rf"({pattern})", line)
    if bool(match) == bool(options["-v"]):
        return None
    else:
        return line


#######################################
def _resolve_env_vars(chip, filepath, step, index):
    if not filepath:
        return None

    env_save = os.environ.copy()

    os.environ.update(get_env_vars(chip, step, index))
    resolved_path = os.path.expandvars(filepath)

    os.environ.clear()
    os.environ.update(env_save)

    resolved_path = os.path.expanduser(resolved_path)

    # variables that don't exist in environment get ignored by `expandvars`,
    # but we can do our own error checking to ensure this doesn't result in
    # silent bugs
    envvars = re.findall(r'\$\{?(\w+)\}?', resolved_path)
    for var in envvars:
        chip.logger.warning(f'Variable {var} in {filepath} not defined in environment')

    return resolved_path


#######################################
def get_env_vars(chip, step, index):
    '''
    Returns a dictionary of environmental variables from the manifest
    '''

    schema_env = {}
    for env in chip.getkeys('option', 'env'):
        schema_env[env] = chip.get('option', 'env', env)

    flow = chip.get('option', 'flow')
    if step is not None and index is not None and flow:
        tool = chip.get('flowgraph', flow, step, str(index), 'tool')
        task = chip.get('flowgraph', flow, step, str(index), 'task')

        if chip.valid('tool', tool, 'task', task, 'env'):
            for env in chip.getkeys('tool', tool, 'task', task, 'env'):
                schema_env[env] = chip.get('tool', tool, 'task', task, 'env', env,
                                           step=step, index=index)

    return schema_env


###########################################################################
def find_sc_file(chip, filename, missing_ok=False, search_paths=None, step=None, index=None):
    """
    Returns the absolute path for the filename provided.

    Searches the for the filename provided and returns the absolute path.
    If no valid absolute path is found during the search, None is returned.

    Shell variables ('$' followed by strings consisting of numbers,
    underscores, and digits) are replaced with the variable value.

    Args:
        filename (str): Relative or absolute filename.
        missing_ok (bool): If False, error out if no valid absolute path
            found, rather than returning None.
        search_paths (list): List of directories to search under instead of
            the defaults.
        step (str): Step name
        index (str): Index

    Returns:
        Returns absolute path of 'filename' if found, otherwise returns
        None.

    Examples:
        >>> chip._find_sc_file('flows/asicflow.py')
        Returns the absolute path based on the sc installation directory.

    """

    if not filename:
        return None

    # Replacing environment variables
    filename = _resolve_env_vars(chip, filename, step, index)

    # If we have an absolute path, pass-through here
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename

    # Otherwise, search relative to search_paths
    if search_paths is None:
        search_paths = [chip.cwd]

    searchdirs = ', '.join([str(p) for p in search_paths])
    chip.logger.debug(f"Searching for file {filename} in {searchdirs}")

    result = None
    for searchdir in search_paths:
        if not os.path.isabs(searchdir):
            searchdir = os.path.join(chip.cwd, searchdir)

        abspath = os.path.abspath(os.path.join(searchdir, filename))
        if os.path.exists(abspath):
            result = abspath
            break

    if result is None and not missing_ok:
        chip.error(f"File {filename} was not found")

    return result


def get_plugins(system, name=None):
    '''
    Search for python modules with a specific function
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


def truncate_text(text, width):
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


def get_hashed_filename(path, package=None, hash=hashlib.sha1):
    '''
    Utility to map collected file to an unambiguous name based on its path.

    The mapping looks like:
    path/to/file.ext => file_<hash('path/to/file')>.ext
    '''
    path = PurePosixPath(path)
    ext = ''.join(path.suffixes)

    # strip off all file suffixes to get just the bare name
    barepath = path
    while barepath.suffix:
        barepath = PurePosixPath(barepath.stem)
    filename = str(barepath.parts[-1])

    if not package:
        package = ''
    else:
        package = f'{package}:'

    path_to_hash = f'{package}{str(path)}'

    pathhash = hash(path_to_hash.encode('utf-8')).hexdigest()

    return f'{filename}_{pathhash}{ext}'


def get_cores(chip, physical=False):
    '''
    Get max number of cores for this machine.

    Args:
        physical (boolean): if true, only count physical cores
    '''

    cores = psutil.cpu_count(logical=not physical)

    if not cores:
        cores = os.cpu_count()
        if physical and cores:
            # assume this is divide by 2
            cores = int(cores / 2)

    if not cores or cores < 1:
        cores = 1

    return cores
