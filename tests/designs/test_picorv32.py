import os
import siliconcompiler
import pytest

@pytest.mark.eda
def test_picorv32(picorv32_dir):
    source = os.path.join(picorv32_dir, 'picorv32.v')

    chip = siliconcompiler.Chip("picorv32")
    chip.load_target('freepdk45_demo')

    chip.add('input', 'verilog', source)
    chip.set('option', 'steplist', ['import'])
    chip.run()

    assert chip.find_result('v', step='import') is not None

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_picorv32(scroot())
