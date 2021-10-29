import os
import pytest

from tests import fixtures

@pytest.fixture(autouse=True)
def test_wrapper(tmp_path):
    '''Fixture that automatically runs each test in a test-specific temporary
    directory to avoid clutter. To override this functionality, pass in the
    --cwd flag when you invoke pytest.'''
    topdir = os.getcwd()
    os.chdir(tmp_path)

    # Run the test.
    yield

    os.chdir(topdir)

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
