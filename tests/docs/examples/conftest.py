import os

import pytest


@pytest.fixture
def setup_docs_test(scroot, monkeypatch):
    '''Sets up test to run a SiliconCompiler example from the docs.
    (Adopted from test/examples/conftest.py)

    This fixture lets us easily run our example code in CI. Any test that is
    meant to run an example automatically uses 'setup_example_test'. This will
    do 2 important things:

    1) Let you directly import any Python modules that are part of the example.
    2) Ensure that relative paths referenced in the example resolve properly.
    '''
    ex_dir = os.path.join(scroot, 'docs', 'user_guide', 'examples')

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(ex_dir)
