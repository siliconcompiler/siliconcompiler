import siliconcompiler
import os
import pytest
import subprocess


@pytest.fixture
def examples_root(scroot):
    return os.path.join(scroot, 'examples')


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

    def _mock_show(chip, filename=None, screenshot=False):
        pass

    # pytest's monkeypatch lets us modify sys.path for this test only.
    monkeypatch.syspath_prepend(examples_root)
    # Mock chip.show() so it doesn't run.
    monkeypatch.setattr(siliconcompiler.Chip, 'show', _mock_show)

    if 'asic_to_syn' in request.keywords:
        org_init = siliconcompiler.Chip.__init__

        def _mock_init(chip, design, loglevel=None):
            org_init(chip, design, loglevel=loglevel)

            chip.set('option', 'to', 'syn')

        monkeypatch.setattr(siliconcompiler.Chip, '__init__', _mock_init)


@pytest.fixture
def run_cli():
    def run(cmd, expect_file):
        if isinstance(cmd, str):
            cmd = [cmd]

        proc = subprocess.run(*cmd)

        assert proc.returncode == 0, \
            f"\"{' '.join(cmd)}\" failed with exit code {proc.returncode}"

        assert os.path.exists(expect_file), \
            f"\"{' '.join(cmd)}\" failed to generate: {expect_file}"

    return run
