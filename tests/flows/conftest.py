import pytest

from tests import fixtures

@pytest.fixture
def datadir():
    '''Fixture for getting absolute path to this module's data directory.'''
    return fixtures.datadir(__file__)
