import os
import pytest
import shutil

# Setup / teardown.
@pytest.fixture(autouse=True)
def test_wrapper():
    # Create and enter a temporary build directory.
    topdir = os.getcwd()
    if os.path.isdir('pytest_tmp'):
        shutil.rmtree('pytest_tmp')
    os.mkdir('pytest_tmp')
    os.chdir('pytest_tmp')

    # Run the test.
    yield

    # Exit and delete the build directory.
    os.chdir(topdir)
    shutil.rmtree('pytest_tmp')
