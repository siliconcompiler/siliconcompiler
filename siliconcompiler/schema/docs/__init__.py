import os.path

from pathlib import PureWindowsPath

import siliconcompiler
from siliconcompiler import __version__ as sc_version

from siliconcompiler.targets import get_targets
from siliconcompiler.flows import get_flows
from siliconcompiler.checklists import get_checklists
from siliconcompiler.libs import get_libs
from siliconcompiler.pdks import get_pdks
from siliconcompiler.apps import get_apps
from siliconcompiler.tools import get_tools


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


def targets():
    modules = []
    for name, mod in get_targets().items():
        modules.append((mod, name))
    return modules


def flows():
    modules = []
    for name, mod in get_flows().items():
        modules.append((mod, name))
    return modules


def libraries():
    modules = []
    for name, mod in get_libs().items():
        modules.append((mod, name))
    return modules


def pdks():
    modules = []
    for name, mod in get_pdks().items():
        modules.append((mod, name))
    return modules


def tools():
    modules = []
    for name, mod in get_tools().items():
        modules.append((mod, name))
    return modules


def apps():
    modules = []
    for name, mod in get_apps().items():
        modules.append((mod, name))
    return modules


def checklists():
    modules = []
    for name, mod in get_checklists().items():
        modules.append((mod, name))
    return modules
