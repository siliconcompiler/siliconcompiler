import pytest
import os

@pytest.fixture
def datadir(scroot):
    '''Fixture for getting absolute path to this module's data directory.'''
    return (os.path.join(scroot, 'tests', 'flows', 'data'))
