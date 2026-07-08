import pytest

import os.path

from siliconcompiler import Project


def _assert_clean(design, steps, jobname="job0"):
    manifest = f'build/{design}/{jobname}/{design}.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history(jobname)
    for step in steps:
        assert project.get('metric', 'errors', step=step, index='0') == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_counter_formal():
    from sva_sby import counter_formal
    counter_formal.main()

    _assert_clean("counter", ["bmc"])


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_fifo():
    from sva_sby import fifo
    fifo.main()

    # all three modes run as parallel nodes in the same job
    _assert_clean("fifo", ["bmc", "prove", "cover"])


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_demo():
    from sva_sby import demo
    demo.main()

    _assert_clean("demo", ["bmc"])


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_prove():
    from sva_sby import prove
    prove.main()

    _assert_clean("prove", ["prove"])


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_cover():
    from sva_sby import cover
    cover.main()

    _assert_clean("cover", ["cover"])
