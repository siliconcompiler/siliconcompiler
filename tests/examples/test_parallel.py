import pytest

import os.path


# Only run daily -- these build the same design several times over.
@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(900)
@pytest.mark.parametrize("approach", ("serial", "indexed", "processes"))
def test_py_parallel(approach):
    from parallel.parallel import APPROACHES, DATAWIDTHS

    APPROACHES[approach]()

    for n in DATAWIDTHS:
        assert os.path.isfile(f'build/adder/N{n}/adder.pkg.json')
