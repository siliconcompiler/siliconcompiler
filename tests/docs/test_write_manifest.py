import os

import pytest


@pytest.mark.quick
def test_py():
    import write_manifest  # noqa: F401

    assert os.path.isfile('hello_world.json')
