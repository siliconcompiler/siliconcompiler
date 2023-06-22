#!/usr/bin/env python3
# Based on https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/7fd48d0e3b557156e56d4370116f1b9d465638ce/flow/util/mergeLib.pl  # noqa E501

import re


library_match = re.compile(r"^\s*library\s*\(")
cell_match = re.compile(r"^\s*cell\s*\(")


def mergeLib(lib_name, base_lib, additional_libs):
    new_lib = __copy_header(base_lib, lib_name)

    for lib in [base_lib, *additional_libs]:
        new_lib += __copy_cells(lib)

    new_lib += "}\n"

    return new_lib


def __copy_header(lib, lib_name):
    new_lib = ""
    for line in lib.splitlines():
        if library_match.match(line):
            new_lib += f"library ({lib_name}) {{\n"
        elif cell_match.match(line):
            break
        else:
            new_lib += line + "\n"

    return new_lib


def __copy_cells(lib):
    new_lib = ""
    flag = 0
    for line in lib.splitlines():
        if cell_match.match(line):
            flag = 1
            new_lib += line + "\n"
        elif flag > 0:
            if "{" in line:
                flag += 1
            if "}" in line:
                flag -= 1
            new_lib += line + "\n"

    return new_lib
