import pytest

import os.path

from siliconcompiler import Project


def _assert_clean(design, jobname="job0"):
    manifest = f'build/{design}/{jobname}/{design}.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history(jobname)
    assert project.get('metric', 'errors', step='formal', index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_counter_formal():
    from sva_sby import counter_formal
    counter_formal.main()

    _assert_clean("counter")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_fifo():
    from sva_sby import fifo
    fifo.main()

    for mode in ("bmc", "prove", "cover"):
        _assert_clean("fifo", jobname=f"job_{mode}")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_demo():
    from sva_sby import demo
    demo.main()

    _assert_clean("demo")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_prove():
    from sva_sby import prove
    prove.main()

    _assert_clean("prove")


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_cover():
    from sva_sby import cover
    cover.main()

    _assert_clean("cover")
