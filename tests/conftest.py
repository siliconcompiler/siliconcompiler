import os
import pytest

from tests import fixtures

def pytest_addoption(parser):
    helpstr = ("Run all tests in current working directory. Default is to run "
               "each test in an isolated per-test temporary directory.")

    parser.addoption(
        "--cwd", action="store_true", help=helpstr
    )

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
