import pytest

import os.path

from siliconcompiler import Project


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_py_lec():
    from adder_lec import lec
    lec.main()

    manifest = 'build/adder/job0/adder.pkg.json'
    assert os.path.isfile(manifest)

    project = Project.from_manifest(manifest).history("job0")

    assert project.get('metric', 'drvs', step='lec', index='0') == 0
