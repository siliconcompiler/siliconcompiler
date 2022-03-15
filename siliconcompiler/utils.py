import os
import shutil
import sys

def copytree(src, dst, ignore=[], dirs_exist_ok=False, link=False):
    '''Simple implementation of shutil.copytree to give us a dirs_exist_ok
    option in Python < 3.8.

    If link is True, create hard links in dst pointing to files in src
    instead of copying them.
    '''
    os.makedirs(dst, exist_ok=dirs_exist_ok)

    for name in os.listdir(src):
        if name in ignore:
            continue

        srcfile = os.path.join(src, name)
        dstfile = os.path.join(dst, name)

        if os.path.isdir(srcfile):
            copytree(srcfile, dstfile, ignore=ignore, dirs_exist_ok=dirs_exist_ok)
        elif link:
            os.link(srcfile, dstfile)
        else:
            shutil.copy2(srcfile, dstfile)

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
