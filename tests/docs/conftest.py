import os

import pytest


@pytest.fixture
def setup_docs_test(scroot, monkeypatch):
    '''Sets up test to run a SiliconCompiler example from the docs.
    (Adopted from test/examples/conftest.py)

    This fixture lets us easily run our example code in CI. Any test that is
    meant to run an example should call 'setup_example_test'. This will
    do 3 important things:

    1) Let you directly import any Python modules that are part of the example.
    2) Ensure that relative paths referenced in the example resolve properly.

    setup_example_test returns the path to that example's directory as a
    convenience for accessing any necessary files.
    '''
    def setup():
        ex_dir = os.path.join(scroot, 'docs', 'user_guide', 'examples')

        # pytest's monkeypatch lets us modify sys.path for this test only.
        monkeypatch.syspath_prepend(ex_dir)
        # Add test dir to SCPATH to ensure relative paths resolve.
        monkeypatch.setenv('SCPATH', ex_dir, prepend=os.pathsep)

        return ex_dir

    return setup
