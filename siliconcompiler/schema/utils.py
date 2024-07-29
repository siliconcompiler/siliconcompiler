# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import os
import re
import sys

PACKAGE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def escape_val_tcl(val, typestr):
    '''Recursive helper function for converting Python values to safe TCL
    values, based on the SC type string.'''
    if val is None:
        return ''
    elif typestr.startswith('('):
        # Recurse into each item of tuple
        subtypes = typestr.strip('()').split(',')
        valstr = ' '.join(escape_val_tcl(v, subtype.strip())
                          for v, subtype in zip(val, subtypes))
        return f'[list {valstr}]'
    elif typestr.startswith('['):
        # Recurse into each item of list
        subtype = typestr.strip('[]')
        valstr = ' '.join(escape_val_tcl(v, subtype) for v in val)
        return f'[list {valstr}]'
    elif typestr == 'bool':
        return 'true' if val else 'false'
    elif typestr in ('str', 'enum'):
        # Escape string by surrounding it with "" and escaping the few
        # special characters that still get considered inside "". We don't
        # use {}, since this requires adding permanent backslashes to any
        # curly braces inside the string.
        # Source: https://www.tcl.tk/man/tcl8.4/TclCmd/Tcl.html (section [4] on)
        escaped_val = (val.replace('\\', '\\\\')  # escape '\' to avoid backslash substitution
                                                  # (do this first, since other replaces insert '\')
                          .replace('[', '\\[')    # escape '[' to avoid command substitution
                          .replace('$', '\\$')    # escape '$' to avoid variable substitution
                          .replace('"', '\\"'))   # escape '"' to avoid string terminating early
        return '"' + escaped_val + '"'
    elif typestr in ('file', 'dir'):
        # Replace $VAR with $env(VAR) for tcl
        val = re.sub(r'\$(\w+)', r'$env(\1)', val)
        # Same escapes as applied to string, minus $ (since we want to resolve env vars).
        escaped_val = (val.replace('\\', '\\\\')  # escape '\' to avoid backslash substitution
                                                  # (do this first, since other replaces insert '\')
                          .replace('[', '\\[')    # escape '[' to avoid command substitution
                          .replace('"', '\\"'))   # escape '"' to avoid string terminating early
        return '"' + escaped_val + '"'
    elif typestr in ('int', 'float'):
        # floats/ints just become strings
        return str(val)
    else:
        raise TypeError(f'{typestr} is not a supported type')


def trim(docstring):
    '''Helper function for cleaning up indentation of docstring.

    This is important for properly parsing complex RST in our docs.

    Source:
    https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation'''
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def translate_loglevel(level):
    return level.upper()
