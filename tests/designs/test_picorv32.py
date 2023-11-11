import siliconcompiler
import pytest


@pytest.mark.eda
def test_picorv32():
    chip = siliconcompiler.Chip("picorv32")
    chip.load_target('freepdk45_demo')

    chip.register_package_source('picorv32',
                                 'git+https://github.com/cliffordwolf/picorv32',
                                 'f9b1beb4cfd6b382157b54bc8f38c61d5ae7d785')

    chip.input('picorv32.v', package='picorv32')
    chip.set('option', 'to', ['import'])
    chip.run()

    assert chip.find_result('v', step='import') is not None


if __name__ == "__main__":
    test_picorv32()
