import pytest
import shutil

import os.path

from siliconcompiler import Project


@pytest.mark.eda
@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which("sby") is None or shutil.which("bitwuzla") is None,
                    reason="sby/bitwuzla are not available in CI")
def test_py_counter_formal():
    from counter_formal import counter_formal
    counter_formal.main()

    manifest = 'build/counter/job0/counter.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history("job0")
    assert project.get('metric', 'errors', step='formal', index='0') == 0
