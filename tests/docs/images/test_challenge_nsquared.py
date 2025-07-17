import os


def test_py(setup_docs_test, has_graphviz):
    import challenge_nsquared  # noqa: F401

    assert os.path.isfile(os.path.join('..', '_images', 'challenge_nsquared.png'))
    assert os.path.isfile(os.path.join('..', '_images', 'siliconcompiler_ir.png'))
