import os
import pytest

from tests import fixtures

@pytest.fixture(autouse=True)
def test_wrapper(tmp_path):
    topdir = os.getcwd()
    os.chdir(tmp_path)

    # Run the test.
    yield

    os.chdir(topdir)

@pytest.fixture
def scroot():
    '''Fixture for getting absolute path to SC install root, no matter where the
    test file is in the tree.'''
    mydir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(mydir, '..'))

@pytest.fixture
def gcd_chip():
    return fixtures.gcd_chip()
