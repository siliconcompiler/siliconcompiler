from siliconcompiler import Project
import pytest


@pytest.fixture(autouse=True)
def setup_example_test(examples_root, monkeypatch, request):
    '''Sets up test to run a SiliconCompiler example.

    This fixture lets us easily run our example code in CI. Any test that is
    meant to run an example should specify 'setup_example_test' as a parameter,
    and then call 'setup_example_test' passing in the name of the relevant
    example as a parameter (matching that example's directory name). This will
    do 3 important things:

    1) Let you directly import any Python modules that are part of the example.
    2) Ensure that relative paths referenced in the example resolve properly.
    3) Mock up chip.show() so that it can be freely used in the example without
       causing CI to hang.

    setup_example_test returns the path to that example's directory as a
    convenience for accessing any necessary files.
    '''

    def _mock_show(*args, **kwargs):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(examples_root)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(Project, 'show', _mock_show)
