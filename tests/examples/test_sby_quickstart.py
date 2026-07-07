import pytest
import shutil

import os.path

from siliconcompiler import Project


def _assert_clean(design, jobname="job0"):
    manifest = f'build/{design}/{jobname}/{design}.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history(jobname)
    assert project.get('metric', 'errors', step='formal', index='0') == 0


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available in CI")
def test_py_demo():
    from sby_quickstart import demo
    demo.main()

    _assert_clean("demo")


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available in CI")
def test_py_prove():
    from sby_quickstart import prove
    prove.main()

    _assert_clean("prove")


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available in CI")
def test_py_cover():
    from sby_quickstart import cover
    cover.main()

    _assert_clean("cover")
