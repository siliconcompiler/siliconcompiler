import pkgutil
import os

from siliconcompiler import targets


def test_get_targets():
    all_targets = targets.get_targets()

    check_targets = set([
        module for _, module, _ in pkgutil.iter_modules([os.path.dirname(targets.__file__)])
    ])

    assert check_targets == set(all_targets.keys())
