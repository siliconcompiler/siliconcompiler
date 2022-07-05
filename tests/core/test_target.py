import siliconcompiler
import pytest

def test_target_valid():
    '''Basic test of target function.'''
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    assert chip.get('option', 'mode') == 'asic'

@pytest.mark.skip(reason="not needed with new target???")
def test_target_flipped_error():
    '''Ensure that we error out if the user mixes up PDK name and flow.'''
    chip = siliconcompiler.Chip('test')

    # Test that call triggers a system exit with status code 1
    # source: https://medium.com/python-pandemonium/testing-sys-exit-with-pytest-10c6e5f7726f
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        chip.load_target('freepdk45_demo')
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

def test_target_fpga_valid():
    '''Ensure that the FPGA flow allows legal part names and sets mode
    correctly.'''
    chip = siliconcompiler.Chip('test')
    chip.set('fpga', 'partname', 'ice40')
    chip.load_flow('fpgaflow')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.get('option', 'mode') == 'fpga'

def test_target_pdk_error():
    '''Ensure that we error out in ASIC mode if given an invalid PDK name.'''
    chip = siliconcompiler.Chip('test')
    with pytest.raises(siliconcompiler.SiliconCompilerError) as pytest_wrapped_e:
        chip.load_flow('asicflow')
        chip.load_pdk('fakepdk')
    assert pytest_wrapped_e.type == siliconcompiler.SiliconCompilerError

@pytest.mark.parametrize('pdk', ['asap7', 'freepdk45', 'skywater130'])
def test_pdk(pdk):
    chip = siliconcompiler.Chip('test')
    chip.load_pdk(pdk)
    assert chip.getkeys('pdk')[0] == pdk
