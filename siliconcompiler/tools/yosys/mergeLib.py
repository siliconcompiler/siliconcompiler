#!/usr/bin/env python3
# Based on https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/7fd48d0e3b557156e56d4370116f1b9d465638ce/flow/util/mergeLib.pl  # noqa E501

import re


library_match  = re.compile(r"^\s*library\s*\(")
cell_match     = re.compile(r"^\s*cell\s*\(")
# For templates renaming
template_match = "_template("
template_end   = "){"


def mergeLib(lib_name, base_lib, additional_libs):
    new_lib = __copy_header(base_lib, lib_name)

    # First we have to rename all the templates from the other libraries (not the base one)
    add_libs = []
    for idx, lib in enumerate(additional_libs):
        items = find_template_items(lib)
        lib2  = re_template_items(lib, '_' + str(idx), items)
        add_libs.append(lib2)

    # Now we also have to copy all the templates for the different libraries
    for lib in add_libs:
        new_lib += __copy_templates(lib)

    for lib in [base_lib, *add_libs]:
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


def __copy_templates(lib):
    # Templates are expected to start from a _template( string and end with the first cell
    new_lib = ""
    start = 0
    for line in lib.splitlines():
        if line.find(template_match) != -1:
            new_lib += line + "\n"
            start = 1
        elif cell_match.match(line):
            break
        elif start == 1:
            new_lib += line + "\n"

    return new_lib

def find_template_items(lib):

    items = []
    for line in lib.splitlines():
        idx = line.find(template_match)
        if idx != -1:
            idx_end = line.find(template_end)
            items.append(line[idx+len(template_match):idx_end])
    return items


def re_template_items(lib, toadd, items):

    for item in items:
        pattern = re.compile(r"\b{}\b".format(item))
        newitem = item[:len(item)] + toadd
        lib     = re.sub(pattern, newitem, lib)
    return lib