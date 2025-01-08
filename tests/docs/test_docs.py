import pkgutil
import os

from siliconcompiler import targets
from siliconcompiler import flows
from siliconcompiler import checklists
from siliconcompiler import libs
from siliconcompiler import pdks
from siliconcompiler import apps
from siliconcompiler import tools


def test_get_targets():
    all_targets = targets.get_targets()

    check_targets = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(targets.__file__)])
    ])

    assert check_targets == set(all_targets.keys())


def test_get_flows():
    all_flows = flows.get_flows()

    check_flows = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(flows.__file__)])
    ])
    check_flows.remove('_common')

    assert check_flows == set(all_flows.keys())


def test_get_checklists():
    all_checklists = checklists.get_checklists()

    check_checklists = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(checklists.__file__)])
    ])

    assert check_checklists == set(all_checklists.keys())


def test_get_apps():
    all_apps = apps.get_apps()

    check_apps = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(apps.__file__)])
    ])
    check_apps.remove('_common')

    assert check_apps == set(all_apps.keys())


def test_get_libs():
    all_libs = libs.get_libs()

    check_libs = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(libs.__file__)])
    ])

    assert check_libs == set(all_libs.keys())


def test_get_pdks():
    all_pdks = pdks.get_pdks()

    check_pdks = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(pdks.__file__)])
    ])

    assert check_pdks == set(all_pdks.keys())


def test_get_tools():
    all_tools = tools.get_tools()

    check_tools = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(tools.__file__)])
    ])
    check_tools.remove('_common')
    check_tools.remove('template')

    assert check_tools == set(all_tools.keys())
