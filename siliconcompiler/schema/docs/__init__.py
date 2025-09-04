import os.path

from pathlib import PureWindowsPath

import siliconcompiler
from siliconcompiler import __version__ as sc_version


sc_root = os.path.dirname(os.path.dirname(os.path.abspath(siliconcompiler.__file__)))


def relpath(file):
    file = os.path.abspath(file)
    if file.startswith(sc_root):
        return PureWindowsPath(os.path.relpath(file, sc_root)).as_posix()
    return None


def get_codeurl(file=None):
    base_url = f"https://github.com/siliconcompiler/siliconcompiler/blob/v{sc_version}"

    if not file:
        return base_url

    if os.path.isabs(file):
        file = relpath(file)
        if not file:
            return None

    return f"{base_url}/{file}"
