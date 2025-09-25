import contextlib
import re
import pathlib
import psutil
import shutil
import stat
import traceback

import os.path

from io import StringIO
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from typing import Dict

import sys
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from siliconcompiler.utils.paths import builddir


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


def get_file_ext(filename: str) -> str:
    '''Get base file extension for a given path, disregarding .gz.'''
    if filename.lower().endswith('.gz'):
        filename = os.path.splitext(filename)[0]
    filetype = os.path.splitext(filename)[1].lower().lstrip('.')
    return filetype


def get_default_iomap() -> Dict[str, str]:
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


def default_credentials_file() -> str:
    cfg_file = os.path.join(Path.home(), '.sc', 'credentials')

    return cfg_file


def default_cache_dir() -> str:
    cfg_file = os.path.join(Path.home(), '.sc', 'cache')

    return cfg_file


def default_email_credentials_file() -> str:
    cfg_file = os.path.join(Path.home(), '.sc', 'email.json')

    return cfg_file


@contextlib.contextmanager
def sc_open(path, *args, **kwargs):
    if 'errors' not in kwargs:
        kwargs['errors'] = 'ignore'
    kwargs["newline"] = "\n"
    fobj = open(path, *args, **kwargs)
    try:
        with contextlib.closing(fobj):
            yield fobj
    finally:
        pass


def get_file_template(path,
                      root=os.path.join(
                          os.path.dirname(
                              os.path.dirname(os.path.abspath(__file__))),
                          'data',
                          'templates')):
    if os.path.isabs(path):
        root = os.path.dirname(path)
        path = os.path.basename(path)

    import siliconcompiler
    scroot = os.path.dirname(siliconcompiler.__file__)

    env = Environment(loader=FileSystemLoader([root, scroot]))
    return env.get_template(path)


#######################################
def safecompare(value, op, goal):
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
def grep(project, args, line):
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
            project.logger.error(switches[i])

    # REGEX
    # TODO: add all the other optinos
    match = re.search(rf"({pattern})", line)
    if bool(match) == bool(options["-v"]):
        return None
    else:
        return line


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


def get_cores(physical=False):
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


def print_traceback(logger, exception):
    logger.error(f'{exception}')
    trace = StringIO()
    traceback.print_tb(exception.__traceback__, file=trace)
    logger.error("Backtrace:")
    for line in trace.getvalue().splitlines():
        logger.error(line)


class FilterDirectories:
    def __init__(self, project):
        self.file_count = 0
        self.directory_file_limit = None
        self.abspath = None
        self.project = project

    @property
    def logger(self):
        return self.project.logger

    @property
    def builddir(self):
        return builddir(self.project)

    def filter(self, path, files):
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
