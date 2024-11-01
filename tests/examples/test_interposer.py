import siliconcompiler
import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_py_interposer():
    from interposer import interposer
    interposer.main()

    assert os.path.exists('build/interposer/job0/write_gds/0/outputs/interposer.gds')
    assert os.path.exists('build/interposer/signoff/interposer.pkg.json')

    chip = siliconcompiler.Chip('interposer')
    chip.read_manifest('build/interposer/signoff/interposer.pkg.json')

    assert chip.get('metric', 'drcs', step='drc', index='0', job='signoff') == 0
