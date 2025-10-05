import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason="skip until new lambdapdk RC2")
def test_py_interposer():
    from interposer import interposer
    project = interposer.main()

    assert os.path.exists('build/interposer/job0/write_gds/0/outputs/interposer.gds')
    assert os.path.exists('build/interposer/job0/interposer.pkg.json')

    assert project.get('metric', 'drcs', step='drc', index='0') == 108
