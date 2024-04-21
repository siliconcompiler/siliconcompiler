#!/usr/bin/env python3
# Based on https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/7fd48d0e3b557156e56d4370116f1b9d465638ce/flow/util/mergeLib.pl  # noqa E501

import re


library_match = re.compile(r"^\s*library\s*\(")
cell_match = re.compile(r"^\s*cell\s*\(")
template_match = re.compile(r"^\s*[a-z_]+_template\s*\((.*)\)")


def mergeLib(lib_name, base_lib, additional_libs):
    new_lib = __copy_header(base_lib, lib_name)

    # First we have to rename all the templates from the other libraries (not the base one)
    add_libs = []
    for idx, lib in enumerate(additional_libs):
        templates = __find_templates(lib)
        lib2 = __rename_templates(lib, f'_sc_{idx}', templates)

        # Add templates to new header
        new_lib.extend(__copy_templates(lib2))

        add_libs.append(lib2)

    # Add cells
    for lib in [base_lib, *add_libs]:
        new_lib.extend(__copy_cells(lib))

    new_lib.append("}")

    return "\n".join(new_lib)


def __copy_header(lib, lib_name):
    new_lib = []
    for line in lib.splitlines():
        if library_match.match(line):
            new_lib.append(f"library ({lib_name}) {{")
        elif cell_match.match(line):
            break
        else:
            new_lib.append(line)

    return new_lib


def __copy_cells(lib):
    new_lib = []
    flag = 0
    for line in lib.splitlines():
        if cell_match.match(line):
            flag = 1
            new_lib.append(line)
        elif flag > 0:
            if "{" in line:
                flag += 1
            if "}" in line:
                flag -= 1
            new_lib.append(line)

    return new_lib


def __copy_templates(lib):
    new_tempates = []
    in_template = False
    for line in lib.splitlines():
        if template_match.match(line):
            in_template = True

        if in_template:
            new_tempates.append(line)
            if "}" in line:
                in_template = False

    return new_tempates


def __find_templates(lib):
    templates = []
    for line in lib.splitlines():
        m = template_match.match(line)
        if m:
            templates.append(m.group(1))

    return templates


def __rename_templates(lib, suffix, templates):
    pattern = re.compile(rf"\(\s*({'|'.join(templates)})\s*\)")
    lib = re.sub(pattern, f"(\\1{suffix})", lib)
    return lib
