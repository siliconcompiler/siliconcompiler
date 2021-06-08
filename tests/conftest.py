import os
import pytest
import shutil

@pytest.fixture(autouse=True, scope='session')
def test_session_wrapper():
    # Create and enter a temporary build directory.
    topdir = os.getcwd()
    if os.path.isdir('pytest_tmp'):
        shutil.rmtree('pytest_tmp')
    os.mkdir('pytest_tmp')
    os.chdir('pytest_tmp')
