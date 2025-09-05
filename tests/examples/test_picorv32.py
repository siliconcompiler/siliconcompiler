import pytest

import os.path


def test_py_make_check():
    from picorv32 import make
    make.check()


@pytest.mark.parametrize("fileset", ("rtl", "rtl.memory"))
def test_py_make_lint(fileset):
    from picorv32 import make
    make.lint(fileset=fileset)

    assert os.path.isfile('build/picorv32/job0/picorv32.pkg.json')


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.parametrize("fileset", ("rtl", "rtl.memory"))
def test_py_make_syn(fileset):
    from picorv32 import make
    make.syn(fileset=fileset)

    assert os.path.isfile('build/picorv32/job0/picorv32.pkg.json')


@pytest.mark.eda
@pytest.mark.ready
@pytest.mark.timeout(2400)
@pytest.mark.parametrize("fileset,top", (
    ("rtl", "picorv32"), ("rtl.memory", "picorv32_top")))
def test_py_make_asic(fileset, top):
    from picorv32 import make
    make.asic(fileset=fileset)

    assert os.path.isfile('build/picorv32/job0/picorv32.pkg.json')
    assert os.path.isfile(f'build/picorv32/job0/write.gds/0/outputs/{top}.gds')
