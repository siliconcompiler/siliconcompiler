import pytest
import pkgutil
import os

from siliconcompiler import targets
from siliconcompiler import flows
from siliconcompiler import checklists
from siliconcompiler import libs
from siliconcompiler import pdks
from siliconcompiler import apps
from siliconcompiler import tools


@pytest.fixture
def list_dir():
    def run(path, dirs):
        paths = []
        if os.path.isfile(path):
            path = os.path.dirname(path)
        for p in os.listdir(path):
            if dirs and os.path.isdir(os.path.join(path, p)):
                if p == '__pycache__':
                    continue
                paths.append(p)
            if not dirs and os.path.isfile(os.path.join(path, p)):
                if p == '__init__.py':
                    continue
                paths.append(p[:-3])
        return set(paths)
    return run


@pytest.fixture
def list_modules():
    def run(module):
        return set([
            module for _, module, _ in pkgutil.iter_modules([os.path.dirname(module.__file__)])
        ])
    return run


def test_get_targets(list_dir, list_modules):
    all_targets = targets.get_targets()

    assert list_modules(targets) == set(all_targets.keys())

    assert list_dir(targets.__file__, False) == set(all_targets.keys())


def test_get_flows(list_dir, list_modules):
    all_flows = flows.get_flows()

    check_flows = list_modules(flows)
    check_flows.remove('_common')

    assert check_flows == set(all_flows.keys())

    check_flows = list_dir(flows.__file__, False)
    check_flows.remove('_common')

    assert check_flows == set(all_flows.keys())


def test_get_checklists(list_dir, list_modules):
    all_checklists = checklists.get_checklists()

    assert list_modules(checklists) == set(all_checklists.keys())

    assert list_dir(checklists.__file__, False) == set(all_checklists.keys())


def test_get_apps(list_dir, list_modules):
    all_apps = apps.get_apps()

    check_flows = list_modules(apps)
    check_flows.remove('_common')

    assert check_flows == set(all_apps.keys())

    check_flows = list_dir(apps.__file__, False)
    check_flows.remove('_common')

    assert check_flows == set(all_apps.keys())


def test_get_libs(list_dir, list_modules):
    all_libs = libs.get_libs()

    assert list_modules(libs) == set(all_libs.keys())

    assert list_dir(libs.__file__, False) == set(all_libs.keys())


def test_get_pdks(list_dir, list_modules):
    all_pdks = pdks.get_pdks()

    assert list_modules(pdks) == set(all_pdks.keys())

    assert list_dir(pdks.__file__, False) == set(all_pdks.keys())


def test_get_tools(list_dir, list_modules):
    all_tools = tools.get_tools()

    check_flows = list_modules(tools)
    check_flows.remove('_common')
    check_flows.remove('template')

    assert check_flows == set(all_tools.keys())

    check_flows = list_dir(tools.__file__, True)
    check_flows.remove('_common')
    check_flows.remove('template')

    assert check_flows == set(all_tools.keys())
