import gzip
import os
from siliconcompiler import utils, sc_open


def is_file_is_binary(path, compressed):
    # Read first chunk and check for non characters
    try:
        if compressed:
            with gzip.open(path, 'rt') as f:
                f.read(8196)
        else:
            with open(path, "r") as f:
                f.read(8196)
    except UnicodeDecodeError:
        return True
    return False


def read_file(path, max_lines):
    _, compressed_file_extension = os.path.splitext(path.lower())
    file_info = []
    honor_max_file = max_lines is not None

    def read_file(fid):
        for line in fid:
            file_info.append(line.rstrip())
            if honor_max_file and len(file_info) >= max_lines:
                file_info.append('... truncated ...')
                return

    is_compressed = compressed_file_extension == '.gz'
    if is_file_is_binary(path, is_compressed):
        return "Binary file"

    if is_compressed:
        with gzip.open(path, 'rt') as fid:
            read_file(fid)
    else:
        with sc_open(path) as fid:
            read_file(fid)
    return "\n".join(file_info)


def get_file_type(ext):
    if ext in ("v", "vh", "sv", "svh", "vg"):
        return "verilog"
    if ext in ("vhdl", "vhd"):
        return "vhdl"
    if ext in ("tcl", "sdc", "xdc"):
        return "tcl"
    if ext in ("c", "cpp", "cc", "h"):
        return "cpp"
    if ext in ("csv",):
        return "csv"
    if ext in ("md",):
        return "markdown"
    if ext in ("sh",):
        return "bash"
    return "log"


def get_file_icon(file):
    if not file:
        return 'file'
    ext = utils.get_file_ext(file)
    file_type = get_file_type(ext)
    if file.endswith('.pkg.json'):
        return 'boxes'
    elif ext in ('png', 'jpg', 'jpeg'):
        return 'file-image'
    elif ext == 'json':
        return 'file-json'
    elif file_type in ('verilog', 'tcl', 'vhdl', 'cpp', 'bash'):
        return 'file-code'
    elif ext in ('log', 'rpt', 'drc', 'warnings', 'errors'):
        return 'file-text'
    return 'file'
