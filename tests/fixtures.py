import os
import pytest
import shutil

# Setup / teardown.
@pytest.fixture(autouse=True)
def test_wrapper(request):
    # Create and enter a per-function test directory.

    # request.node.nodeid looks like "tests/asic/test_gcd.py::test_gcd_local"
    # Clean it up by replacing all separators with '_'.
    testdir = request.node.nodeid
    testdir = testdir.replace('/', '_')
    testdir = testdir.replace('.', '_')
    testdir = testdir.replace('::', '_')

    topdir = os.getcwd()

    if os.path.isdir(testdir):
        shutil.rmtree(testdir)
    os.mkdir(testdir)
    os.chdir(testdir)

    # Run the test.
    yield

    # Exit the per-function directory.
    os.chdir(topdir)
