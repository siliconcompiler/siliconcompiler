"""
Utility functions for handling and displaying files in the web dashboard.

This module provides helpers for reading files (including compressed ones),
determining file types for syntax highlighting, selecting appropriate icons,
and structuring file lists into a hierarchical tree for UI components.
"""
import gzip
import os
from siliconcompiler import utils, sc_open


def is_file_is_binary(path, compressed):
    """
    Checks if a file is binary by attempting to read it as text.

    Args:
        path (str): The path to the file.
        compressed (bool): True if the file is gzip compressed.

    Returns:
        bool: True if a UnicodeDecodeError occurs (indicating binary content),
              False otherwise.
    """
    # Read the first chunk and check for non-text characters.
    try:
        if compressed:
            with gzip.open(path, 'rt', errors='strict') as f:
                f.read(8196)
        else:
            with open(path, "r", errors='strict') as f:
                f.read(8196)
    except UnicodeDecodeError:
        return True
    return False


def read_file(path, max_lines):
    """
    Reads the contents of a text file, with support for gzip compression.

    If the file is determined to be binary, it returns a placeholder string.
    If `max_lines` is specified, the file content will be truncated.

    Args:
        path (str): The path to the file to read.
        max_lines (int or None): The maximum number of lines to read. If None,
                                 the entire file is read.

    Returns:
        str: The content of the file as a single string, or a placeholder
             if the file is binary.
    """
    _, compressed_file_extension = os.path.splitext(path.lower())
    file_info = []
    honor_max_file = max_lines is not None

    def _read_lines(fid):
        """Helper to read lines from a file object and handle truncation."""
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
            _read_lines(fid)
    else:
        with sc_open(path) as fid:
            _read_lines(fid)
    return "\n".join(file_info)


def get_file_type(ext):
    """
    Maps a file extension to a language identifier for syntax highlighting.

    Args:
        ext (str): The file extension (without the dot).

    Returns:
        str: The language identifier (e.g., 'verilog', 'tcl'). Defaults to 'log'.
    """
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
    """
    Determines an appropriate icon name for a given file path.

    The icon name is based on the file's extension and type.

    Args:
        file (str): The path to the file.

    Returns:
        str: A string identifier for the icon (e.g., 'file-code', 'file-image').
    """
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


def convert_filepaths_to_select_tree(logs_and_reports):
    """
    Converts a flat list of file paths into a hierarchical tree structure.

    This structure is suitable for UI components like `streamlit_tree_select`.
    The function recursively builds the tree based on the directory structure.

    Args:
        logs_and_reports (list): A list of 3-tuples, where each tuple contains
            (path_name, list_of_folders, list_of_files).

    Returns:
        list: A list of dictionaries representing the root nodes of the tree.
    """
    if not logs_and_reports:
        return []

    # Create a dictionary for quick lookup of folder contents.
    all_files = {}
    for path_name, folders, files in logs_and_reports:
        all_files[path_name] = {
            'files': list(files),
            'folders': list(folders)
        }

    def organize_node(base_folder):
        """Recursively builds the node structure for a given folder."""
        nodes = []

        # Add sub-folders as expandable nodes.
        for folder in all_files[base_folder]['folders']:
            path = os.path.join(base_folder, folder)
            nodes.append({
                'value': path,
                'label': folder,
                'children': organize_node(path)
            })
        # Add files as leaf nodes.
        for file in all_files[base_folder]['files']:
            nodes.append({
                'value': os.path.join(base_folder, file),
                'label': file
            })

        return nodes

    # Start the recursion from the root path.
    starting_path_name = logs_and_reports[0][0]
    return organize_node(starting_path_name)
