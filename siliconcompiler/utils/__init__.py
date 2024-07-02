import contextlib
import os
import re
import psutil
import shutil
from pathlib import Path
from siliconcompiler._metadata import version as sc_version
from jinja2 import Environment, FileSystemLoader


PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_siliconcompiler_data_path = 'git+https://github.com/siliconcompiler/siliconcompiler'


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
    hll_c = ('c', 'cc', 'cpp', 'c++', 'cp', 'cxx', 'hpp')
    hll_bsv = ('bsv',)
    hll_scala = ('scala',)
    hll_python = ('py',)

    config_chisel = ('sbt',)

    # Register transfer languages
    rtl_verilog = ('v', 'sv', 'verilog')
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
    constraint_sdc = ('sdc', )
    constraint_upf = ('upf', )

    # FPGA constraints
    fpga_xdc = ('xdc',)
    constraint_pcf = ('pcf',)
    fpga_vpr_place = ('place',)
    fpga_vpr_route = ('route',)

    # Build default map with fileset and type
    default_iomap = {}
    default_iomap.update({ext: ('hll', 'c') for ext in hll_c})
    default_iomap.update({ext: ('hll', 'bsv') for ext in hll_bsv})
    default_iomap.update({ext: ('hll', 'scala') for ext in hll_scala})
    default_iomap.update({ext: ('hll', 'python') for ext in hll_python})
    default_iomap.update({ext: ('config', 'chisel') for ext in config_chisel})

    default_iomap.update({ext: ('rtl', 'verilog') for ext in rtl_verilog})
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

    return default_iomap


def format_fileset_type_table(indent=12):
    '''
    Generate a table to use in the __doc__ of the input function which auto
    updates based on the iomap
    '''
    table = "filetype  | fileset    | suffix (case insensitive)\n"
    indent = " " * indent
    table += f"{indent}----------|------------|---------------------------------------------\n"

    iobytype = {}
    for ext, settype in get_default_iomap().items():
        fileset, filetype = settype
        iobytype.setdefault((fileset, filetype), []).append(ext)

    for settype, exts in iobytype.items():
        fileset, filetype = settype
        ext = ",".join(exts)
        table += f"{indent}{filetype:<10}| {fileset:<11}| {ext}\n"

    return table


def default_credentials_file():
    cfg_file = os.path.join(Path.home(), '.sc', 'credentials')

    return cfg_file


def default_cache_dir():
    cfg_file = os.path.join(Path.home(), '.sc', 'cache')

    return cfg_file


def register_sc_data_source(chip):
    chip.register_package_source('siliconcompiler_data',
                                 _siliconcompiler_data_path,
                                 'v'+sc_version)


@contextlib.contextmanager
def sc_open(path, *args, **kwargs):
    kwargs['errors'] = 'ignore_with_warning'
    fobj = open(path, *args, **kwargs)
    try:
        with contextlib.closing(fobj):
            yield fobj
    finally:
        pass


def get_file_template(path, root=os.path.join(PACKAGE_ROOT, 'templates')):
    if os.path.isabs(path):
        root = os.path.dirname(path)
        path = os.path.basename(path)

    env = Environment(loader=FileSystemLoader(root))
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
        chip.error(f"Illegal comparison operation {op}")


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
