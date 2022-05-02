import os
import siliconcompiler
import pytest

@pytest.mark.eda
def test_picorv32(picorv32_dir):
    source = os.path.join(picorv32_dir, 'picorv32.v')
    design = "picorv32"

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')

    chip.add('source', source)
    chip.set('design', design)
    chip.set('steplist', ['import'])
    chip.run()

    assert chip.find_result('v', step='import') is not None

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_picorv32(scroot())
