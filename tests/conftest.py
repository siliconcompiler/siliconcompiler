import os
import pytest
import shutil

@pytest.fixture(autouse=True, scope='session')
def test_session_wrapper():
    # Create and enter a temporary build directory.
    try:
        os.mkdir('pytest_tmp')
    except FileExistsError:
        pass
    os.chdir('pytest_tmp')
