import pytest
import shutil

import os.path

from siliconcompiler import Project


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available in CI")
def test_py_fifo():
    from sby_fifo import fifo
    fifo.main()

    for mode in ("bmc", "prove", "cover"):
        jobname = f"job_{mode}"
        manifest = f'build/fifo/{jobname}/fifo.pkg.json'
        assert os.path.isfile(manifest)

        project = Project.from_manifest(manifest).history(jobname)
        assert project.get('metric', 'errors', step='formal', index='0') == 0
