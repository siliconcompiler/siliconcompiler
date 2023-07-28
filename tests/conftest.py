import os
import subprocess
import pytest

import siliconcompiler
from tests import fixtures
from siliconcompiler.tools.openroad import openroad


def pytest_addoption(parser):
    helpstr = ("Run all tests in current working directory. Default is to run "
               "each test in an isolated per-test temporary directory.")

    parser.addoption(
        "--cwd", action="store_true", help=helpstr
    )


def pytest_generate_tests(metafunc):
    os.environ['SCPATH'] = os.path.join(fixtures.scroot(), 'siliconcompiler')


@pytest.fixture(autouse=True)
def test_wrapper(tmp_path, request):
    '''Fixture that automatically runs each test in a test-specific temporary
    directory to avoid clutter. To override this functionality, pass in the
    --cwd flag when you invoke pytest.'''
    if not request.config.getoption("--cwd"):
        topdir = os.getcwd()
        os.chdir(tmp_path)

        # Run the test.
        yield

        os.chdir(topdir)
    else:
        yield


@pytest.fixture(autouse=True)
def use_strict(monkeypatch, request):
    '''Set [option, strict] to True for all Chip objects created in test
    session.

    This helps catch bugs.
    '''
    if 'nostrict' in request.keywords:
        return

    old_init = siliconcompiler.Chip.__init__

    def mock_init(chip, design, **kwargs):
        old_init(chip, design, **kwargs)
        chip.set('option', 'strict', True)

    monkeypatch.setattr(siliconcompiler.Chip, '__init__', mock_init)


@pytest.fixture(autouse=True)
def disable_or_images(monkeypatch, request):
    '''
    Disable OpenROAD image generation since this adds to the runtime
    '''
    if 'eda' not in request.keywords:
        return
    old_run = siliconcompiler.Chip.run

    def mock_run(chip):
        for task in chip._get_tool_tasks(openroad):
            chip.set('tool', 'openroad', 'task', task, 'var', 'ord_enable_images', 'false',
                     clobber=False)

        old_run(chip)

    monkeypatch.setattr(siliconcompiler.Chip, 'run', mock_run)


@pytest.fixture
def scroot():
    '''Returns an absolute path to the SC root directory.'''
    return fixtures.scroot()


@pytest.fixture
def datadir(request):
    '''Returns an absolute path to the current test directory's local data
    directory.'''
    return fixtures.datadir(request.fspath)


@pytest.fixture
def gcd_chip():
    '''Returns a fully configured chip object that will compile the GCD example
    design using freepdk45 and the asicflow.'''
    return fixtures.gcd_chip()

# Submodule fixtures
# Tests that rely on data from design submodules should use this pattern to
# create a fixture for the submodule, which will clone it if needed (and will
# not attempt to do so more than once per session). This prevents us from having
# to separately document which tests require submodules, and makes it easier to
# specify tests in CI systems.


def clone_submodule(dir):
    scroot = fixtures.scroot()
    subprocess.run(['git', 'submodule', 'update', '--init', '--recursive', dir], cwd=scroot)
    return os.path.join(scroot, dir)


@pytest.fixture(scope='session')
def picorv32_dir():
    dir = os.path.join('third_party', 'designs', 'picorv32')
    return clone_submodule(dir)


@pytest.fixture(scope='session')
def oh_dir():
    dir = os.path.join('third_party', 'designs', 'oh')
    return clone_submodule(dir)


@pytest.fixture(scope='session')
def microwatt_dir():
    dir = os.path.join('third_party', 'designs', 'microwatt')
    return clone_submodule(dir)
