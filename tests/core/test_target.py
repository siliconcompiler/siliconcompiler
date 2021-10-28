import siliconcompiler
import pytest

def test_target_valid():
    '''Basic test of target function.'''
    chip = siliconcompiler.Chip()
    chip.target('asicflow_freepdk45')

    assert chip.get('mode') == 'asic'

def test_target_flipped_error():
    '''Ensure that we error out if the user mixes up PDK name and flow.'''
    chip = siliconcompiler.Chip()

    # Test that call triggers a system exit with status code 1
    # source: https://medium.com/python-pandemonium/testing-sys-exit-with-pytest-10c6e5f7726f
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        chip.target('freepdk45_asicflow')
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

def test_target_fpga_valid():
    '''Ensure that the FPGA flow allows an arbitrary partname and sets mode
    correctly.'''
    chip = siliconcompiler.Chip()
    chip.target('fpgaflow_myfpga')

    assert chip.get('mode') == 'fpga'

def test_target_pdk_error():
    '''Ensure that we error out in ASIC mode if given an invalid PDK name.'''
    chip = siliconcompiler.Chip()
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        chip.target('asicflow_fakepdk')
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

@pytest.mark.parametrize('pdk', ['asap7', 'freepdk45', 'skywater130'])
def test_pdk(pdk):
    chip = siliconcompiler.Chip()
    chip.target(pdk)
    assert chip.get('pdk', 'process') == pdk
